from models.greedy.random_ai import RandomAI
from models.greedy.greedy_ai import GreedyAI
from models.greedy.greedy_exploration import GreedyExplorationAI
from models.downloaded.stockfish import StockfishAI

AVAILABLE_MODELS = {
    "Random AI": RandomAI,
    "Greedy AI": GreedyAI,
    "GreedyExploration AI": GreedyExplorationAI,
    "Stockfish AI": StockfishAI,
}
"""
This dictionary exposes all the models that are available for testing or using in the interface.
The key is the model name and the value is the model class.

"""
