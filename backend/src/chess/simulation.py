from .game import Game
import chess
import random

class Simulation:
    def __init__(self, game: Game):
        self.initial_game = game
        self.game: Game = Game().load(game.fen())  # Avoid unnecessary Game() instantiation
        self.checkpoints = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.checkpoints.clear()  # More efficient than iterating over keys
        del self.game

    def checkpoint(self, name: str):
        self.checkpoints[name] = self.game.fen()

    def rollback(self, name: str):
        if (fen := self.checkpoints.get(name)):  # Prevent KeyError
            self.game = Game.load(fen)

    def reset(self):
        self.game = self.game.load(self.initial_game.fen())
        self.game.checkmate = self.initial_game.checkmate
        self.game.draw = self.initial_game.draw
        self.game.king_in_check = self.initial_game.king_in_check.copy()
        self.game.last_player = self.initial_game.last_player

    def run(self, engine: type, depth=1, play_args: dict = {}):
        engineA, engineB = engine(), engine()
        engineA.game, engineA.color, engineA.shallow = self.game, chess.WHITE, True
        engineB.game, engineB.color, engineB.shallow = self.game, chess.BLACK, True

        engineA.setup()
        engineB.setup()

        if depth == -1: # play until the end
            while not self.game.is_game_over():
                move = engineA.play(**play_args) if self.game.board.turn == chess.WHITE else engineB.play(**play_args)
                if not move:
                    return

                if isinstance(move, list) and move:
                    move = random.choice(move)

                self.game.move(move)
        else:
            for _ in range(depth):
                move = engineA.play(**play_args) if self.game.board.turn == chess.WHITE else engineB.play(**play_args)
                if not move:
                    return

                if isinstance(move, list) and move:
                    move = random.choice(move)

                self.game.move(move)
                if self.game.is_game_over():
                    return
