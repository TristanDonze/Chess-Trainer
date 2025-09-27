import requests
from typing import List, Dict

def get_chesscom_data(username: str) -> tuple[Dict[str, int], List[Dict[str, str]]]:
    """
    Fetches the latest Elo ratings and recent games of a Chess.com user.
    Args:
        username (str): The Chess.com username.
    Returns:
        tuple: A dictionary with Elo ratings and a list of recent games.
        Dictionary keys for recent games: 'url', 'white', 'black', 'pgn'.
    """
    user = username.lower()

    headers = {
        "User-Agent": "chess-trainer/0.1"
    }

    stats_url = f"https://api.chess.com/pub/player/{user}/stats"
    stats_resp = requests.get(stats_url, headers=headers)
    stats_resp.raise_for_status()
    if stats_resp.status_code != 200:
        raise ValueError(f"Unable to retrieve stats for {username}")
    stats = stats_resp.json()

    elo = {
        "bullet": stats.get("chess_bullet", {}).get("last", {}).get("rating"),
        "blitz": stats.get("chess_blitz", {}).get("last", {}).get("rating"),
        "rapid": stats.get("chess_rapid", {}).get("last", {}).get("rating"),
        "daily": stats.get("chess_daily", {}).get("last", {}).get("rating"),
    }

    archives_url = f"https://api.chess.com/pub/player/{user}/games/archives/"
    archives_resp = requests.get(archives_url, headers=headers)
    archives_resp.raise_for_status()
    if archives_resp.status_code != 200:
        raise ValueError(f"Unable to retrieve archives for {username}")
    archives = archives_resp.json().get("archives", [])

    if not archives:
        return elo, []
    
    last_archive_url = archives[-1] # only last month for demo
    games_resp = requests.get(last_archive_url, headers=headers)
    games_resp.raise_for_status()
    if games_resp.status_code != 200:
        raise ValueError(f"Unable to retrieve games for {username}")
    games = games_resp.json().get("games", [])

    games_list = []
    for g in games:
        games_list.append({
            "url": g.get("url"),
            "white": g.get("white", {}),
            "black": g.get("black", {}),
            "pgn": g.get("pgn")
        })

    return elo, games_list

if __name__ == "__main__":
    elo, games_list = get_chesscom_data("EnzoPinchon")

    print("Elo:", elo)
    print("Number of games:", len(games_list))

    if games_list:
        print("Moves of the first game:")
        print(games_list[0])
