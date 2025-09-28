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


# ---------- helpers: split + parse ----------
_INSTR_SPLIT_RE   = re.compile(r'^\s*&{2,}\s*INSTRUCTIONS\s*&{2,}\s*$', re.IGNORECASE | re.MULTILINE)
_INSTR_FEN_RE     = re.compile(r'^\s*FEN:\s*(.*?)\s*(?:#.*)?$', re.IGNORECASE | re.MULTILINE)
_INSTR_MOVES_RE   = re.compile(r'^\s*MOVE\s+INDICATION:\s*(.*?)\s*(?:#.*)?$', re.IGNORECASE | re.MULTILINE)
_INSTR_RED_RE     = re.compile(r'^\s*RED\s+SQUARES:\s*(.*?)\s*(?:#.*)?$', re.IGNORECASE | re.MULTILINE)
_INSTR_GREEN_RE   = re.compile(r'^\s*GREEN\s+SQUARES:\s*(.*?)\s*(?:#.*)?$', re.IGNORECASE | re.MULTILINE)   


def _split_text_and_instructions(text: str) -> tuple[str, str | None]:
    m = _INSTR_SPLIT_RE.search(text)
    if not m:
        return text.strip(), None
    main = text[:m.start()].rstrip()
    instr = text[m.end():].strip()
    return main, instr

def _is_valid_fen(fen: str) -> bool:
    try:
        chess.Board(fen)
        return True
    except Exception:
        return False

def _parse_instruction_block(instr: str | None) -> dict:
    if not instr:
        return {'fen': None, 'moves': [], 'red_squares': []}

    fen = None
    m = _INSTR_FEN_RE.search(instr)
    if m:
        cand = (m.group(1) or '').strip()
        if cand and _is_valid_fen(cand):
            fen = cand

    moves: list[str] = []
    m = _INSTR_MOVES_RE.search(instr)
    if m:
        raw = (m.group(1) or '').strip().lower()
        if raw:
            for tok in re.split(r'[;\s,]+', raw):
                tok = tok.strip()
                if tok and re.fullmatch(r'[a-h][1-8][a-h][1-8][qrbn]?$', tok):
                    moves.append(tok)

    reds: list[str] = []
    m = _INSTR_RED_RE.search(instr)
    if m:
        raw = (m.group(1) or '').strip().lower()
        if raw:
            for tok in re.split(r'[;\s,]+', raw):
                if tok in chess.SQUARE_NAMES:
                    reds.append(tok)

    greens: list[str] = []
    m = _INSTR_GREEN_RE.search(instr)
    if m:
        raw = (m.group(1) or '').strip().lower()
        if raw:
            for tok in re.split(r'[;\s,]+', raw):
                if tok in chess.SQUARE_NAMES:
                    greens.append(tok)

    return {'fen': fen, 'moves': moves, 'red_squares': reds, 'green_squares': greens}

# --- replace this helper ---
def _move_dict(move_obj: chess.Move, board: chess.Board) -> dict:
    return {
        "uci": move_obj.uci().upper(),
        "san": board.san(move_obj),
        "from": chess.square_name(move_obj.from_square).upper(),
        "to": chess.square_name(move_obj.to_square).upper(),
        "promotion": chess.piece_symbol(move_obj.promotion).upper() if move_obj.promotion else None,
    }

