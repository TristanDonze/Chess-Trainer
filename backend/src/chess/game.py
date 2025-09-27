try: from .player import Player
except ImportError: from player import Player

import io
import chess
import chess.pgn
import numpy as np

class Game:
    BB_EDGE = chess.SquareSet(chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_FILE_A | chess.BB_FILE_H)

    PIECE_VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 10 # not really important
    }

    def __init__(self):

        self.board = None

        # Players (can be AI or human)
        self.white = None
        self.black = None

        self.ia_move_handler = None
        self.draw = None

        self.checkmate = None
        self.king_in_check = {chess.WHITE: False, chess.BLACK: False}
        self.last_player = chess.BLACK

        self.one_hot_idx = {
            'K': 0, 'Q': 1, 'N': 2, 'B': 3, 'R': 4, 'P': 5,  # White pieces
            'k': 6, 'q': 7, 'n': 8, 'b': 9, 'r': 10, 'p': 11  # Black pieces
        }

        self.history = []
        self.winner = None

    def __str__(self):
        return self.board.__str__()
    
    def __repr__(self):
        return self.board.__repr__()

    def fen(self):
        return self.board.fen()
    
    def _update_game_state(self):
        if self.board.is_checkmate():
            self.checkmate = not self.board.turn # TODO update ?
        else:
            self.checkmate = None

        self.draw = self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition()
        self.king_in_check = {
            chess.WHITE: self.board.is_check() and self.board.turn == chess.WHITE,
            chess.BLACK: self.board.is_check() and self.board.turn == chess.BLACK
        }
        self.last_player = chess.WHITE if self.board.turn == chess.BLACK else chess.BLACK

        if self.board.is_checkmate() and self.winner is None:
            self.winner = self.last_player
    
    def rewind(self, nb_moves):
        for _ in range(nb_moves):
            self.board.pop()

        self._update_game_state()

    
    def reverse(self):
        """
        Return a new instance of Game with the exact reversed position.
        """
        new_game = Game()
        new_game.board = self.board.mirror()  # Flip the board position
        new_game.last_player = not self.last_player  # Swap turn

        # Copy over relevant attributes
        new_game.white = self.white
        new_game.black = self.black
        new_game.ia_move_handler = self.ia_move_handler
        new_game.draw = self.draw
        new_game.checkmate = None if self.checkmate is None else not self.checkmate
        new_game.king_in_check = {
            chess.WHITE: self.king_in_check[chess.BLACK],
            chess.BLACK: self.king_in_check[chess.WHITE]
        }
        new_game.history = self.history.copy() # Copy the move history not REVERSED: TODO ?
        new_game.winner = None if self.winner is None else not self.winner

        return new_game
    
    def copy(self):
        """
            Return a new instance of the game with the exact same position
        """
        cpy = Game().load(self.fen())
        cpy.history = self.history.copy()
        cpy.board = self.board.copy()
        cpy.white = self.white
        cpy.black = self.black
        cpy.ia_move_handler = self.ia_move_handler
        return cpy

    def _load_fen(self, fen):
        self.board = chess.Board(fen)
        self.draw = self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition()
        self.king_in_check = {chess.WHITE: self.board.is_check() and self.board.turn == chess.WHITE, chess.BLACK: self.board.is_check() and self.board.turn == chess.BLACK}
        self.last_player = chess.WHITE if self.board.turn == chess.BLACK else chess.BLACK
        self.is_checkmate = self.last_player if self.board.is_checkmate() else None
        self.winner = self.last_player if self.board.is_checkmate() else None
        return self
    
    def _load_pgn(self, pgn_string):
        """
        Load a PGN game from a string.
        :param pgn_string: PGN game as a string
        :type pgn_string: str
        :return: self
        :rtype: Game
        """
        pgn_io = io.StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)

        if game is None:
            raise ValueError("Invalid PGN format")

        self.board = game.board()
        for i, move in enumerate(game.mainline_moves()):
            self.board.push(move)  # Play all moves
            self.history.append(move)

        # Check game state
        if self.board.is_checkmate():
            self.checkmate = not self.board.turn  # The player to move is in checkmate (loser)
        else:
            self.checkmate = None  # No checkmate

        self.draw = self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition()
        self.king_in_check = {
            chess.WHITE: self.board.is_check() and self.board.turn == chess.WHITE,
            chess.BLACK: self.board.is_check() and self.board.turn == chess.BLACK
        }
        self.last_player = chess.WHITE if self.board.turn == chess.BLACK else chess.BLACK
        self.winner = self.last_player
        return self

       
    def load(self, data, format="fen"):
        """
        Load a game from a string.
        :param data: data to load
        :type data: str
        :param format: format of the data (fen or pgn)
        :type format: str
        :return: self
        :rtype: Game
        """
        if format == "fen":
            return self._load_fen(data)
        elif format == "pgn":
            return self._load_pgn(data)
        else:
            raise Exception("Invalid format")
    
    def move(self, move: chess.Move):
        # check if the move is legal
        if move not in self.board.legal_moves:
            raise Exception("Illegal move: " + str(move))
        
        self.board.push(move)

        # check for draw
        if self.board.is_stalemate():
            self.draw = "stalemate"
        elif self.board.is_insufficient_material():
            self.draw = "insufficient material"
        elif self.board.is_seventyfive_moves():
            self.draw = "seventyfive moves"
        elif self.board.is_fivefold_repetition():
            self.draw = "fivefold repetition"
        elif self.board.is_checkmate():
            self.checkmate = self.last_player
            self.winner = self.last_player
        
        if self.board.is_check():
            self.king_in_check[self.last_player] = True
        else:
            self.king_in_check[self.last_player] = False
        self.king_in_check[not self.last_player] = False

        self.last_player = chess.WHITE if self.last_player == chess.BLACK else chess.BLACK
    
    def play_engine_move(self):
        """
        Get the move from the AI.
        """
        if self.checkmate is not None or self.draw is not None: return

        if self.board.turn == chess.WHITE and self.white.is_engine:
            move = self.white.play()
        elif self.board.turn == chess.BLACK and self.black.is_engine:
            move = self.black.play()
        else: return
        
        if move is None: # surrender
            raise Exception("No legal moves")
        
        self.move(move)

        if self.ia_move_handler is not None: self.ia_move_handler(move)

    def one_hot(self):
        """ Converts the chess board to a 8x8x12 one-hot encoded representation. """

        board_matrix = np.zeros((8, 8, 12), dtype=int)
        board_str = str(self.board).replace("\n", " ").split()

        for i in range(8):
            for j in range(8):
                piece = board_str[i * 8 + j]
                index = self.one_hot_idx.get(piece)
                if index is not None:
                    board_matrix[i, j, index] = 1

        return board_matrix
    
    def one_hot_to_fen(self, one_hot_board):
        """ Converts a 8x8x13 one-hot encoded board back to FEN notation. """
        fen_rows = []

        for row in one_hot_board:
            fen_row = ""
            empty_count = 0

            for square in row:
                piece_index = np.argmax(square)  # Get the index of the 1 in the one-hot vector
                piece = self.one_hot_idx[piece_index]

                if piece == '.':
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    fen_row += piece

            if empty_count > 0:
                fen_row += str(empty_count)

            fen_rows.append(fen_row)

        fen = "/".join(fen_rows) + " w - - 0 1"  # Default values for turn, castling, en passant, etc.
        return fen
    
    def get_score(self, color):
        """
            Return a score, positive if <color> is winning, negative otherwise.
            The score depends of the material balance.
        """
        score = sum(
            self.PIECE_VALUES[piece] * (
                len(self.board.pieces(piece, color)) - len(self.board.pieces(piece, not color))
            )
            for piece in self.PIECE_VALUES
        )

        return score
    
    def get_box_idx(self, *args) -> chess.Piece:
        """
        Get a piece from the board.
        """

        # we want to transform args into a string like "a1"

        if len(args) == 1:
            coords = args[0]
            if type(coords) is int: # already a box index
                return coords
        else:
            coords = (args[0], args[1])

        if type(coords) == tuple:
            x, y = coords
            if type(x) == int:
                x = chr(x + 65)
                y += 1
            coords = x + str(y)

        box_idx = chess.parse_square(coords.lower())
        return box_idx
    
    def get_coords(self, *args) -> tuple:
        """
        Get the coordinates of a box.
        
        :param args: info of the box
        :type args: tuple or str
        :return: coordinates
        :rtype: tuple (int, int)
        """

        if len(args) == 1:
            coords = args[0]
            if type(coords) is tuple: return coords
            if type(coords) is int:
                x = coords % 8
                y = coords // 8
                return (x, y)
        else:
            coords = (args[0], args[1])

        if type(coords) == str:
            x, y = coords[0], int(coords[1])
            x = ord(x) - 65
            y -= 1
            coords = (x, y)
        return coords
    
    def get_box_label(self, *args) -> str:
        """
        Get the label of a box.
        """

        if len(args) == 1:
            coords = args[0]
            if type(coords) is str: return coords
            else: # idx
                x = coords % 8
                y = coords // 8
                coords = (x, y)

        else:
            coords = (args[0], args[1])

        if type(coords) == tuple:
            x, y = coords
            if type(x) == int:
                x = chr(x + 65)
                y += 1
            coords = x + str(y)
        return coords

    def get_piece(self, *args) -> chess.Piece:
        """
        Get a piece from the board using coordinates.

        :param args: coordinates of the piece
        :type args: tuple or str
        :return: the piece
        :rtype: chess.Piece
        """
        if self.board is None: raise Exception("No board loaded")

        coords = self.get_box_idx(*args)
        return self.board.piece_at(coords)
    
    def find_piece_box(self, piece_to_find: chess.Piece, color, _exception=True) -> int:
        """
        Find the box of a piece.
        """
        for square, piece in self.board.piece_map().items():
            if piece.piece_type == piece_to_find and piece.color == color:
                return square
        if _exception: raise Exception("Piece not found")
        return None
    
    def get_possible_moves(self, *args) -> list:
        """
        Get the possible moves of a piece knowing its coordinates.

        :param args: coordinates of the piece
        :type args: tuple or str
        :return: list of possible moves
        :rtype list[chess.Move]
        """
        if self.board is None: raise Exception("No board loaded")

        coords = self.get_box_idx(*args)
        return [move for move in self.board.legal_moves if move.from_square == coords]

    def play(self, white, black, fen=None):
        """
        Play a game between two players.
        """

        self.white = white
        self.black = black

        if issubclass(type(white), Player):
            white.color = chess.WHITE
            white.game = self
        if issubclass(type(black), Player):
            black.color = chess.BLACK
            black.game = self

        if fen is not None:
            self.load(fen)
        else:
            self.board = chess.Board()

        return self

    def is_game_over(self):
        return self.checkmate is not None or self.draw
    
    @staticmethod
    def reverse_move(uci_move):
        """
        Reverse a (UCI) move (e.g., "e2e4" becomes "e7e5").
        """
        auto_cast = False
        if type(uci_move) is chess.Move:
            auto_cast = True
            uci_move = uci_move.uci()

        x1 = chess.square_name(chess.square_mirror(chess.parse_square(uci_move[:2])))
        x2 = chess.square_name(chess.square_mirror(chess.parse_square(uci_move[2:4])))
        move_reversed = x1 + x2
        if len(uci_move) == 5:
            move_reversed += uci_move[4]

        return move_reversed if not auto_cast else chess.Move.from_uci(move_reversed)



if __name__ == "__main__":
    game = Game()
    game.play(white=Player(False), black=Player(False))
    print(game.get_piece('A', 1), "==", game.get_piece('A1'))
    print(game)

    moves = game.get_possible_moves('a2')
    print("all moves of A2:", moves)
    print("captures:", [game.board.san(move) for move in moves if game.board.is_capture(move)])
    print("checks:", [game.board.san(move) for move in moves if game.board.gives_check(move)])

    game.move(chess.Move.from_uci('d2d4'))
    game.move(chess.Move.from_uci('d7d6'))
    game.move(chess.Move.from_uci('d4d5'))
    game.move(chess.Move.from_uci('c7c5'))

    moves = game.get_possible_moves("D5")
    print(game)

    print("all moves of D5:", moves)
    print("captures:", [game.board.san(move) for move in moves if game.board.is_capture(move)])

