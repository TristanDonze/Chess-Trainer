"""Services to handle RAG-augmented theory assistance."""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
import weaviate
from weaviate.classes.init import Auth
import chess


class RagServiceError(RuntimeError):
    """Raised when the RAG service cannot satisfy a query."""


@dataclass
class RetrievedChunk:
    title: Optional[str]
    text: str
    source: Optional[str]
    url: Optional[str]


class TheoryAssistant:
    """Thin wrapper around Weaviate + OpenAI to answer chess theory questions."""

    _env_loaded = False
    _env_lock = threading.Lock()

    def __init__(self) -> None:
        self._openai: Optional[OpenAI] = None
        self._weaviate: Optional["weaviate.WeaviateClient"] = None
        self._collection = None
        self._model = os.getenv("THEORY_ASSISTANT_MODEL", "gpt-4.1-mini")
        self._use_rag = os.getenv("THEORY_USE_RAG", "false").lower() in {"1", "true", "yes", "on"}

        self._ensure_env_loaded()

    def _ensure_env_loaded(self) -> None:
        # Load env only once across instances.
        if self.__class__._env_loaded:
            return
        with self.__class__._env_lock:
            if self.__class__._env_loaded:
                return

            project_root = Path(__file__).resolve().parents[3]
            load_dotenv(project_root / ".env")
            load_dotenv(project_root / "misc" / "rag" / ".env")
            self.__class__._env_loaded = True

    def _ensure_openai(self) -> OpenAI:
        if self._openai is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RagServiceError("Missing OPENAI_API_KEY environment variable")
            self._openai = OpenAI(api_key=api_key)
        return self._openai

    def _ensure_collection(self):
        if not self._use_rag:
            return None

        if self._collection is not None:
            return self._collection

        url = os.getenv("WEAVIATE_REST_ENDPOINT")
        api_key = os.getenv("WEAVIATE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not url or not api_key or not openai_key:
            raise RagServiceError("Missing Weaviate configuration in environment variables")

        headers = {"X-OpenAI-Api-Key": openai_key}

        try:
            self._weaviate = weaviate.connect_to_weaviate_cloud(
                cluster_url=url,
                auth_credentials=Auth.api_key(api_key),
                skip_init_checks=True,
                headers=headers,
            )
        except Exception as exc:  # pragma: no cover - network path
            raise RagServiceError(f"Unable to connect to Weaviate: {exc}") from exc

        try:
            self._collection = self._weaviate.collections.get("ChessKnowledgeBase")
        except Exception as exc:  # pragma: no cover - network path
            raise RagServiceError(f"Unable to access ChessKnowledgeBase collection: {exc}") from exc

        return self._collection

    def _retrieve_context(self, query: str, limit: int = 4) -> List[RetrievedChunk]:
        collection = self._ensure_collection()
        if collection is None:
            return []
        try:
            response = collection.query.near_text(query=query, limit=limit)
        except Exception as exc:  # pragma: no cover - network path
            raise RagServiceError(f"Weaviate query failed: {exc}") from exc

        chunks: List[RetrievedChunk] = []
        for obj in getattr(response, "objects", []) or []:
            props: Dict[str, Any] = getattr(obj, "properties", {}) or {}
            text = props.get("content") or props.get("text") or ""
            if not text:
                continue
            chunk = RetrievedChunk(
                title=props.get("title") or props.get("heading"),
                text=text,
                source=props.get("source"),
                url=props.get("url") or props.get("link"),
            )
            chunks.append(chunk)
        return chunks

    def _build_prompt(self, question: str, fen: Optional[str], context: List[RetrievedChunk]) -> List[Dict[str, Any]]:
        system_instructions = (
            "You are a chess coach. Combine the current board state and retrieved knowledge "
            "to provide practical, trustworthy advice. Always verify tactical claims, "
            "mention critical variations in algebraic notation, and cite any referenced sources."
            "If no position is given, focus on theory advice, you can use move recommandation or showcase (or both) to make it more lisible."
            "If a board position (FEN) is supplied, include an explicit move recommendation in UCI notation"
            "on a dedicated line formatted exactly as:"
            "'Recommended move (UCI): <move_uci>'."
            "To showcase a position (like for an example, with fen notation) use exactly the following format:"
            "'Suggested position (FEN): <fen>'."
            "Even if the user doesn't ask for showcase or move, you can still provide them if relevant. (it can really help the user to understand). Though, never propose to showcase, do it directly."
            "If you give showcase FEN or move recommandation, directly add them at the end of your answer without context (they will be parsed)."
            "Always answer in English."

        )

        context_lines: List[str] = []
        if fen:
            context_lines.append(f"Current position FEN: {fen}")
            context_lines.append("Explain relevant plans for the side to move and tactical alerts.")

        if context:
            context_lines.append("Retrieved knowledge base excerpts:")
            for idx, chunk in enumerate(context, start=1):
                parts = [f"[{idx}]"]
                if chunk.title:
                    parts.append(chunk.title)
                parts.append(chunk.text.strip())
                if chunk.source:
                    parts.append(f"Source: {chunk.source}")
                if chunk.url:
                    parts.append(f"URL: {chunk.url}")
                context_lines.append("\n".join(parts))
        else:
            context_lines.append("No external context was retrieved; rely on core chess knowledge.")

        user_prompt = (
            "\n\n".join(context_lines)
            + "\n\nUser question:\n"
            + question.strip()
        )

        return [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_prompt},
        ]

    def answer(self, question: str, fen: Optional[str] = None, *, request_id: Optional[str] = None) -> Dict[str, Any]:
        question_clean = question.strip()
        if not question_clean:
            raise RagServiceError("Cannot answer an empty question")

        context: List[RetrievedChunk] = []
        if self._use_rag:
            try:
                context = self._retrieve_context(question_clean)
            except RagServiceError:
                # If retrieval fails, proceed with empty context after recording the problem.
                context = []

        messages = self._build_prompt(question_clean, fen, context)

        client = self._ensure_openai()
        try:
            response = client.responses.create(model=self._model, input=messages)
        except Exception as exc:  # pragma: no cover - network path
            raise RagServiceError(f"OpenAI response failed: {exc}") from exc

        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise RagServiceError("OpenAI returned an empty response")

        references: List[Dict[str, Optional[str]]] = []
        if context:
            for idx, chunk in enumerate(context, start=1):
                references.append(
                    {
                        "label": f"[{idx}] {chunk.title}" if chunk.title else f"Source [{idx}]",
                        "source": chunk.source,
                        "url": chunk.url,
                    }
                )
        recommended_move: Optional[Dict[str, Any]] = None
        recommended_move = self._extract_recommended_move(output_text, fen)

        if not recommended_move:
            recommended_move = {"uci": "N/A", "san": "N/A", "from": "N/A", "to": "N/A", "promotion": "N/A"}

        showcase_position: Optional[str] = None
        fen_match = re.search(r"Suggested position \(FEN\):\s*([^\s]+)", output_text)
        if fen_match:
            showcase_position = fen_match.group(1).strip()
        if showcase_position:
            recommended_move["showcase_fen"] = showcase_position

        return {
            "id": request_id,
            "answer": output_text.strip(),
            "references": references,
            "recommended_move": recommended_move,
        }

    def _extract_recommended_move(self, text: str, fen: str) -> Optional[Dict[str, Any]]:
        """Extract and validate a move recommendation from model output."""
        try:
            board = chess.Board(fen)
        except Exception:
            return None

        move_uci = self._find_uci_move(text, board)
        move_obj: Optional[chess.Move] = None

        if move_uci:
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                move = None
            if move and move in board.legal_moves:
                move_obj = move

        if move_obj is None:
            move_obj = self._find_san_move(text, board)

        if move_obj is None:
            return None

        best_move_san = board.san(move_obj)
        promotion = chess.piece_symbol(move_obj.promotion).upper() if move_obj.promotion else None

        return {
            "uci": move_obj.uci().upper(),
            "san": best_move_san,
            "from": chess.square_name(move_obj.from_square).upper(),
            "to": chess.square_name(move_obj.to_square).upper(),
            "promotion": promotion,
        }

    @staticmethod
    def _find_uci_move(text: str, board: chess.Board) -> Optional[str]:
        pattern = re.compile(r"\b([a-h][1-8][a-h][1-8][qrbn]?)\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            candidate = match.group(1).lower()
            try:
                move = chess.Move.from_uci(candidate)
            except ValueError:
                continue
            if move in board.legal_moves:
                return candidate
        return None


    @staticmethod
    def _find_san_move(text: str, board: chess.Board) -> Optional[chess.Move]:
        san_pattern = re.compile(r"\b([PNBRQK]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRNB])?[+#]?|O-O-O|O-O)\b")
        for match in san_pattern.finditer(text):
            candidate = match.group(1)
            try:
                move = board.parse_san(candidate)
            except ValueError:
                continue
            if move in board.legal_moves:
                return move
        return None


# Shared singleton instance used across the app
THEORY_ASSISTANT = TheoryAssistant()
