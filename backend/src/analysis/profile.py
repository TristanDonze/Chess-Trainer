"""Profile analytics helpers for extracting mistakes and trends from PGNs."""
from __future__ import annotations

import io
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import chess
import chess.pgn

try:
    from stockfish import Stockfish
except ImportError:  # pragma: no cover - guard for environments without stockfish bindings
    Stockfish = None  # type: ignore


PHASES: Tuple[str, ...] = ("opening", "middlegame", "endgame")
SEVERITIES: Tuple[str, ...] = ("mistake", "blunder")

MISTAKE_THRESHOLD = -150.0     # ~1.5 pawns
BLUNDER_THRESHOLD = -300.0     # ~3 pawns

MATE_SCORE = 10_000.0


class AnalysisError(RuntimeError):
    """Raised when the engine cannot be initialised or an evaluation fails."""


@dataclass(slots=True)
class Mistake:
    ply: int
    move_number: int
    san: str
    uci: str
    severity: str
    phase: str
    motif: str
    delta: float
    cp_before: float
    cp_after: float


def analyze_recent_games(
    games: Iterable[Dict[str, object]],
    username: str,
    *,
    max_games: int = 5,
    engine_depth: int = 12,
) -> Dict[str, object]:
    """Analyze the latest games of the player and return aggregated insights."""
    username = (username or "").strip()
    if not username:
        return {"error": "Missing player username", "games_analyzed": 0}

    if Stockfish is None:
        return {
            "error": "Stockfish python bindings are unavailable; cannot compute analysis.",
            "games_analyzed": 0,
        }

    try:
        evaluator = _create_evaluator(depth=engine_depth)
    except AnalysisError as exc:
        return {"error": str(exc), "games_analyzed": 0}
    player_lc = username.lower()

    prepared_games = _select_games(games, player_lc, max_games=max_games)
    if not prepared_games:
        return {"error": "No recent games found for player", "games_analyzed": 0}

    game_summaries: List[Dict[str, object]] = []
    aggregate_phase_moves = {phase: 0 for phase in PHASES}
    aggregate_phase_mistakes = {phase: 0 for phase in PHASES}
    aggregate_motifs: Counter[str] = Counter()
    aggregate_severity: Counter[str] = Counter()

    for game_info in prepared_games:
        try:
            game_result = _analyze_single_game(game_info, evaluator, player_lc)
        except AnalysisError:
            continue

        if game_result is None:
            continue

        summary = game_result["summary"]
        game_summaries.append(summary)

        for phase in PHASES:
            breakdown = summary["phase_breakdown"][phase]
            aggregate_phase_moves[phase] += breakdown["moves"]
            aggregate_phase_mistakes[phase] += breakdown["mistakes"]

        aggregate_motifs.update(summary["motif_counts"])
        aggregate_severity.update(summary["mistakes"]["by_severity"])

    if not game_summaries:
        return {"error": "Failed to evaluate recent games", "games_analyzed": 0}

    game_summaries.sort(key=lambda item: item.get("end_time") or 0)

    phase_breakdown = {}
    for phase in PHASES:
        moves = aggregate_phase_moves[phase]
        mistakes = aggregate_phase_mistakes[phase]
        rate = (mistakes / moves) if moves else 0.0
        phase_breakdown[phase] = {
            "moves": moves,
            "mistakes": mistakes,
            "rate": round(rate, 3),
        }

    motif_counts = [
        {"motif": motif, "count": count}
        for motif, count in aggregate_motifs.most_common()
    ]

    trend = [
        {
            "label": _format_trend_label(summary),
            "end_time": summary.get("end_time"),
            "mistakes": summary["mistakes"]["total"],
            "blunders": summary["mistakes"]["by_severity"].get("blunder", 0),
            "mistake_rate": summary["mistakes"].get("rate", 0.0),
            "color": summary.get("color"),
            "result": summary.get("result"),
            "url": summary.get("url"),
        }
        for summary in game_summaries
    ]

    return {
        "player": username,
        "games_analyzed": len(game_summaries),
        "phase_breakdown": phase_breakdown,
        "motif_counts": motif_counts,
        "trend": trend,
        "severity_totals": dict(aggregate_severity),
        "games": game_summaries,
    }


def _create_evaluator(*, depth: int) -> Stockfish:
    path_candidates = [
        os.getenv("STOCKFISH_EXECUTABLE"),
        os.getenv("STOCKFISH_PATH"),
        "/opt/homebrew/bin/stockfish",
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
    ]
    for candidate in path_candidates:
        if candidate and os.path.isfile(candidate):
            engine = Stockfish(candidate, depth=depth)
            if hasattr(engine, "set_skill_level"):
                engine.set_skill_level(15)
            return engine
    raise AnalysisError("Stockfish executable not found. Set STOCKFISH_PATH or install Stockfish.")


