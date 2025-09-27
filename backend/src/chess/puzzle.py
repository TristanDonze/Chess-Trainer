from src.chess.game import Game

import chess

class Puzzle:
    """
    Represents a puzzle. (lichess.org format)

    https://database.lichess.org/#puzzles
    """

    def __init__(self):
        self.id: str = None
        """lichess.org puzzle id"""

        self.fen: str = None
        """FEN representation of the game"""

        self.moves: list[chess.Move] = None
        """List of moves to solve the puzzle"""

        self.rating: int = None
        """Rating of the puzzle: 100 * (upvotes - downvotes)/(upvotes + downvotes)"""

        self.rating_deviation: int = None

        self.popularity: int = None

        self.nb_plays: int = None

        self.themes: list[str] = None

        self.game_url: str = None

        self.opening_tags: str = None

        self.game: Game = None

    def __repr__(self):
        return f"Puzzle({self.id}, {self.rating} : {self.popularity})"
    
    def __str__(self):
        return self.__repr__()

    def load(self, puzzle_fen: str) -> "Puzzle":
        """
        Load a puzzle from a FEN string.

        puzzle_fen: str
            The FEN representation of the puzzle.

        Information
        -----------
        Puzzle fen format:
        PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags
        00sHx,q3k1nr/1pp1nQpp/3p4/1P2p3/4P3/B1PP1b2/B5PP/5K2 b k - 0 17,e8d7 a2e6 d7d8 f7f8,1760,80,83,72,mate mateIn2 middlegame short,https://lichess.org/yyznGmXs/black#34,Italian_Game Italian_Game_Classical_Variation
        """
        if type(puzzle_fen) is str: puzzle_fen = puzzle_fen.split(',')
        elif type(puzzle_fen) in [list, tuple]: ...
        else: raise Exception(f"Invalid type for puzzle_fen, must be str, list or tuple not <{type(puzzle_fen)}>")

        self.id = puzzle_fen[0]
        self.fen = puzzle_fen[1]
        self.moves = puzzle_fen[2].split(' ')
        self.rating = int(puzzle_fen[3])
        self.rating_deviation = int(puzzle_fen[4])
        self.popularity = int(puzzle_fen[5])
        self.nb_plays = int(puzzle_fen[6])
        self.themes = puzzle_fen[7].split(' ')
        self.game_url = puzzle_fen[8]
        self.opening_tags = puzzle_fen[9]

        self.game = Game().load(self.fen)
        self.moves = [chess.Move.from_uci(move) for move in self.moves]
        self.game.move(self.moves[0])
        self.moves = self.moves[1:]

        self.game.checkmate = None if not self.game.board.is_checkmate() else (chess.WHITE if self.game.board.turn == chess.BLACK else chess.BLACK)
        self.game.draw = (self.game.board.is_stalemate() or self.game.board.is_insufficient_material()) and not self.game.board.is_checkmate() 
        self.game.king_in_check = {chess.WHITE: self.game.board.is_check() and self.game.board.turn == chess.WHITE, chess.BLACK: self.game.board.is_check() and self.game.board.turn == chess.BLACK}
        self.game.last_player = chess.WHITE if self.game.board.turn == chess.BLACK else chess.BLACK

        return self
