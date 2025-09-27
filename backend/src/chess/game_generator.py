try: from src.chess.game import Game
except ImportError: from game import Game

import chess
import random

class GameGenerator:

    def __init__(self):
        self.white_pieces = [
            chess.Piece(chess.PAWN, chess.WHITE),
            chess.Piece(chess.KNIGHT, chess.WHITE),
            chess.Piece(chess.BISHOP, chess.WHITE),
            chess.Piece(chess.ROOK, chess.WHITE),
            chess.Piece(chess.QUEEN, chess.WHITE),
            # chess.Piece(chess.KING, chess.WHITE)
        ]

        self.black_pieces = [
            chess.Piece(chess.PAWN, chess.BLACK),
            chess.Piece(chess.KNIGHT, chess.BLACK),
            chess.Piece(chess.BISHOP, chess.BLACK),
            chess.Piece(chess.ROOK, chess.BLACK),
            chess.Piece(chess.QUEEN, chess.BLACK),
            # chess.Piece(chess.KING, chess.BLACK)
        ]

    def generate(self, depth=100): 
            # nb_white_pieces=16, nb_black_pieces=16, 
            # white_promotion_proba=0.1, black_promotion_proba=0.1,
            # checkmate_proba=0.05, draw_proba=0.05, check_proba=0.1,
            # white_to_move=True) -> Game:
        """
        ...
        """

        # need_white_promotion = random.random() < white_promotion_proba
        # need_black_promotion = random.random() < black_promotion_proba
        # need_checkmate = random.random() < checkmate_proba
        # need_draw = random.random() < draw_proba and not need_checkmate
        # need_check = random.random() < check_proba and not need_draw

        # assert nb_white_pieces + nb_black_pieces <= 32, "Maximum 32 pieces are allowed"
        # assert nb_white_pieces + nb_black_pieces >= 2, "At least 2 pieces are required"

        board = chess.Board()

        # play random moves until the board is in the desired state
        for _ in range(depth):
            if board.is_checkmate() or board.is_stalemate():
                break
            move = random.choice(list(board.legal_moves))
            board.push(move)

        game = Game().load(board.fen())
        game.checkmate = None if not board.is_checkmate() else (chess.WHITE if board.turn == chess.BLACK else chess.BLACK)
        game.draw = None if not (board.is_stalemate() or board.is_insufficient_material()) or board.is_checkmate() else True # draw, not game format, but easier for learning
        game.king_in_check = {chess.WHITE: board.is_check() and board.turn == chess.WHITE, chess.BLACK: board.is_check() and board.turn == chess.BLACK}
        game.last_player = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
        return game
    
if __name__ == "__main__":
    g = GameGenerator()

    games = [g.generate() for _ in range(10_000)]
    nb_checkmate = sum(game.board.is_checkmate() for game in games)
    nb_draw = sum(game.board.is_stalemate() for game in games)
    nb_check = sum(game.board.is_check() for game in games)
    is_correct = sum(int(game.board.is_valid()) for game in games)

    print(f"Checkmate: {nb_checkmate}")
    print(f"Draw: {nb_draw}")
    print(f"Check: {nb_check}")
    print(f"Is correct: {is_correct}")

    print(games[3])
    print(games[10])

