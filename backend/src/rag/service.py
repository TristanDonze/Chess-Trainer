"""Services to handle RAG-augmented theory assistance."""
from __future__ import annotations

import os
import re
import threading
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
import weaviate
from weaviate.classes.init import Auth
import chess


# Global Weaviate clients for RAG
_weaviate_client = None
_chess_collection = None


def get_weaviate_client():
    """Get or create Weaviate client with proper connection management"""
    global _weaviate_client
    
    if _weaviate_client is None:
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        weaviate_url = os.environ.get("WEAVIATE_REST_ENDPOINT", "")
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY", "")
        
        headers = {"X-OpenAI-Api-Key": openai_api_key}
        
        _weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
            skip_init_checks=True,
            headers=headers
        )
    
    # Ensure connection is active
    if not _weaviate_client.is_connected():
        try:
            _weaviate_client.connect()
        except Exception as e:
            print(f"Warning: Could not reconnect to Weaviate: {e}")
    
    return _weaviate_client


def get_chess_collection():
    """Get chess knowledge collection"""
    global _chess_collection
    
    if _chess_collection is None:
        client = get_weaviate_client()
        _chess_collection = client.collections.get("ChessKnowledgeBase")
    
    return _chess_collection


def retrieve_chess_knowledge(query: str, limit: int = 2) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chess knowledge from the knowledge base.
    
    Args:
        query (str): The query string to search for relevant information.
        limit (int): Number of results to return
        
    Returns:
        List[Dict]: The retrieved information from the knowledge base.
    """
    try:
        collection = get_chess_collection()
        response = collection.query.near_text(
            query=query,
            limit=limit
        )
        return [obj.properties for obj in response.objects]
    except Exception as e:
        print(f"Error retrieving chess knowledge: {e}")
        return []


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


# Helper function to convert from misc/rag format to our RetrievedChunk format
def _convert_rag_results_to_chunks(rag_results) -> List[RetrievedChunk]:
    """Convert results from misc/rag retrieve_chess_knowledge to RetrievedChunk format"""
    chunks = []
    if isinstance(rag_results, list):
        for result in rag_results:
            if isinstance(result, dict):
                chunk = RetrievedChunk(
                    title=result.get("title") or result.get("heading"),
                    text=result.get("content") or result.get("text") or "",
                    source=result.get("source"),
                    url=result.get("url") or result.get("link"),
                )
                if chunk.text:  # Only add if there's actual content
                    chunks.append(chunk)
    return chunks


class TheoryAssistant:
    """RAG-enhanced chess theory assistant."""

    _env_loaded = False
    _env_lock = threading.Lock()

    def __init__(self) -> None:
        self._openai: Optional[OpenAI] = None
        self._model = os.getenv("THEORY_ASSISTANT_MODEL", "gpt-4o")
        self._use_rag = os.getenv("THEORY_USE_RAG", "true").lower() in {"1", "true", "yes", "on"}
        
        self._ensure_env_loaded()
        print(f"✅ TheoryAssistant initialized (RAG enabled: {self._use_rag})")

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



    def _retrieve_context(self, query: str, limit: int = 4) -> List[RetrievedChunk]:
        """Retrieve context using RAG implementation."""
        if not self._use_rag:
            print(f"🚫 RAG: disabled")
            return []
            
        try:
            print(f"🔍 RAG: querying '{query[:50]}...' (limit={limit})")
            rag_results = retrieve_chess_knowledge(query, limit)
            chunks = _convert_rag_results_to_chunks(rag_results)
            print(f"✅ RAG: retrieved {len(chunks)} chunks from {len(rag_results)} results")
            return chunks
        except Exception as e:
            print(f"❌ RAG retrieval failed: {e}")
            return []

    def _build_prompt(self, question: str, fen: Optional[str], context: List[RetrievedChunk]) -> List[Dict[str, Any]]:
        system_instructions = (
            "You are a chess coach. Combine the current board state and retrieved knowledge "
            "to provide practical advice. Always verify tactical claims,"
            "mention critical variations in algebraic notation. Don't use markdown or code blocks. Focus on INSTRUCTION block.\n\n"

            "FEN POLICY (IMPORTANT):\n"
            "- You SHOULD create a correct FEN (not empty, don't have two bishops on the same square colors) in order to answers the question\n."
            "- it MUST be legal and logical.\n"
            "- Only place the FEN in the INSTRUCTIONS block; NEVER mention or display FEN in the main answer.\n"

            "ARROW / MOVE POLICY:\n"
            "- In the INSTRUCTIONS block, use UCI coordinates (lowercase, e.g., e2e5, g2b7) to draw ARROWS that depict plans, attacks, lines, or piece trajectories.\n"
            "- Use arrows to convey ideas (for instance, to describe 'Fianchetto' do an arrow along the whole diagonal: g2a8).\n"
            "- List multiple arrows separated by ';'. Do NOT include SAN or comments in this field.\n\n"

            "HIGHLIGHT POLICY:\n"
            "- Use at most 0 to 2 colored squares and try to avoid using them. Avoid highlighting irrelevant squares.\n"
            "- RED SQUARES use lowercase coordinates (e.g., 'e4;f7'). In the main answer (not in the block), briefly explain it.\n\n"

            "OUTPUT FORMAT (MANDATORY, MACHINE-PARSABLE TAIL, IMPORTANT):\n"
            "At the very END of your answer, output EXACTLY ONE block with this header and the four lines below, with no extra lines, quotes, or code fences. "
            "Fields may be empty after the colon. Do NOT add any text after this block.\n"
            "&&&&&& INSTRUCTIONS &&&&&&\n"
            "FEN: <fen>\n"
            "MOVE INDICATION: <uci1;uci2;... or empty>\n"
            "RED SQUARES: <empty or sq1>\n"

            "GENERAL CONTENT:\n"
            "- If no position is given, teach thematic plans and typical tactics; you should provide an illustrative FEN (in the block).\n"
            "- Keep evaluations qualitative.\n"
            "- Use only standard ASCII characters in the INSTRUCTIONS block and do not mention the block in the main text."
        )


        context_lines: List[str] = []
        # if fen:
        #     context_lines.append(f"Current position FEN: {fen}")
        #     context_lines.append("Explain relevant plans for the side to move and tactical alerts.")

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
            rag_status = "disabled" if not self._use_rag else "no results"
            print(f"RAG: {rag_status} (use_rag={self._use_rag})")
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

    def _create_rag_tools(self) -> List[Dict[str, Any]]:
        """Create function tools for RAG-enhanced chat completion."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "retrieve_chess_knowledge",
                    "description": "Retrieve relevant chess knowledge from the knowledge base to provide more accurate and detailed answers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query string to search for relevant chess information"
                            },
                            "limit": {
                                "type": "integer", 
                                "description": "Number of results to return (default: 2)",
                                "default": 2
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def _execute_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call and return the result."""
        function_name = function_call.get("name")
        function_args = function_call.get("arguments", "{}")
        
        if isinstance(function_args, str):
            args = json.loads(function_args)
        else:
            args = function_args
        
        if function_name == "retrieve_chess_knowledge":
            try:
                rag_results = retrieve_chess_knowledge(args.get("query", ""), args.get("limit", 2))
                chunks = _convert_rag_results_to_chunks(rag_results)
                # Convert chunks to a simple format for the AI
                result = []
                for chunk in chunks:
                    chunk_data = {
                        "text": chunk.text,
                        "title": chunk.title,
                        "source": chunk.source,
                        "url": chunk.url
                    }
                    result.append(chunk_data)
                return {"results": result}
            except Exception as e:
                return {"results": [], "error": str(e)}
        else:
            raise ValueError(f"Unknown function: {function_name}")

    def answer(self, question: str, fen: Optional[str] = None, *, request_id: Optional[str] = None) -> Dict[str, Any]:
        question_clean = question.strip()
        if not question_clean:
            raise RagServiceError("Cannot answer an empty question")

        # Retrieve chess knowledge using RAG
        context: List[RetrievedChunk] = []
        if self._use_rag:
            try:
                context = self._retrieve_context(question_clean)
            except Exception:
                context = []

        # Build enhanced prompt with RAG context
        messages = self._build_prompt(question_clean, fen, context)

        # Get OpenAI response
        client = self._ensure_openai()
        try:
            response = client.chat.completions.create(model=self._model, messages=messages)
        except Exception as exc:
            raise RagServiceError(f"OpenAI response failed: {exc}") from exc

        output_text = response.choices[0].message.content
        if not output_text:
            raise RagServiceError("OpenAI returned an empty response")

        # Process response to expected format
        return self._process_response(output_text, fen, request_id, context)

    def _process_response(self, raw_response: str, fen: Optional[str], request_id: Optional[str], context: List[RetrievedChunk]) -> Dict[str, Any]:
        """Process RAG agent response to match expected format"""
        # Split main text vs INSTRUCTIONS block
        main_text, instr_block = _split_text_and_instructions(raw_response)
        
        # Parse INSTRUCTIONS (FEN, moves[], red_squares[])
        parsed = _parse_instruction_block(instr_block)
        instr_fen = parsed.get('fen')
        raw_moves = parsed.get('moves', [])
        red_squares = parsed.get('red_squares', [])
        green_squares = parsed.get('green_squares', [])

        effective_fen = instr_fen or fen

        # Validate all explicit UCIs against the effective FEN
        move_dicts: list[dict] = []
        if raw_moves:
            move_dicts = [_arrow_from_uci(u, effective_fen) for u in raw_moves]
        elif effective_fen:
            # Fallback: try extracting one legal recommendation from text
            fb = self._extract_recommended_move(raw_response, effective_fen)
            if fb:
                move_dicts = [fb]

        # Back-compat: accept old 'Suggested position (FEN): ...' if no instr FEN
        showcase_fen = instr_fen
        if not showcase_fen:
            m_old = re.search(r"Suggested position \(FEN\):\s*([^\s]+)", raw_response)
            if m_old:
                cand = m_old.group(1).strip()
                if _is_valid_fen(cand):
                    showcase_fen = cand

        instructions = {
            "showcase_fen": showcase_fen,
            "red_squares": red_squares,
            "green_squares": green_squares,
            "moves": move_dicts,
        }

        # Build references from retrieved context
        references: List[Dict[str, Optional[str]]] = []
        if context:
            for idx, chunk in enumerate(context, start=1):
                references.append({
                    "label": f"[{idx}] {chunk.title}" if chunk.title else f"Source [{idx}]",
                    "source": chunk.source,
                    "url": chunk.url,
                })

        return {
            "id": request_id,
            "answer": main_text.strip(),
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
