
import time
from src.utils.socket_server import ServerSocket
from src.utils.extract_chesscom import get_chesscom_data

import src.utils.message as protocol

from meta import AVAILABLE_MODELS

from src.chess.game import Game
from src.chess.player import Player
from models.engine import Engine
from src.rag import THEORY_ASSISTANT, RagServiceError

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

        for model in AVAILABLE_MODELS.values():
            try: getattr(model, "__author__")
            except: raise Engine.UndefinedAuthorError(model, f"Model {model.__name__} has no author")

            try: getattr(model, "__description__")
            except: raise Engine.UndefinedDescriptionError(model, f"Model {model.__name__} has no description")

            try: getattr(model, "play")
            except: raise Engine.UndefinedPlayMethodError(model, f"Model {model.__name__} has no play method")

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
            move = chess.Move.from_uci(info["start"].lower() + info["end"].lower() + (info.get("promote", "") or "").lower())
            self.focused_game.move(move)
        except Exception as e:
            asyncio.create_task(self.socket.broadcast(protocol.Message(str, "error"(e)).to_json()))
            traceback.print_exc()
            return

        ctn = {
            "FEN": self.focused_game.fen(),
            "king_in_check": self.focused_game.king_in_check[chess.WHITE] or self.focused_game.king_in_check[chess.BLACK],
            "checkmate": "w" if self.focused_game.checkmate == chess.WHITE else "b" if self.focused_game.checkmate == chess.BLACK else None,
            "draw": self.focused_game.draw,
        }

        asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "confirm-move").to_json()))
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
            ctn = {
                "elo": elo,
                "nb_games": len(games),
                "games": games
            }
            self.client_profil = ctn
            asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "chesscom-profil").to_json()))
        except Exception as e:
            asyncio.create_task(self.socket.broadcast(protocol.Message(str(e), "error").to_json()))
            traceback.print_exc()

    async def analyse_game(self, client, info):
        """
        Analyze a game with the given PGN.
        """
        # 1. load the PGN into a game object
        self.focused_game = Game()
        self.focused_game.load(info["game"]["pgn"], format="pgn")
        
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
            await screen.init(["Analyze gamme"])
            await screen.step("Analyze gamme", 0)

            for idx, move in enumerate(self.focused_game.history):
                self.focused_game.move(move)

                evaluation = stockfish.evaluate(self.focused_game)
                moves["white" if idx % 2 == 0 else "black"].append({
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
                    **evaluation
                })

                await screen.step("Analyze gamme", (idx + 1) / len(self.focused_game.history), info=f"Analyzing move {idx + 1}/{len(self.focused_game.history)}", eta_s=(len(self.focused_game.history) - idx) * 2)

        ctn = {
            "moves": moves,
            "result": "white - " + info["game"]["white"]["result"] if info["game"]["white"]["result"] in ["win", "checkmated"] else "black - " + info["game"]["black"]["result"]
        }
        asyncio.create_task(self.socket.broadcast(protocol.Message(ctn, "game-analyzed").to_json()))

    async def handle_theory_question(self, client, info):
        """Answer a theory question using the OpenAI assistant."""
        info = info or {}
        question = (info.get("question") or "").strip()
        request_id = info.get("request_id")
        fen = info.get("fen") or None

        if not question:
            payload = {
                "id": request_id,
                "error": "Question cannot be empty."
            }
            await self.socket.send(client, protocol.Message(payload, "theory-answer"))
            return

        try:
            answer = THEORY_ASSISTANT.answer(question=question, fen=fen, request_id=request_id)
            payload = {
                **answer,
                "fen": fen,
            }
        except RagServiceError as exc:
            payload = {
                "id": request_id,
                "error": str(exc),
                "fen": fen,
            }
        except Exception as exc:
            traceback.print_exc()
            payload = {
                "id": request_id,
                "error": f"Unexpected error: {exc}",
                "fen": fen,
            }

        await self.socket.send(client, protocol.Message(payload, "theory-answer"))

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