# --- with this legality-agnostic arrow builder ---
def _arrow_from_uci(uci: str, fen: Optional[str]) -> dict:
    u = (uci or "").strip().lower()
    frm = u[:2].upper() if len(u) >= 4 else None
    to  = u[2:4].upper() if len(u) >= 4 else None
    promo = u[4].upper() if len(u) == 5 else None

    san = None
    if fen and len(u) >= 4 and frm and to:
        try:
            board = chess.Board(fen)
            mv = chess.Move.from_uci(u)
            if mv in board.legal_moves:
                san = board.san(mv)
        except Exception:
            pass

    return {
        "uci": u.upper(),
        "san": san,          # None if not legal/unknown
        "from": frm,
        "to": to,
        "promotion": promo,
    }

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
            "to provide practical, trustworthy advice. Always verify tactical claims,"
            "mention critical variations in algebraic notation, and cite any referenced sources. Don't use markdown or code blocks.\n\n"

            "FEN POLICY (IMPORTANT):\n"
            "- Even if the user doesn't ask for showcase or move, you can still provide them if relevant. (it can really help the user to understand). Though, never propose to showcase, do it directly."
            "- Ensure the FEN follow your answer and is consistent with the position you describe.\n"
            "- You SHOULD create a correct FEN (not empty, don't have two bishops on the same square colors) that answers the question, it MUST be legal and logical.\n"
            "- If you are talking about a specific position you MUST provide a FEN .\n"
            "- Only place the FEN in the INSTRUCTIONS block; NEVER mention or display FEN in the main answer.\n"

            "ARROW / MOVE POLICY:\n"
            "- In the INSTRUCTIONS block, use UCI coordinates (lowercase, e.g., e2e5, g2b7) to draw ARROWS that depict plans, attacks, lines, or piece trajectories.\n"
            "- Avoid using too much arrows.\n"
            "- Use arrows to convey ideas (for instance, to describe 'Fianchetto' do an arrow along the whole diagonal: g2a8).\n"
            "- List multiple arrows separated by ';'. Do NOT include SAN or comments in this field.\n\n"

            "HIGHLIGHT POLICY:\n"
            "- Prefer arrows over colored squares. Only use colored squares if arrows are insufficient.\n"
            "- Use at most 1-2 colored squares total and try to avoid using them. Avoid highlighting irrelevant squares.\n"
            "- RED SQUARES use lowercase coordinates (e.g., 'e4;f7'). In the main answer (not in the block), briefly explain your color coding.\n\n"

            "OUTPUT FORMAT (MANDATORY, MACHINE-PARSABLE TAIL):\n"
            "At the very END of your answer, output EXACTLY ONE block with this header and the four lines below, with no extra lines, quotes, or code fences. "
            "Fields may be empty after the colon. Do NOT add any text after this block.\n"
            "&&&&&& INSTRUCTIONS &&&&&&\n"
            "FEN: <fen>\n"
            "MOVE INDICATION: <uci1;uci2;... or empty>\n"
            "RED SQUARES: <empty or sq1>\n"

            "GENERAL CONTENT:\n"
            "- If no position is given, teach thematic plans and typical tactics; you should provide an illustrative FEN (in the block).\n"
            "- If a FEN is given, prioritize concrete calculation with one main line and one critical alternative in SAN in the main text.\n"
            "- Keep evaluations qualitative.\n"
            "- Use only standard ASCII characters in the INSTRUCTIONS block and do not mention the block in the main text."
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
                context = []

        messages = self._build_prompt(question_clean, fen, context)

        client = self._ensure_openai()
        try:
            response = client.responses.create(model=self._model, input=messages)
        except Exception as exc:  # pragma: no cover
            raise RagServiceError(f"OpenAI response failed: {exc}") from exc

        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise RagServiceError("OpenAI returned an empty response")

        # Split main text vs INSTRUCTIONS block
        main_text, instr_block = _split_text_and_instructions(output_text)
        print(instr_block)
        references: List[Dict[str, Optional[str]]] = []
        if context:
            for idx, chunk in enumerate(context, start=1):
                references.append({
                    "label": f"[{idx}] {chunk.title}" if chunk.title else f"Source [{idx}]",
                    "source": chunk.source,
                    "url": chunk.url,
                })

        # Parse INSTRUCTIONS (FEN, moves[], red_squares[])
        parsed = _parse_instruction_block(instr_block)
        instr_fen   = parsed.get('fen')
        raw_moves   = parsed.get('moves', [])
        red_squares = parsed.get('red_squares', [])
        green_squares = parsed.get('green_squares', [])

        effective_fen = instr_fen or fen

        # Validate all explicit UCIs against the effective FEN
        move_dicts: list[dict] = []
        if raw_moves:
            move_dicts = [_arrow_from_uci(u, effective_fen) for u in raw_moves]
        elif effective_fen:
            # Fallback: if the model didn't provide arrows, try extracting one legal recommendation from text
            fb = self._extract_recommended_move(output_text, effective_fen)
            if fb:
                move_dicts = [fb]

        # Back-compat: accept old 'Suggested position (FEN): ...' if no instr FEN
        showcase_fen = instr_fen
        if not showcase_fen:
            m_old = re.search(r"Suggested position \(FEN\):\s*([^\s]+)", output_text)
            if m_old:
                cand = m_old.group(1).strip()
                if _is_valid_fen(cand):
                    showcase_fen = cand

        instructions = {
            "showcase_fen": showcase_fen,     # str | None
            "red_squares": red_squares,       # list[str]
            "green_squares": green_squares,   # list[str]
            "moves": move_dicts,              # list[dict], can be empty
        }

        return {
            "id": request_id,
            "answer": main_text.strip(),   # instructions block removed from the human text
            "references": references,
            "instructions": instructions,
        }

    def _extract_recommended_move(self, text: str, fen: Optional[str]) -> Optional[Dict[str, Any]]:
        if not fen:
            return None
        try:
            board = chess.Board(fen)
        except Exception:
            return None

        move_uci = self._find_uci_move(text, board)
        move_obj: Optional[chess.Move] = None

        if move_uci:
            try:
                mv = chess.Move.from_uci(move_uci)
            except ValueError:
                mv = None
            if mv and mv in board.legal_moves:
                move_obj = mv

        if move_obj is None:
            move_obj = self._find_san_move(text, board)
        if move_obj is None:
            return None

        return {
            "uci": move_obj.uci().upper(),
            "san": board.san(move_obj),
            "from": chess.square_name(move_obj.from_square).upper(),
            "to": chess.square_name(move_obj.to_square).upper(),
            "promotion": chess.piece_symbol(move_obj.promotion).upper() if move_obj.promotion else None,
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
