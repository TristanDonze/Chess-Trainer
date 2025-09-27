import chess
import json
import tqdm

from src.chess.game import Game
from meta import AVAILABLE_MODELS

def play_game(ai1, ai2) -> int:
    """
    Play a game between two AIs.

    Return:
    - 1 if AI1 wins
    - 2 if AI2 wins
    - 0 if it's a draw
    """

    game = Game()
    game.play(white=ai1, black=ai2)

    while not game.is_game_over():
        game.play_engine_move()

    if game.checkmate:
        return 1 if game.winner == chess.WHITE else 2
    return 0

def calculate_elo_update(elo1, elo2) -> dict:
    """
    Calculate the elo update between two players if they play a game.

    Return:
    - Dictionary containing the elo update for player1 (player2 gets the opposite update)
      {"win": int, "draw": int, "loss": int}
    """
    
    # Set the K-factor and compute player1's expected score
    K = 32
    expected = 1 / (1 + 10 ** ((elo2 - elo1) / 400))
    
    # Determine rating changes for win, draw, and loss outcomes
    win_update = round(K * (1 - expected))
    draw_update = round(K * (0.5 - expected))
    loss_update = round(K * (0 - expected))
    
    return {"win": win_update, "draw": draw_update, "loss": loss_update}


import math
import random

def choose_match(ai_dict) -> tuple:
    """
    Choose a match between two AIs.

    Parameters:
    - ai_dict: dictionary containing the AIs and their respective information
      {ai1: {"name": str, "elo": int, "nb_games": int}, ai2: {...}, ...}

    Returns:
    - Tuple containing the keys of the two selected AIs.
    """
    # Parameter controlling the sensitivity to ELO differences
    sigma = 100.0

    pairs = []
    weights = []
    keys = list(ai_dict.keys())
    n = len(keys)
    
    for i in range(n):
        for j in range(i + 1, n):
            ai_i = ai_dict[keys[i]]
            ai_j = ai_dict[keys[j]]
            
            # Lower ELO difference gives a higher weight.
            elo_diff = abs(ai_i["elo"] - ai_j["elo"])
            closeness_factor = math.exp(-elo_diff / sigma)
            
            # Newer AIs (with lower nb_games) get a higher chance.
            newness_factor = (1 / (1 + ai_i["nb_games"])) + (1 / (1 + ai_j["nb_games"]))
            
            weight = closeness_factor * newness_factor
            
            pairs.append((keys[i], keys[j]))
            weights.append(weight)
    
    # Randomly choose one pair weighted by the computed scores
    chosen_pair = random.choices(pairs, weights=weights, k=1)[0]
    random.shuffle(list(chosen_pair)) # Shuffle the pair to randomize the order
    return chosen_pair

if __name__ == "__main__":
    ranking_path = "data/ranking.json"
    with open(ranking_path, "r") as f:
        ranking: list = json.load(f)

    

    nb_games = 20
    ranking_dict = {}
    for ai in ranking:
        if ai.get("model") in AVAILABLE_MODELS:
            ranking_dict[ai["model"]] = ai

    for _ in tqdm.tqdm(range(nb_games)):
        ai1, ai2 = choose_match(ranking_dict)
        ai1_model = AVAILABLE_MODELS[ai1]()
        ai2_model = AVAILABLE_MODELS[ai2]()
        ai1_model.setup()
        ai2_model.setup()

        result = play_game(ai1_model, ai2_model)
        print(ai1, "vs", ai2, "-->", result)
        elo_update = calculate_elo_update(ranking_dict[ai1]["elo"], ranking_dict[ai2]["elo"])

        if result == 1:
            ranking_dict[ai1]["elo"] += elo_update["win"]
            ranking_dict[ai2]["elo"] -= elo_update["win"]
        elif result == 2:
            ranking_dict[ai1]["elo"] += elo_update["loss"]
            ranking_dict[ai2]["elo"] -= elo_update["loss"]
        else:
            ranking_dict[ai1]["elo"] += elo_update["draw"]
            ranking_dict[ai2]["elo"] -= elo_update["draw"]

        ranking_dict[ai1]["nb_games"] += 1
        ranking_dict[ai2]["nb_games"] += 1

    updated_ranking = list(ranking_dict.values())
    # merge the updated ranking with the original ranking

    for player in ranking:
        if player.get("model") in ranking_dict: continue
        updated_ranking.append(player)

    with open(ranking_path, "w") as f:
        json.dump(updated_ranking, f, indent=4)
    