def _select_games(
    games: Iterable[Dict[str, object]],
    username_lc: str,
    *,
    max_games: int,
) -> List[Dict[str, object]]:
    filtered: List[Dict[str, object]] = []
    for game in games:
        if not isinstance(game, dict):
            continue
        if _player_in_game(game, username_lc):
            filtered.append(game)
    filtered.sort(key=lambda g: g.get("end_time") or 0)
    return filtered[-max_games:]


def _player_in_game(game_info: Dict[str, object], username_lc: str) -> bool:
    white = ((game_info.get("white") or {}) if isinstance(game_info.get("white"), dict) else {})
    black = ((game_info.get("black") or {}) if isinstance(game_info.get("black"), dict) else {})
    w_name = str(white.get("username") or "").lower()
    b_name = str(black.get("username") or "").lower()
    return username_lc in (w_name, b_name)


def _analyze_single_game(
    game_info: Dict[str, object],
    engine: Stockfish,
    username_lc: str,
) -> Optional[Dict[str, object]]:
    pgn = game_info.get("pgn")
    if not isinstance(pgn, str) or not pgn.strip():
        return None

    parsed = chess.pgn.read_game(io.StringIO(pgn))
    if parsed is None:
        return None

    player_color = _resolve_player_color(game_info, parsed, username_lc)
    if player_color is None:
        return None

    opponent = _resolve_opponent_name(game_info, parsed, player_color)
    result = _resolve_result(parsed, player_color)

    board = parsed.board()

    phase_moves = {phase: 0 for phase in PHASES}
    phase_mistakes = {phase: 0 for phase in PHASES}
    severity_counts: Counter[str] = Counter()
    motif_counts: Counter[str] = Counter()
    mistake_list: List[Dict[str, object]] = []
    player_moves = 0

    for ply_idx, move in enumerate(parsed.mainline_moves(), start=1):
        phase = _phase_for(board, ply_idx)
        board_before = board.copy(stack=False)

        if board.turn == player_color:
            player_moves += 1
            phase_moves[phase] += 1
            san = board.san(move)
            cp_before = _evaluate_cp(engine, board, player_color)

            board.push(move)
            cp_after = _evaluate_cp(engine, board, player_color)
            delta = cp_after - cp_before
            severity = _classify_severity(delta)

            if severity:
                motif = _classify_motif(board_before, board, move, player_color, phase, severity)
                phase_mistakes[phase] += 1
                severity_counts[severity] += 1
                motif_counts[motif] += 1
                mistake = Mistake(
                    ply=ply_idx,
                    move_number=board_before.fullmove_number,
                    san=san,
                    uci=move.uci(),
                    severity=severity,
                    phase=phase,
                    motif=motif,
                    delta=round(delta, 1),
                    cp_before=round(cp_before, 1),
                    cp_after=round(cp_after, 1),
                )
                mistake_list.append(_mistake_to_dict(mistake))
        else:
            board.push(move)

    total_mistakes = sum(severity_counts.values())
    mistake_rate = (total_mistakes / player_moves) if player_moves else 0.0

    summary: Dict[str, object] = {
        "url": game_info.get("url"),
        "end_time": game_info.get("end_time"),
        "time_control": game_info.get("time_control"),
        "color": "white" if player_color == chess.WHITE else "black",
        "opponent": opponent,
        "result": result,
        "player_moves": player_moves,
        "mistakes": {
            "total": total_mistakes,
            "rate": round(mistake_rate, 3),
            "by_phase": phase_mistakes,
            "by_severity": {severity: severity_counts.get(severity, 0) for severity in SEVERITIES},
        },
        "mistake_moves": mistake_list,
        "phase_breakdown": {
            phase: {
                "moves": phase_moves[phase],
                "mistakes": phase_mistakes[phase],
            }
            for phase in PHASES
        },
        "motif_counts": dict(motif_counts),
    }

    return {"summary": summary}


def _mistake_to_dict(mistake: Mistake) -> Dict[str, object]:
    return {
        "ply": mistake.ply,
        "move_number": mistake.move_number,
        "san": mistake.san,
        "uci": mistake.uci,
        "severity": mistake.severity,
        "phase": mistake.phase,
        "motif": mistake.motif,
        "delta": mistake.delta,
        "cp_before": mistake.cp_before,
        "cp_after": mistake.cp_after,
    }


def _resolve_player_color(
    game_info: Dict[str, object],
    parsed: chess.pgn.Game,
    username_lc: str,
) -> Optional[chess.Color]:
    white_info = game_info.get("white") if isinstance(game_info.get("white"), dict) else {}
    black_info = game_info.get("black") if isinstance(game_info.get("black"), dict) else {}

    white_username = str((white_info or {}).get("username") or parsed.headers.get("White", "")).lower()
    black_username = str((black_info or {}).get("username") or parsed.headers.get("Black", "")).lower()

    if white_username == username_lc:
        return chess.WHITE
    if black_username == username_lc:
        return chess.BLACK
    return None


