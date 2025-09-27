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
    
    def evaluate(self, game) -> tuple[float, float]:
        """
        Evaluates the current board position using Stockfish.
        
        :return: A tuple containing (centipawn evaluation, mate in N moves).
                 Centipawn evaluation is positive if White is better, negative if Black is better.
                 Mate in N moves is positive if White can mate in N moves, negative if Black can mate in N moves.
        """
        board_fen = game.board.fen()
        self.stockfish.set_fen_position(board_fen)
        evaluation = self.stockfish.get_evaluation()

        side = board_fen.split()[1]            # 'w' ou 'b'

        out = {
            'white_win_pct': None,
            'black_win_pct': None,
            'white_mate_in': None,
            'black_mate_in': None,
            'cp': None,
        }

        if evaluation.get('type') != 'mate':
            cp = evaluation.get('value', 0)   # centipawns (signé, point de vue du camp au trait)
            if side == 'b':
                cp = -cp                       # on inverse le signe si c'est aux Noirs de jouer
            out['cp'] = cp
            out['white_win_pct'] = max(0, min(100, 50 + cp / 10))  # approximation très grossière
            out['black_win_pct'] = 100 - out['white_win_pct']

            return out  # pas de mate forcé détecté

        ply = int(evaluation.get('value', 0))  # mate en N demis-coups (signé, point de vue du camp au trait)
        if ply == 0:
            return out  # cas pathologique, on ignore

        if ply > 0:
            winner = side                     # le camp au trait mate
            mate_moves = (ply + 1) // 2       # ceil(ply/2)
        else:
            winner = 'w' if side == 'b' else 'b'  # l'autre camp mate
            mate_moves = ((-ply) + 1) // 2

        if winner == 'w':
            out['white_win_pct'] = 100
            out['white_mate_in'] = mate_moves
        else:
            out['black_win_pct'] = 100
            out['black_mate_in'] = mate_moves
        return evaluation
