
import base64
import math
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

from src.utils.socket_server import ServerSocket
from src.utils.extract_chesscom import get_chesscom_data
from src.analysis import analyze_recent_games

import src.utils.message as protocol

from meta import AVAILABLE_MODELS

from src.chess.game import Game
from src.chess.player import Player
from models.engine import Engine
from src.rag import THEORY_ASSISTANT, RagServiceError

# Import the chess agent from misc/rag/src
misc_rag_path = Path(__file__).parent.parent / "misc" / "rag" / "src"
if str(misc_rag_path) not in sys.path:
    sys.path.insert(0, str(misc_rag_path))

try:
    from chess_agent import get_chess_agent # type: ignore
except ImportError as e:
    print(f"Warning: Could not import chess_agent from misc/rag/src: {e}")
    get_chess_agent = None

import traceback
import asyncio
import json
import chess

PATHS = {
    "ranking": ["./data/ranking.json", "backend/data/ranking.json"]
}

class Server:
    """
    Server class that handles the app.
    """

    def __init__(self):
        self.socket = ServerSocket(_print=True)
        self.client_pseudo = None
        self.client_profil = None

        self.focused_game = None
        self.analysis_engine = None
        self._reset_player_eval_history()
        self._analysis_lock = asyncio.Lock()
        self._commentary_lock = asyncio.Lock()
        self._tts_lock = asyncio.Lock()
        self._tts_client = None
        self._tts_voice = os.getenv("COMMENTARY_TTS_VOICE", os.getenv("TTS_VOICE", "nova"))
        self._tts_model = os.getenv("COMMENTARY_TTS_MODEL", os.getenv("TTS_MODEL", "gpt-4o-mini-tts"))

        # Initialize RAG-enhanced chess commentary agent
        try:
            if get_chess_agent is not None:
                self.chess_agent = get_chess_agent()
            else:
                self.chess_agent = None
        except Exception as exc:
            traceback.print_exc()
            print(f"Warning: Could not initialize chess agent for enhanced commentary: {exc}")
            self.chess_agent = None

        for model in AVAILABLE_MODELS.values():
            try: getattr(model, "__author__")
            except: raise Engine.UndefinedAuthorError(model, f"Model {model.__name__} has no author")

            try: getattr(model, "__description__")
            except: raise Engine.UndefinedDescriptionError(model, f"Model {model.__name__} has no description")

            try: getattr(model, "play")
            except: raise Engine.UndefinedPlayMethodError(model, f"Model {model.__name__} has no play method")

        self._ensure_analysis_engine()

    def _reset_player_eval_history(self):
        self._last_player_eval_cp = {
            chess.WHITE: None,
            chess.BLACK: None,
        }

    def _debug_log(self, payload):
        if not os.getenv("CHESS_TRAINER_DEBUG"):
            return
        try:
            print("[debug]", payload)
        except Exception:
            pass

    def open_file(self, name, mode):
        """
        Open a file with the given name.

        Was create because some computer need different paths to access the same file. 
        (maybe it's because the person didn't follow the README)
        """
        if name in PATHS:
            for path in PATHS[name]:
                try:
                    return open(path, mode)
                except FileNotFoundError:
                    continue
                except Exception as e:
                    raise e
            raise Exception(f"File {name} not found")
        else:
            raise Exception(f"Path {name} not registered in PATHS")

    async def run(self):

        # Main loop
        self.set_up_event_listeners() # See README.md for more details

        # Start the server properly
        async with self.socket:
            await self.socket.wait()
    
    def set_up_event_listeners(self):
        """
        Set up the event listeners for the server.
        """

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "start-game",
            lambda client, message: self.start_game(message.content) if message.type == "start-game" else None
        )

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "get-possible-moves",
            lambda client, message: self.get_possible_moves(message.content) if message.type == "get-possible-moves" else None
        )

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "move-piece",
            lambda client, message: self.move_piece(message.content) if message.type == "move-piece" else None
        )

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "connect-user",
            lambda client, message: self.connect_user(message.content) if message.type == "connect-user" else None
        )

        # self.socket.on(
        #     ServerSocket.EVENTS_TYPES.on_message,
        #     "get-players-list",
        #     lambda client, message: self.get_players_list() if message.type == "get-players-list" else None
        # )

        # self.socket.on(
        #     ServerSocket.EVENTS_TYPES.on_message,
        #     "create-player",
        #     lambda client, message: self.create_player(message.content) if message.type == "create-player" else None
        # )

        # self.socket.on(
        #     ServerSocket.EVENTS_TYPES.on_message,
        #     "get-evaluators-list",
        #     lambda client, message: self.get_evaluators_list() if message.type == "get-evaluators-list" else None
        # )

        # self.socket.on(
        #     ServerSocket.EVENTS_TYPES.on_message,
        #     "evaluate-game",
        #     lambda client, message: self.evaluate_game(message.content) if message.type == "evaluate-game" else None
        # )

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "get-chesscom-profil",
            lambda client, message: self.get_chesscom_profil(message.content) if message.type == "get-chesscom-profil" else None
        )

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "analyze-game",
            lambda client, message: self.analyse_game(client, message.content) if message.type == "analyze-game" else None
        )

        self.socket.on(
            ServerSocket.EVENTS_TYPES.on_message,
            "theory-question",
            lambda client, message: asyncio.create_task(self.handle_theory_question(client, message.content))
            if message.type == "theory-question" else None
        )
    
    async def start_game(self, info):
        """
        Start a new game with the given info.
        """
        self._reset_player_eval_history()
        self.focused_game = Game()
        
        # self.focused_game.play(white=Player(info["player2"]), black=Player(info["player1"]))
        ai = AVAILABLE_MODELS["Stockfish AI"](skill_level=20).setup() # skills level from 0 (weakest) to 20 (strongest)
        self.focused_game.play(white=Player(info["player1"]), black=ai)

        # if info["player_color"] == "w":
        #     self.focused_game.play(white=Player(info["player"]), black=ai)
        # else:
        #     self.focused_game.play(white=ai, black=Player(info["player"]))

        self.focused_game.ia_move_handler = self.ia_move_handler
        ctn = {
            "FEN": self.focused_game.fen(),
            "current_player": self.focused_game.board.turn
        }
        
        # Update chess agent with initial game state
        self._update_chess_agent_fen(self.focused_game.fen())
        
        asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "game-started").to_json()))

        # wait 1s before playing the first move
        await asyncio.sleep(0.8)
        self.focused_game.play_engine_move()

    # def get_evaluators_list(self):
    #     """
    #     Get all available evaluators.
    #     """
        
    #     # a model is an evaluator if it has a 'evaluate' method
    #     evaluators = []
    #     for name, model in AVAILABLE_MODELS.items():
    #         if not hasattr(model, "evaluate"): continue

    #         evaluators.append({
    #             "name": name,
    #             "author": model.__author__,
    #             "description": model.__description__
    #         })

    #     asyncio.create_task(self.socket.broadcast(protocol.Message(evaluators, "evaluators-list").to_json()))

    # def evaluate_game(self, info):
    #     """return win probability for blacks"""
    #     model_name = info["model"]
    #     if model_name not in AVAILABLE_MODELS:
    #         asyncio.create_task(self.socket.broadcast(protocol.Message(f"Model {model_name} not found",  "error").to_json()))
    #         return
        
    #     if self.focused_game is None:
    #         asyncio.create_task(self.socket.broadcast(protocol.Message("No game started", "error").to_json()))
    #         return
        
    #     model = AVAILABLE_MODELS[model_name]()
    #     outcome = int(model.evaluate(self.focused_game)[0] * 100)
    #     asyncio.create_task(self.socket.broadcast(protocol.Message(outcome, "game-evaluated").to_json()))

    def get_possible_moves(self, info):
        """
        Get the possible moves for the given position.
        """
        if self.focused_game is None:
            asyncio.create_task(self.socket.broadcast(protocol.Message("No game started", "error").to_json()))
            return
        
        piece = self.focused_game.get_piece(info["pos"])
        if piece is None:
            asyncio.create_task(self.socket.broadcast(protocol.Message("No piece at position", "error").to_json()))
            return
        
        if str(piece) != info["fen"]:
            asyncio.create_task(self.socket.broadcast(protocol.Message(f"Invalid piece at position; find: {piece.fen()}, should be {info['fen']}", "error").to_json()))
            return
        
        moves = self.focused_game.get_possible_moves(info["pos"])
        # transform coordinates to end box names
        moves = [chess.square_name(move.to_square).upper() for move in moves]
        asyncio.create_task(self.socket.broadcast(protocol.Message({'moves': moves}, "possible-moves").to_json()))

    def move_piece(self, info):
        """
        Move the piece from start to end.
        """
        if self.focused_game is None:
            asyncio.create_task(self.socket.broadcast(protocol.Message("No game started", "error").to_json()))
            return
        
        try:
            pre_fen = self.focused_game.fen()
            player_color = self.focused_game.board.turn
            move_number = self.focused_game.board.fullmove_number
            move = chess.Move.from_uci(info["start"].lower() + info["end"].lower() + (info.get("promote", "") or "").lower())
            self.focused_game.move(move)
            post_fen = self.focused_game.fen()
            
            # Update chess agent with new position
            self._update_chess_agent_fen(post_fen)
        except Exception as e:
            asyncio.create_task(self.socket.broadcast(protocol.Message(str(e), "error").to_json()))
            traceback.print_exc()
            return

        ctn = {
            "FEN": self.focused_game.fen(),
            "king_in_check": self.focused_game.king_in_check[chess.WHITE] or self.focused_game.king_in_check[chess.BLACK],
            "checkmate": "w" if self.focused_game.checkmate == chess.WHITE else "b" if self.focused_game.checkmate == chess.BLACK else None,
            "draw": self.focused_game.draw,
        }

        asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "confirm-move").to_json()))

        if not self._is_engine_color(player_color):
            asyncio.create_task(
                self._provide_live_commentary(
                    move=move,
                    player_color=player_color,
                    pre_fen=pre_fen,
                    post_fen=post_fen,
                    move_number=move_number
                )
            )

        async def play():
            self.focused_game.play_engine_move()
        asyncio.create_task(play())

    def ia_move_handler(self, move: chess.Move):
        """
        Handle the move of the AI.
        """
        _from = chess.square_name(move.from_square).upper()
        _to = chess.square_name(move.to_square).upper()
        if move.promotion is not None:
            promote = chess.piece_symbol(move.promotion)
            # upper if white, lower if black (reverse in the if because the turn is already changed)
            promote = promote.upper() if self.focused_game.board.turn == chess.BLACK else promote.lower()
        else:
            promote = None

        ctn = {
            "FEN": self.focused_game.fen(),
            "king_in_check": self.focused_game.king_in_check[chess.WHITE] or self.focused_game.king_in_check[chess.BLACK],
            "checkmate": "w" if self.focused_game.checkmate == chess.WHITE else "b" if self.focused_game.checkmate == chess.BLACK else None,
            "draw": self.focused_game.draw,
            "from": _from,
            "to": _to,
            "promote": promote
        }
        
        # Update chess agent with new position after AI move
        self._update_chess_agent_fen(self.focused_game.fen())
        
        asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "ai-move").to_json()))
        
        async def play():
            await asyncio.sleep(0.8)
            self.focused_game.play_engine_move()
        asyncio.create_task(play())

    def get_chesscom_profil(self, info, _preloaded=True):
        """
        Get the profil of a chess.com user.
        """
        if _preloaded and self.client_pseudo is None:
            asyncio.create_task(self.socket.broadcast(protocol.NavigationCommand(url="../index.html").to_json()))
            return
        
        reload = info.get("refresh", False)
        if _preloaded and self.client_profil is not None and not reload:
            asyncio.create_task(self.socket.broadcast(protocol.Message(self.client_profil, "chesscom-profil").to_json()))
            return
        
        try:
            elo, games = get_chesscom_data(self.client_pseudo)
            analysis = analyze_recent_games(games, self.client_pseudo)
            ctn = {
                "elo": elo,
                "nb_games": len(games),
                "games": games,
                "analysis": analysis,
            }
            self.client_profil = ctn
            asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "chesscom-profil").to_json()))
        except Exception as e:
            asyncio.create_task(self.socket.broadcast(protocol.Message(str(e), "error").to_json()))
            traceback.print_exc()


    async def get_comment_game_analysis(self, fen: str, move: str, dx: float, last_white_winrate: float | None, current_white_winrate: float | None, is_user_white: bool, move_player_color: str) -> str | None:
        print("move:", move, "dx:", dx)
        question = (
            f"You are given a chess position (FEN: {fen} — do not display it) we want the user to rethink about the current position. "
            f"The player that you are training is playing {'White' if is_user_white else 'Black'}. "
            f"The move will be play by {move_player_color}. NOTE: we don't give back to the player the move he just played, it's just to help you understand the position with a fresh eyes. "
            f"Understand that {'black' if move_player_color == 'white' else 'white'} win rate WOULD change after that move by {dx:+.1f}% if the same move is played. You don't need to mention the exact win rates, it's just to help you understand the impact of the move that was played in the initial game."
            f"Write at most two sentences that ask the user what they would do or avoid here and why, focusing on the idea and practical consequences. "
            + (f", from {last_white_winrate:.1f}% to {current_white_winrate:.1f}%." if last_white_winrate is not None and current_white_winrate is not None else ". ")
            + "Optionally reference a famous game/quote only if directly relevant; Don't say 'a tactic' or 'an opportunity' etc. be specific. DON'T name pieces on the board (e.g. 'the knight on f5'),"
            "do not use notation (SAN/UCI) or square names; avoid generic praise/blame; be qualitative and concise; "
            "prefer describing plans/attacks (think arrows) over color-highlights; end with a direct (short ?) question."
        )

        try:
            async with self._commentary_lock:
                response = await asyncio.to_thread(
                    THEORY_ASSISTANT.answer,
                    question=question,
                )
        except RagServiceError:
            return None
        except Exception:
            traceback.print_exc()
            return None

        if not response:
            return None

        answer = response.get("answer") if isinstance(response, dict) else None
        if not answer:
            return None
        return answer.strip()

    async def analyse_game(self, client, info):
        """
        Analyze a game with the given PGN.
        """
        # 1. load the PGN into a game object
        self._reset_player_eval_history()
        self.focused_game = Game()
        self.focused_game.load(info["game"]["pgn"], format="pgn")

        # players ?
        white_player = info["game"]["white"]["username"] or "White"
        black_player = info["game"]["black"]["username"] or "Black"

        is_user_white = (self.client_pseudo is not None and white_player.lower() == self.client_pseudo.lower())

        
        # Update chess agent with initial position for analysis
        self._update_chess_agent_fen(self.focused_game.fen())
        
        # 2. analyze the game with stockfish
        if "Stockfish AI" not in AVAILABLE_MODELS:
            asyncio.create_task(self.socket.broadcast(protocol.Message("Stockfish AI not available", "error").to_json()))
            return
        
        stockfish = AVAILABLE_MODELS["Stockfish AI"]()
        moves = {
            "white": [], # [{"move": "e4", "evaluation": 0.23}, ...]
            "black": []
        }

        self.focused_game.play(Player("White", False), Player("Black", False)) # to set the players (not IA)

        async with protocol.LoadingScreen(self.socket, client) as screen:
            await screen.init(["Analyze game"])
            await screen.step("Analyze game", 0)

            THRESHOLD = 15 # winrate change threshold to consider a move to be.a key move

            last_last_white_winrate = 50
            last_dx = 0
            last_move = None
            last_fen = None
            last_white_winrate = 50
            for idx, move in enumerate(self.focused_game.history):
                fen = self.focused_game.fen()
                self.focused_game.move(move)

                evaluation = stockfish.evaluate(self.focused_game)
                dx = (evaluation["white_win_pct"] or last_white_winrate) - last_white_winrate  # todo handle None case (e.g. mate found)
                
                comment = None
                comment_audio = None
                if abs(dx) >= THRESHOLD:
                    if is_user_white and self.focused_game.board.turn == chess.BLACK \
                    or (not is_user_white) and self.focused_game.board.turn == chess.WHITE:
                        comment = await self.get_comment_game_analysis(
                            fen=fen,
                            move=move.uci(),
                            dx=dx,
                            last_white_winrate=last_white_winrate,
                            current_white_winrate=last_white_winrate,
                            is_user_white=is_user_white,
                            move_player_color="white" if idx % 2 == 0 else "black"
                        )
                    else:
                        comment = await self.get_comment_game_analysis(
                            fen=last_fen,
                            move=last_move.uci(),
                            dx=last_dx,
                            last_white_winrate=last_last_white_winrate,
                            current_white_winrate=last_white_winrate,
                            is_user_white=is_user_white,
                            move_player_color="white" if (idx - 1) % 2 == 0 else "black"
                        )

                    # Generate TTS audio for the comment if it exists
                    if comment and comment.strip():
                        comment_audio = await self._generate_comment_audio(comment)
                    
                move_data = {
                    "move": move.uci().upper(),
                    "fen": self.focused_game.fen(),
                    "from": chess.square_name(move.from_square).upper(),
                    "to": chess.square_name(move.to_square).upper(),
                    "promote": chess.piece_symbol(move.promotion).upper() if move.promotion else None,
                    "white_checkmate": self.focused_game.checkmate == chess.WHITE,
                    "black_checkmate": self.focused_game.checkmate == chess.BLACK,
                    "king_in_check": self.focused_game.king_in_check[chess.WHITE] or self.focused_game.king_in_check[chess.BLACK],
                    "draw": self.focused_game.draw,
                    "piece": str(self.focused_game.get_piece(chess.square_name(move.to_square).upper())),
                    "key_move": abs(dx) >= THRESHOLD,
                    "comment": comment,
                    **evaluation
                }
                
                # Add audio data if TTS was generated
                if comment_audio:
                    move_data["audio"] = comment_audio
                    
                moves["white" if idx % 2 == 0 else "black"].append(move_data)
                last_last_white_winrate = last_white_winrate
                last_white_winrate = evaluation["white_win_pct"] or last_white_winrate
                last_dx = dx
                last_move = move
                last_fen = fen

                await screen.step("Analyze game", (idx + 1) / len(self.focused_game.history), info=f"Analyzing move {idx + 1}/{len(self.focused_game.history)}", eta_s=(len(self.focused_game.history) - idx) * 2)

        ctn = {
            "white_player": white_player,
            "black_player": black_player,
            "is_user_white": is_user_white,
            "moves": moves,
            "result": "white - " + info["game"]["white"]["result"] if info["game"]["white"]["result"] in ["win", "checkmated"] else "black - " + info["game"]["black"]["result"]
        }
        asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "game-analyzed").to_json()))

    async def handle_theory_question(self, client, info):
        """Answer a theory question using the OpenAI assistant."""
        info = info or {}
        question = (info.get("question") or "").strip()
        request_id = info.get("request_id")

        if not question:
            payload = {
                "id": request_id,
                "error": "Question cannot be empty."
            }
            await self.socket.send(client, protocol.Message(payload, "theory-answer"))
            return

        try:
            answer = THEORY_ASSISTANT.answer(question=question, request_id=request_id)
            payload = {
                **answer,
            }
        except RagServiceError as exc:
            payload = {
                "id": request_id,
                "error": str(exc),
            }
        except Exception as exc:
            traceback.print_exc()
            payload = {
                "id": request_id,
                "error": f"Unexpected error: {exc}",
            }

        await self.socket.send(client, protocol.Message(payload, "theory-answer"))

    def _canon_player_color(self, player_color, fallback_turn=None):
        """Return chess.WHITE or chess.BLACK for assorted inputs."""
        if isinstance(player_color, bool):
            return chess.WHITE if player_color else chess.BLACK
        if isinstance(player_color, int):
            if player_color == 1:
                return chess.WHITE
            if player_color == 0:
                return chess.BLACK
        if player_color in (chess.WHITE, chess.BLACK):
            return player_color
        if isinstance(player_color, str):
            s = player_color.strip().lower()
            if s in {"white", "w", "1", "true", "yes"}:
                return chess.WHITE
            if s in {"black", "b", "0", "false", "no"}:
                return chess.BLACK
        fallback = fallback_turn if fallback_turn in (chess.WHITE, chess.BLACK) else None
        # if fallback is None:
        #     self._debug_log({
        #         "warn": "canon_color_fallback_missing",
        #         "received": repr(player_color)
        #     })
        return fallback or chess.WHITE

    def _ensure_analysis_engine(self):
        if self.analysis_engine is not None:
            return self.analysis_engine

        stockfish_cls = AVAILABLE_MODELS.get("Stockfish AI")
        if stockfish_cls is None:
            return None

        try:
            self.analysis_engine = stockfish_cls(skill_level=20, depth=18, think_time=80).setup()
        except Exception as exc:
            traceback.print_exc()
            self.analysis_engine = None
        return self.analysis_engine

    def _update_chess_agent_fen(self, fen: str):
        """Update the chess agent with current FEN position"""
        if self.chess_agent:
            try:
                self.chess_agent.update_fen_position(fen)
            except Exception as exc:
                self._debug_log({"warn": "chess_agent_fen_update_failed", "error": str(exc)})

    def _update_chess_agent_analysis(self, analysis_str: str):
        """Update the chess agent with current Stockfish analysis"""
        if self.chess_agent:
            try:
                self.chess_agent.update_stockfish_input(analysis_str)
            except Exception as exc:
                self._debug_log({"warn": "chess_agent_analysis_update_failed", "error": str(exc)})

    def _is_engine_color(self, color):
        if self.focused_game is None:
            return False

        color = self._canon_player_color(color, fallback_turn=chess.WHITE)
        player = self.focused_game.white if color == chess.WHITE else self.focused_game.black
        if player is None:
            return False
        return getattr(player, "is_engine", False)

    async def _provide_live_commentary(self, move: chess.Move, player_color, pre_fen: str, post_fen: str, move_number: int):
        if self._ensure_analysis_engine() is None:
            return

        try:
            analysis = await self._collect_move_analysis(move, player_color, pre_fen, post_fen, move_number)
            if not analysis:
                return

            severity = analysis.get("severity")
            comment_text = None
            if severity != "correct":
                comment_text = await self._generate_comment_text(analysis)

            if comment_text:
                analysis["comment"] = comment_text.strip()
            else:
                if severity == "correct":
                    analysis["comment"] = self._comment_for_correct_move(analysis)
                else:
                    analysis["comment"] = self._fallback_comment(analysis)

            if analysis.get("severity") != "correct":
                audio_payload = await self._generate_comment_audio(analysis.get("comment"))
                if audio_payload:
                    analysis["audio"] = audio_payload

            message_payload = self._build_commentary_message(analysis)
            if message_payload:
                await self.socket.broadcast(protocol.Message(message_payload, "game-commentary").to_json())
        except RagServiceError:
            pass
        except Exception:
            traceback.print_exc()

    async def _collect_move_analysis(self, move: chess.Move, player_color, pre_fen: str, post_fen: str, move_number: int):
        engine = self._ensure_analysis_engine()
        if engine is None:
            return None

        async with self._analysis_lock:
            return await asyncio.to_thread(
                self._collect_move_analysis_sync,
                engine,
                move,
                player_color,
                pre_fen,
                post_fen,
                move_number
            )

    def _collect_move_analysis_sync(self, engine, move: chess.Move, player_color, pre_fen: str, post_fen: str, move_number: int):
        try:
            board_before = chess.Board(pre_fen)
            board_after = chess.Board(post_fen)
        except Exception:
            return None
        
        player_color_norm = self._canon_player_color(player_color, fallback_turn=board_before.turn)

        try:
            move_san = board_before.san(move)
        except Exception:
            move_san = move.uci().upper()
        move_uci = move.uci().upper()
        move_from = chess.square_name(move.from_square).upper()
        move_to = chess.square_name(move.to_square).upper()
        promotion = chess.piece_symbol(move.promotion).upper() if move.promotion else None

        stockfish_engine = engine.stockfish

        stockfish_engine.set_fen_position(pre_fen)
        try:
            raw_top = stockfish_engine.get_top_moves(3) or []
        except Exception:
            raw_top = []
        raw_pre = stockfish_engine.get_evaluation()

        stockfish_engine.set_fen_position(post_fen)
        raw_post = stockfish_engine.get_evaluation()

        pre_eval = self._normalize_evaluation(board_before, raw_pre)
        post_eval = self._normalize_evaluation(board_after, raw_post)

        score_before_cp = pre_eval.get("score_for_white_cp")
        if score_before_cp is None:
            score_before_cp = 0.0
        score_after_cp = post_eval.get("score_for_white_cp")
        if score_after_cp is None:
            score_after_cp = 0.0
        raw_delta_cp = score_after_cp - score_before_cp
        move_delta_cp = raw_delta_cp if player_color_norm == chess.WHITE else -raw_delta_cp

        player_score_after_cp = score_after_cp if player_color_norm == chess.WHITE else -score_after_cp

        previous_eval_cp = self._last_player_eval_cp.get(player_color_norm)
        if previous_eval_cp is not None:
            player_delta_cp = player_score_after_cp - previous_eval_cp
        else:
            player_delta_cp = move_delta_cp
        self._last_player_eval_cp[player_color_norm] = player_score_after_cp

        top_moves = self._convert_top_moves(board_before, raw_top)
        best_move = top_moves[0] if top_moves else None
        actual_is_best = bool(best_move and best_move.get("uci") == move_uci)

        recommendation = None
        if best_move and not actual_is_best:
            recommendation = {
                "from": best_move.get("from"),
                "to": best_move.get("to"),
                "uci": best_move.get("uci"),
                "san": best_move.get("san"),
                "promotion": best_move.get("promotion")
            }

        severity_key, severity_label = self._classify_move_severity(player_color_norm, player_delta_cp, post_eval)

        analysis = {
            "pre_fen": pre_fen,
            "fen": post_fen,
            "player_color": "white" if player_color_norm == chess.WHITE else "black",
            "move_number": move_number,
            "move": {
                "uci": move_uci,
                "san": move_san,
                "from": move_from,
                "to": move_to,
                "promotion": promotion
            },
            "pre_eval": pre_eval,
            "post_eval": post_eval,
            "pre_eval_summary": self._summarize_eval(pre_eval),
            "post_eval_summary": self._summarize_eval(post_eval),
            "score_before_cp": score_before_cp,
            "score_after_cp": score_after_cp,
            "player_delta_cp": player_delta_cp,
            "player_delta_pawns": player_delta_cp / 100 if player_delta_cp is not None else None,
            "severity": severity_key,
            "severity_label": severity_label,
            "top_moves": top_moves,
            "best_move": best_move,
            "actual_is_best": actual_is_best,
            "recommendation": recommendation,
            "show_recommendation": bool(recommendation),
            "player_score_after_cp": player_score_after_cp,
            "player_score_after_display": self._format_cp(player_score_after_cp),
            "raw_delta_cp": move_delta_cp,
        }

        if best_move:
            analysis["best_move_summary"] = self._summarize_move_score(best_move)
        else:
            analysis["best_move_summary"] = None

        return analysis

    def _convert_top_moves(self, board: chess.Board, raw_list):
        top_moves = []
        for entry in raw_list:
            move_code = (entry.get("Move") or "").strip()
            if not move_code:
                continue
            move_uci = move_code.upper()
            info = {
                "uci": move_uci,
                "centipawn": entry.get("Centipawn"),
                "mate": entry.get("Mate"),
            }
            try:
                move_obj = chess.Move.from_uci(move_uci.lower())
            except ValueError:
                move_obj = None

            if move_obj and move_obj in board.legal_moves:
                info["san"] = board.san(move_obj)
                info["from"] = chess.square_name(move_obj.from_square).upper()
                info["to"] = chess.square_name(move_obj.to_square).upper()
                if move_obj.promotion:
                    info["promotion"] = chess.piece_symbol(move_obj.promotion).upper()
            else:
                info["from"] = move_uci[:2]
                info["to"] = move_uci[2:4]
                info["promotion"] = move_uci[4].upper() if len(move_uci) == 5 else None

            score_cp, mate_in_moves, winner = self._score_from_top_entry(board, entry)
            info["score_for_white_cp"] = score_cp
            info["mate_in_moves"] = mate_in_moves
            info["winner"] = winner
            top_moves.append(info)

        return top_moves

    def _normalize_evaluation(self, board: chess.Board, raw_eval):
        if not raw_eval:
            return {"type": "unknown", "score_for_white_cp": 0.0}

        eval_type = raw_eval.get("type")
        result = {"type": eval_type}

        if eval_type == "mate":
            mate_val = raw_eval.get("value", 0)
            if mate_val == 0:
                result.update({
                    "score_for_white_cp": 0.0,
                    "winner": None,
                    "mate_in_moves": None
                })
                return result

            mate_plies = abs(int(mate_val))
            mate_moves = math.ceil(mate_plies / 2)
            winner_color = board.turn if mate_val > 0 else (chess.WHITE if board.turn == chess.WHITE else chess.BLACK)
            score_for_white = 100000 - mate_moves * 100
            # if winner_color == chess.BLACK:
            #     score_for_white = -score_for_white

            result.update({
                "score_for_white_cp": -score_for_white,
                "winner": "white" if winner_color == chess.WHITE else "black",
                "mate_in_moves": mate_moves
            })
            return result

        cp_val = raw_eval.get("value", 0)
        try:
            cp_val = float(cp_val)
        except (TypeError, ValueError):
            cp_val = 0.0

        if board.turn == chess.WHITE:
            cp_val = -cp_val

        result.update({
            "score_for_white_cp": cp_val,
            "cp": cp_val
        })
        return result

    def _score_from_top_entry(self, board: chess.Board, entry):
        mate_val = entry.get("Mate")
        if mate_val is not None:
            try:
                mate_val = int(mate_val)
            except (TypeError, ValueError):
                mate_val = 0
        cp_val = entry.get("Centipawn")
        if cp_val is not None:
            try:
                cp_val = float(cp_val)
            except (TypeError, ValueError):
                cp_val = None

        if mate_val and mate_val != 0:
            mate_plies = abs(mate_val)
            mate_moves = math.ceil(mate_plies / 2)
            winner_color = board.turn if mate_val > 0 else (chess.WHITE if board.turn == chess.BLACK else chess.BLACK)
            score_for_white = 100000 - mate_moves * 100
            if winner_color == chess.BLACK:
                score_for_white = -score_for_white
            return score_for_white, mate_moves, "white" if winner_color == chess.WHITE else "black"

        score_cp = cp_val or 0.0
        if board.turn == chess.BLACK:
            score_cp = -score_cp
        return score_cp, None, None

    def _classify_move_severity(self, player_color, player_delta_cp, post_eval):
        winner = post_eval.get("winner")
        mate_in = post_eval.get("mate_in_moves")
        if winner and mate_in:
            if (winner == "white" and player_color == chess.WHITE) or (winner == "black" and player_color == chess.BLACK):
                return "brilliant", f"Winning - mate in {mate_in}"
            return "blunder", f"Blunder - allows mate in {mate_in}"

        delta = player_delta_cp or 0.0
        if delta <= -250:
            return "blunder", "Blunder"
        if delta <= -120:
            return "mistake", "Mistake"
        if delta <= -60:
            return "inaccuracy", "Inaccuracy"
        if delta >= 160:
            return "brilliant", "Brilliant move"
        if delta >= 80:
            return "good", "Strong move"
        return "correct", "Correct move"

    def _format_cp(self, cp_value):
        if cp_value is None:
            return "+0.00"
        return f"{cp_value / 100:+.2f}"

    def _summarize_eval(self, evaluation):
        if not evaluation:
            return "+0.00 for White"
        winner = evaluation.get("winner")
        mate_in = evaluation.get("mate_in_moves")
        if winner and mate_in:
            return f"Mate in {mate_in} for {winner.capitalize()}"

        score_cp = evaluation.get("score_for_white_cp")
        if score_cp is None:
            score_cp = 0.0
        return f"{self._format_cp(score_cp)} for White"

    def _summarize_move_score(self, move_info):
        if not move_info:
            return None
        winner = move_info.get("winner")
        mate_in = move_info.get("mate_in_moves")
        if winner and mate_in:
            return f"Mate in {mate_in} for {winner.capitalize()}"

        score_cp = move_info.get("score_for_white_cp")
        if score_cp is None:
            return None
        return f"{self._format_cp(score_cp)} for White"

    def _build_comment_prompt_for_training_game(self, analysis):
        if not analysis:
            return None

        color_text = "White" if analysis.get("player_color") == "white" else "Black"
        move_info = analysis.get("move", {})
        severity_label = analysis.get("severity_label", "")
        delta_pawns = analysis.get("player_delta_cp", 0.0) / 100

        lines = [
            f"We are analyzing a live chess game. {color_text} just played {move_info.get('san') or move_info.get('uci')} ({move_info.get('uci')}) on move {analysis.get('move_number')}.",
            f"Before the move, Stockfish evaluation was {analysis.get('pre_eval_summary')}. After the move it is {analysis.get('post_eval_summary')}.",
            f"This changed {color_text}'s evaluation by {delta_pawns:+.2f} pawns ({severity_label}).",
            f"Don't use 'OR' to describe impact of the move, it's look like you are not sure about the impact.",
            "Don't use general phrases like 'This move is good' or 'There is threat', or 'a critical vulnerability', explain and describe concretely the threat, the tactic, the plan, the idea, the strategy, the positional or material gain or loss, etc.",
            f"Your task is to provide concise, clear, constructive, interesting and natural chess commentary to help the player understand their move and improve their skills.",
            f"Avoid generic advice as possible, describe directly the impact of the move (and the move itself if needed); focus on the specific position and move made. Don't mention Stockfish or engine analysis explicitly.",
        ]

        best_move = analysis.get("best_move")
        if best_move and not analysis.get("actual_is_best"):
            best_label = best_move.get("san") or best_move.get("uci")
            best_summary = analysis.get("best_move_summary")
            if best_summary:
                lines.append(f"Stockfish recommended {best_label}, leading to {best_summary}.")
            else:
                lines.append(f"Stockfish recommended {best_label}.")

        lines.append("Provide at most two concise coaching sentences for the player. Explain the move's quality and give one concrete improvement suggestion if needed.")
        return "\n".join(lines)

    async def _generate_comment_text(self, analysis):
        """Generate commentary text using RAG agent when available, fallback to THEORY_ASSISTANT"""
        # Try RAG agent first if available
        if self.chess_agent:
            try:
                # Update chess agent with current position and analysis
                current_fen = analysis.get("fen")
                if current_fen:
                    self.chess_agent.update_fen_position(current_fen)
                
                # Build stockfish analysis summary for the agent
                color_text = "White" if analysis.get("player_color") == "white" else "Black"
                move_info = analysis.get("move", {})
                severity_label = analysis.get("severity_label", "")
                delta_pawns = analysis.get("player_delta_cp", 0.0) / 100
                
                stockfish_summary = f"Move: {color_text} played {move_info.get('san') or move_info.get('uci')} on move {analysis.get('move_number')}. "
                stockfish_summary += f"Before: {analysis.get('pre_eval_summary')}, After: {analysis.get('post_eval_summary')}. "
                stockfish_summary += f"Impact: {severity_label}, {delta_pawns:+.2f} pawns change."
                
                best_move = analysis.get("best_move")
                if best_move and not analysis.get("actual_is_best"):
                    best_label = best_move.get("san") or best_move.get("uci")
                    stockfish_summary += f" Best move was: {best_label}."
                
                self.chess_agent.update_stockfish_input(stockfish_summary)
                
                # Use the existing detailed prompt from _build_comment_prompt_for_training_game
                detailed_prompt = self._build_comment_prompt_for_training_game(analysis)
                
                async with self._commentary_lock:
                    response = await asyncio.to_thread(
                        self.chess_agent.chat,
                        detailed_prompt
                    )
                return response.strip() if response else None
            except Exception:
                traceback.print_exc()
                # Fall through to THEORY_ASSISTANT backup

        # Fallback to original THEORY_ASSISTANT implementation
        question = self._build_comment_prompt_for_training_game(analysis)
        if not question:
            return None
            
        try:
            async with self._commentary_lock:
                response = await asyncio.to_thread(
                    THEORY_ASSISTANT.answer,
                    question=question,
                    fen=analysis.get("fen"),
                    request_id=None
                )
        except RagServiceError:
            return None
        except Exception:
            traceback.print_exc()
            return None

        if not response:
            return None

        answer = response.get("answer") if isinstance(response, dict) else None
        if not answer:
            return None
        return answer.strip()

    async def _generate_comment_audio(self, text):
        if not text or not text.strip():
            return None
        if not os.getenv("OPENAI_API_KEY"):
            return None
        if not self._tts_model:
            return None

        try:
            async with self._tts_lock:
                return await asyncio.to_thread(self._synthesize_commentary_sync, text.strip())
        except Exception:
            traceback.print_exc()
            return None

    def _synthesize_commentary_sync(self, text):
        if not text:
            return None

        try:
            client = self._ensure_tts_client()
        except Exception:
            traceback.print_exc()
            return None

        if client is None:
            return None

        try:
            response = client.audio.speech.create(
                model=self._tts_model,
                voice=self._tts_voice,
                input=text,
                speed=1.05,  
            )
        except Exception:
            traceback.print_exc()
            return None

        audio_bytes = b""
        try:
            audio_bytes = response.read()
        except AttributeError:
            try:
                audio_bytes = b"".join(chunk for chunk in response.iter_bytes())
            except Exception:
                audio_bytes = b""

        if not audio_bytes:
            return None

        return {
            "mime": "audio/mpeg",
            "b64": base64.b64encode(audio_bytes).decode("ascii"),
        }

    def _ensure_tts_client(self):
        if self._tts_client is None:
            self._tts_client = OpenAI()
        return self._tts_client

    def _fallback_comment(self, analysis):
        move_info = analysis.get("move", {})
        severity = analysis.get("severity")
        color = analysis.get("player_color", "white").capitalize()
        move_label = move_info.get("san") or move_info.get("uci") or "the move"
        best_move = analysis.get("best_move") or {}
        best_label = best_move.get("san") or best_move.get("uci")

        if severity == "blunder":
            if best_label:
                return f"{color} blundered with {move_label}. {best_label} would keep the king safe."
            return f"{color} blundered with {move_label}. Watch for tactical shots next time."
        if severity == "mistake":
            if best_label:
                return f"{move_label} is a mistake; try {best_label} to fight for equality."
            return f"{move_label} was a mistake; aim for more active squares."
        if severity == "inaccuracy":
            if best_label:
                return f"{move_label} is slightly inaccurate. {best_label} keeps the pressure."
            return f"{move_label} is okay but there was a sharper continuation."
        if severity == "brilliant" or severity == "good":
            return f"Great job! {move_label} is a strong idea."
        if severity == "correct":
            return self._comment_for_correct_move(analysis)
        return f"{move_label} keeps the position stable. Stay alert for the next plan."

    def _comment_for_correct_move(self, analysis):
        move_info = analysis.get("move", {})
        color = analysis.get("player_color", "white").capitalize()
        move_label = move_info.get("san") or move_info.get("uci") or "the move"
        if analysis["show_recommendation"]:
            return f"{color} played {move_label}, a correct move that maintains the balance."
        return f"{color} played {move_label}, the best move in this position."

    def _build_commentary_message(self, analysis):
        if not analysis:
            return None

        score_before_cp = analysis.get("score_before_cp")
        if score_before_cp is None:
            score_before_cp = 0.0
        score_after_cp = analysis.get("score_after_cp")
        if score_after_cp is None:
            score_after_cp = 0.0
        player_delta_cp = analysis.get("player_delta_cp")
        if player_delta_cp is None:
            player_delta_cp = 0.0
        player_score_after_cp = analysis.get("player_score_after_cp")
        if player_score_after_cp is None:
            player_score_after_cp = 0.0

        evaluation = {
            "before": {
                "summary": analysis.get("pre_eval_summary"),
                "score_cp": round(score_before_cp, 1),
                "score_pawns": round(score_before_cp / 100, 2)
            },
            "after": {
                "summary": analysis.get("post_eval_summary"),
                "score_cp": round(score_after_cp, 1),
                "score_pawns": round(score_after_cp / 100, 2)
            },
            "player_delta_cp": round(player_delta_cp, 1),
            "player_delta_pawns": round(player_delta_cp / 100, 2),
            "player_score_after_cp": round(player_score_after_cp, 1),
            "player_score_after_display": analysis.get("player_score_after_display"),
        }

        payload = {
            "timestamp": time.time(),
            "fen": analysis.get("fen"),
            "player_color": analysis.get("player_color"),
            "move_number": analysis.get("move_number"),
            "move": analysis.get("move"),
            "severity": analysis.get("severity"),
            "severity_label": analysis.get("severity_label"),
            "evaluation": evaluation,
            "comment": analysis.get("comment"),
            "best_move": analysis.get("best_move"),
            "top_moves": analysis.get("top_moves"),
            "show_recommendation": analysis.get("show_recommendation"),
            "recommendation": analysis.get("recommendation"),
            "actual_is_best": analysis.get("actual_is_best"),
            "best_move_summary": analysis.get("best_move_summary"),
        }

        audio_payload = analysis.get("audio")
        if audio_payload:
            payload["audio"] = audio_payload

        return payload

    def connect_user(self, info):
        """
        Connect a user with the given pseudo.
        """
        self.client_pseudo = info["pseudo"]
        self.get_chesscom_profil({}, _preloaded=False)

        if self.client_profil is None:
            asyncio.create_task(self.socket.broadcast(protocol.Toast("error", "Error while connecting user").to_json()))
            asyncio.create_task(self.socket.broadcast(protocol.LoadingCommand("hide").to_json()))
            return
            
        asyncio.create_task(self.socket.broadcast(protocol.NavigationCommand(url="html/home.html").to_json()))

if __name__ == "__main__":
    Server = Server()
    asyncio.run(Server.run())