def _resolve_opponent_name(
    game_info: Dict[str, object],
    parsed: chess.pgn.Game,
    player_color: chess.Color,
) -> str:
    if player_color == chess.WHITE:
        black_info = game_info.get("black") if isinstance(game_info.get("black"), dict) else {}
        return str((black_info or {}).get("username") or parsed.headers.get("Black", "Opponent"))
    white_info = game_info.get("white") if isinstance(game_info.get("white"), dict) else {}
    return str((white_info or {}).get("username") or parsed.headers.get("White", "Opponent"))


def _resolve_result(parsed: chess.pgn.Game, player_color: chess.Color) -> str:
    result = (parsed.headers.get("Result") or "").strip()
    if result == "1-0":
        return "win" if player_color == chess.WHITE else "loss"
    if result == "0-1":
        return "win" if player_color == chess.BLACK else "loss"
    if result == "1/2-1/2":
        return "draw"
    return "unknown"


def _phase_for(board: chess.Board, ply_idx: int) -> str:
    move_number = board.fullmove_number
    if move_number <= 15:
        return "opening"

    piece_map = board.piece_map()
    non_pawn_pieces = sum(1 for piece in piece_map.values() if piece.piece_type not in (chess.PAWN, chess.KING))
    total_material = sum(_piece_value(piece.piece_type) for piece in piece_map.values())

    if non_pawn_pieces <= 6 or total_material <= 24 or move_number >= 40:
        return "endgame"

    return "middlegame"


def _piece_value(piece_type: chess.PieceType) -> int:
    values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }
    return values.get(piece_type, 0)


def _evaluate_cp(engine: Stockfish, board: chess.Board, player_color: chess.Color) -> float:
    try:
        engine.set_fen_position(board.fen())
        evaluation = engine.get_evaluation()
    except Exception as exc:  # pragma: no cover - stockfish-specific failure
        raise AnalysisError(str(exc)) from exc

    eval_type = evaluation.get("type")
    value = evaluation.get("value")
    if value is None:
        return 0.0

    if eval_type == "mate":
        mate_sign = 1.0 if value > 0 else -1.0
        mate_score = MATE_SCORE - min(abs(int(value)), 50) * 100.0
        score = mate_sign * mate_score
    else:
        score = float(value)

    if board.turn != player_color:
        score = -score
    return score


def _classify_severity(delta: float) -> Optional[str]:
    if delta <= BLUNDER_THRESHOLD:
        return "blunder"
    if delta <= MISTAKE_THRESHOLD:
        return "mistake"
    return None


def _classify_motif(
    board_before: chess.Board,
    board_after: chess.Board,
    move: chess.Move,
    player_color: chess.Color,
    phase: str,
    severity: str,
) -> str:
    opponent = not player_color

    if _is_hanging_piece(board_after, player_color):
        return "hanging_piece"

    if _missed_fork(board_before, move, player_color):
        return "missed_fork"

    if _king_exposed(board_after, player_color):
        return "king_safety"

    if phase == "endgame" and severity in {"mistake", "blunder"}:
        return "endgame_technique"

    if severity == "blunder":
        return "major_blunder"

    return "positional_drift"


def _is_hanging_piece(board: chess.Board, player_color: chess.Color) -> bool:
    opponent = not player_color
    for square, piece in board.piece_map().items():
        if piece.color != player_color or piece.piece_type == chess.KING:
            continue
        if board.is_attacked_by(opponent, square) and not board.is_attacked_by(player_color, square):
            return True
    return False


def _missed_fork(board_before: chess.Board, actual_move: chess.Move, player_color: chess.Color) -> bool:
    if board_before.turn != player_color:
        return False

    if _creates_fork(board_before, actual_move, player_color):
        return False

    candidates = list(board_before.legal_moves)
    for move in candidates[:40]:
        if move == actual_move:
            continue
        if _creates_fork(board_before, move, player_color):
            return True
    return False


def _creates_fork(board: chess.Board, move: chess.Move, player_color: chess.Color) -> bool:
    temp = board.copy(stack=False)
    temp.push(move)
    attacked = temp.attacks(move.to_square)
    targets = []
    for square in attacked:
        piece = temp.piece_at(square)
        if piece is None or piece.color == player_color:
            continue
        targets.append(piece.piece_type)
    high_value = [t for t in targets if t in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)]
    king_targeted = chess.KING in targets
    if len(high_value) >= 2:
        return True
    if king_targeted and high_value:
        return True
    if temp.is_check() and high_value:
        return True
    return False


def _king_exposed(board: chess.Board, player_color: chess.Color) -> bool:
    king_square = board.king(player_color)
    if king_square is None:
        return False
    opponent = not player_color
    attackers = board.attackers(opponent, king_square)
    if not attackers:
        return False
    defenders = board.attackers(player_color, king_square)
    return len(attackers) > len(defenders) + 1


def _format_trend_label(summary: Dict[str, object]) -> str:
    color = summary.get("color")
    opponent = summary.get("opponent") or "Opponent"
    prefix = "W" if color == "white" else "B"
    return f"{prefix} vs {opponent}"
