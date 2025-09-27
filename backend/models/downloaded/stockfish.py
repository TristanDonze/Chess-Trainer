from stockfish import Stockfish
from models.engine import Engine
import chess

class StockfishAI(Engine):
    """
    Chess AI that uses the Stockfish engine.
    """

    __author__ = "Downloaded"
    __description__ = "Chess AI that uses the Stockfish engine."

    def __init__(self, stockfish_path="/opt/homebrew/bin/stockfish", skill_level=20, depth=10, think_time=100, *args, **kwargs):
        """
        Initializes the Stockfish AI.
        
        :param stockfish_path: Path to the Stockfish binary.
        :param skill_level: Stockfish skill level (0 to 20).
        :param depth: Search depth for Stockfish.
        :param think_time: Time in seconds for Stockfish to think per move.
        """
        super().__init__(*args, **kwargs)
        import os
        if not os.path.exists(stockfish_path):
            raise FileNotFoundError("Stockfish binary not found at: " + stockfish_path)
        self.stockfish = Stockfish(stockfish_path, depth=depth)
        self.stockfish.set_skill_level(skill_level)
        self.think_time = think_time

    def play(self) -> chess.Move:
        """
        Uses Stockfish to determine the best move.
        
        :return: The best move as a chess.Move object.
        """
        board_fen = self.game.board.fen()
        self.stockfish.set_fen_position(board_fen)
        # Get best move from Stockfish
        best_move_uci = self.stockfish.get_best_move_time(self.think_time)
        if best_move_uci:
            return chess.Move.from_uci(best_move_uci)
        return None
