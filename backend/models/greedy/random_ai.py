from models.engine import Engine

import random

class RandomAI(Engine):
    """
    Random AI that plays a random move.
    """

    __author__ = "Enzo Pinchon"
    __description__ = "Random AI that plays a random move."

    def play(self) -> dict:
        """
        Return the move played by the AI.
        
        :param pieces: list of pieces of the AI
        :type pieces: list[Piece]
        :return: {"from": (int, int), "to": (int, int), ["promotion": str]}
        :rtype: dict
        """

        actions = list(self.game.board.legal_moves)
        if len(actions) == 0: return None
        return random.choice(actions)
        