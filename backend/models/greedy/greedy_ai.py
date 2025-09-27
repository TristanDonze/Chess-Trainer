from models.engine import Engine
import chess
import numpy as np

class GreedyAI(Engine):
    """
    Optimized Greedy AI that plays as strongly as possible with a single-move evaluation.
    """

    __author__ = "Enzo Pinchon"
    __description__ = "Optimized Greedy AI that plays as strongly as possible with a single-move evaluation."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_move_piece = None
        self.last_last_move_piece = None

    def play(self, topN=-1) -> chess.Move:
        """
        Select the best move based on a greedy evaluation function.
        """
        all_moves = list(self.game.board.legal_moves)
        if not all_moves:
            return None  # No legal moves (stalemate or checkmate)

        if topN > 0:
            return sorted(all_moves, key=self.get_action_score, reverse=True)[:min(topN, len(all_moves))]
        
        best_move = max(all_moves, key=self.get_action_score)
        self.last_last_move_piece = self.last_move_piece
        self.last_move_piece = self.game.get_piece(best_move.from_square).piece_type
        return best_move

    def get_action_score(self, move: chess.Move) -> float:
        """
        Evaluates a move using an optimized greedy function.
        """
        board = self.game.board
        value = 0

        from_square = move.from_square
        to_square = move.to_square
        from_piece = self.game.get_piece(from_square)
        captured_piece = self.game.get_piece(to_square)

        _from_coords = self.game.get_coords(from_square)
        _to_coords = self.game.get_coords(to_square)

        if not from_piece:
            return -1000  # Invalid move (should never happen)

        piece_type = from_piece.piece_type
        color = from_piece.color

        # Piece value bonus (scaled dynamically based on game phase)
        piece_value = self.game.PIECE_VALUES[piece_type]
        value += piece_value

        # Capture evaluation (favor good trades)
        if captured_piece:
            value += self.game.PIECE_VALUES[captured_piece.piece_type] * 9

        # Avoid moving the same piece twice in a row (unless it's a strong move)
        if self.last_move_piece == piece_type:
            value -= 20
        
        if self.last_last_move_piece == piece_type:
            value -= 10

        # **Piece Development - Force pieces to move from initial position**
        initial_ranks = {chess.WHITE: 1, chess.BLACK: 6}
        if chess.square_rank(from_square) == initial_ranks[color]:
            value += 5  # Encourage moving pieces out of the back rank

        # **Positional Bonuses**
        # Encourage castling
        if piece_type == chess.KING and abs(chess.square_file(from_square) - chess.square_file(to_square)) == 2:
            value += 15  # Castling is very important

        # Encourage center control
        if to_square in chess.SquareSet(chess.BB_CENTER):
            value += 5

        # Avoid retreating (unless necessary)
        if from_square in chess.SquareSet(chess.BB_CENTER) and to_square not in chess.SquareSet(chess.BB_CENTER):
            value -= 5

        # encourage moving pieces away from the edges
        if to_square in self.game.BB_EDGE or from_square in self.game.BB_EDGE:
            value -= 5

        # **Piece-Specific Bonuses**
        if piece_type == chess.PAWN:
            value += 1 + (to_square in chess.SquareSet(chess.BB_RANK_8 | chess.BB_RANK_1)) * 5  # Encourage promotion
            if chess.square_rank(to_square) >= 6:  # Encourage advancing pawns
                value += 3
            # encourage moving * 2 pawns
            if abs(chess.square_rank(from_square) - chess.square_rank(to_square)) == 2:
                value += 1

            # encourage moving pawn in endgame
            if len(board.pieces(chess.PAWN, color)) < 4 and len(board.pieces(chess.QUEEN, color)) == 0:
                value += 6

        elif piece_type == chess.KNIGHT:
            value += 3
            if to_square in self.game.BB_EDGE:
                value -= 6  # Knights are weak on edges
            if from_square in self.game.BB_EDGE:
                value += 3
        elif piece_type == chess.BISHOP:
            value += 3 + (len(list(board.attacks(to_square))) / 3)
            # encourage long moves
            value += (abs(_from_coords[0] - _to_coords[0]) + abs(_from_coords[1] - _to_coords[1])) / 4.5

            # avoid bishops on middle bottom
            if to_square in chess.SquareSet(chess.BB_RANK_1) and chess.square_file(to_square) in [2, 3, 4, 5]:
                value -= 10

        elif piece_type == chess.ROOK:
            value += 1
            # encourage long moves
            value += (abs(_from_coords[0] - _to_coords[0]) + abs(_from_coords[1] - _to_coords[1])) / 3.5

            # don't move if we still can castle
            if color == chess.WHITE:
                if from_square == chess.A1 and board.has_kingside_castling_rights(chess.WHITE):
                    value -= 20
                if from_square == chess.H1 and board.has_queenside_castling_rights(chess.WHITE):
                    value -= 20
            else:
                if from_square == chess.A8 and board.has_kingside_castling_rights(chess.BLACK):
                    value -= 20
                if from_square == chess.H8 and board.has_queenside_castling_rights(chess.BLACK):
                    value -= 20


        elif piece_type == chess.QUEEN:
            # Stronger early-game penalty
            if board.fullmove_number < 15:  
                value -= 20  # Really discourage early queen moves
            
            # Encourage developing other pieces first
            undeveloped_pieces = sum(1 for sq in chess.SquareSet(chess.BB_RANK_1 if color == chess.WHITE else chess.BB_RANK_8)
                                    if board.piece_at(sq) and board.piece_at(sq).color == color)
            value -= undeveloped_pieces * 3  # The less developed pieces, the harsher the penalty

        elif piece_type == chess.KING:
            value -= 50  # Avoid moving the king unless necessary

        # **Promotion Bonus**
        if move.promotion:
            value += (self.game.PIECE_VALUES[move.promotion] - 1) * 3

        # **Tactical Awareness**
        attackers = len(board.attackers(not color, to_square)) + 1
        defenders = len(board.attackers(color, to_square))

        if attackers > 1:
            value -= self.game.PIECE_VALUES[piece_type] * 8 # trade cost

        attackers_from = len(board.attackers(not color, from_square)) + 1

        if attackers > defenders:
            value -= self.game.PIECE_VALUES[piece_type] * 5  # Avoid hanging pieces

        if attackers_from > 0:
            value += self.game.PIECE_VALUES[piece_type] * 5  # Avoid undefended pieces

        # Simulate move
        board.push(move)

        # **Checkmate & Stalemate Detection**
        enemy_king_square = board.king(not color)
        enemy_king_moves_before = [m for m in board.legal_moves if m.from_square == enemy_king_square]
        is_check = board.is_check()
        is_checkmate = board.is_checkmate()
        is_stalemate = board.is_stalemate()

        if is_checkmate:
            value = 1e6  # Winning move (checkmate)
        elif is_stalemate:
            value -= 1e6  # Avoid stalemate unless losing

        # **Check Bonus**
        if is_check:
            value += 3  # Encourage checks

        # **Reduce Enemy King Mobility** (Restored from your code)
        enemy_king_square = board.king(not color)
        enemy_king_moves_after = [m for m in board.legal_moves if m.from_square == enemy_king_square]
        king_mobility_reduction = len(enemy_king_moves_before) - len(enemy_king_moves_after)
        value += king_mobility_reduction * 5  # More reduction = better move
        if is_check:
            value += king_mobility_reduction  # Bonus if check also reduces mobility

        board.pop()  # Undo move simulation

        return value
