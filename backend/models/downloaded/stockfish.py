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
    
    def evaluate(self, game) -> dict:
        """
        Evaluate the current position with Stockfish.

        Returns a dict:
        {
            'cp': int | None,                # centipawns from White's POV (positive = White better)
            'white_win_pct': float | None,   # heuristic win prob for White in [0,100]
            'black_win_pct': float | None,   # 100 - white_win_pct (if available)
            'white_mate_in': int | None,     # mate in N moves for White (if forced)
            'black_mate_in': int | None,     # mate in N moves for Black (if forced)
        }
        Notes:
        - When a forced mate is reported, cp is None.
        - Win percentages are heuristic, not calibrated; do not use for scoring.
        """
        board_fen = game.board.fen()
        self.stockfish.set_fen_position(board_fen)
        evaluation = self.stockfish.get_evaluation()

        side = board_fen.split()[1]  # 'w' or 'b'

        out = {
            'white_win_pct': None,
            'black_win_pct': None,
            'white_mate_in': None,
            'black_mate_in': None,
            'cp': None,
        }

        if evaluation.get('type') != 'mate':
            cp = int(evaluation.get('value', 0))  # Stockfish cp is from side-to-move POV
            # if side == 'b':
            #     cp = -cp  # convert to White's POV
            out['cp'] = cp

            # Heuristic win prob from cp (logistic; scale ~250 cp ≈ 75/25 split)
            # Adjust 250 to your taste / calibration data.
            k = 250.0
            p_white = 1.0 / (1.0 + pow(10.0, -cp / k))
            out['white_win_pct'] = max(0.0, min(100.0, 100.0 * p_white))
            out['black_win_pct'] = 100.0 - out['white_win_pct']
            return out

        # Mate score: value is plies (signed), from side-to-move POV
        ply = int(evaluation.get('value', 0))
        if ply == 0:
            return out  # ignore pathological zero

        if ply > 0:
            winner = side                 # side to move mates
            mate_moves = (ply + 1) // 2   # ceil(plies/2)
        else:
            winner = 'w' if side == 'b' else 'b'
            mate_moves = ((-ply) + 1) // 2

        if winner == 'w':
            out['white_win_pct'] = 100.0
            out['black_win_pct'] = 0.0
            out['white_mate_in'] = mate_moves
        else:
            out['white_win_pct'] = 0.0
            out['black_win_pct'] = 100.0
            out['black_mate_in'] = mate_moves

        return out

