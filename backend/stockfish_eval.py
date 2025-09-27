import chess
import chess.engine
import json
import tqdm
import asyncio
import torch
import os
import numpy as np
import platform

from src.chess.game import Game
from meta import AVAILABLE_MODELS

# Initialize the Stockfish engine with platform-specific path
def get_engine_path():
    if platform.system() == "Windows":
        return "stockfish/stockfish-windows-x86-64-avx2.exe"  # Adjust as needed
    elif platform.system() == "Darwin":  # macOS
        return "/opt/homebrew/bin/stockfish"
    else:  # Linux
        return "stockfish"  # Assumes it's in PATH

engine_path = get_engine_path()
engine = chess.engine.SimpleEngine.popen_uci(engine_path)

# Engine analysis parameters
ANALYSIS_DEPTH = 8  # Lower depth for quicker analysis
MOVE_LIMIT = 100   # Maximum number of moves per game
MOVE_QUALITY_THRESHOLDS = {
    'brilliant': 5,    # <= 5 cp loss
    'excellent': 15,   # <= 15 cp loss
    'good': 30,        # <= 30 cp loss
    'inaccuracy': 80,  # <= 80 cp loss
    'mistake': 150,    # <= 150 cp loss
    'blunder': float('inf')  # > 150 cp loss
}

# Define the path for Stockfish evaluation results
stockfish_eval_path = "data/results_stockfish.json"

# Ensure the Stockfish evaluation results file exists
if not os.path.exists(stockfish_eval_path):
    os.makedirs(os.path.dirname(stockfish_eval_path), exist_ok=True)
    with open(stockfish_eval_path, "w") as f:
        json.dump([], f)

# Function to save evaluation results to a JSON file
def save_evaluation_results(results):
    with open(stockfish_eval_path, "r") as f:
        existing_results = json.load(f)
    existing_results.append(results)
    with open(stockfish_eval_path, "w") as f:
        json.dump(existing_results, f, indent=4)

def get_game_phase(board):
    """
    Determine the phase of the game based on piece count and position
    Returns: 'opening', 'middlegame', or 'endgame'
    """
    # Count material
    total_pieces = len(board.piece_map())
    
    if total_pieces >= 28:  # Most pieces still on board
        return 'opening'
    elif total_pieces <= 12:  # Few pieces left
        return 'endgame'
    else:
        return 'middlegame'

def classify_move_quality(cp_loss):
    """Classify the quality of a move based on centipawn loss"""
    for quality, threshold in MOVE_QUALITY_THRESHOLDS.items():
        if cp_loss <= threshold:
            return quality
    return 'blunder'

def evaluate_game(ai_white_name, ai_black_name):
    print(f"Starting game: {ai_white_name} (white) vs {ai_black_name} (black)")
    
    ai_white = AVAILABLE_MODELS[ai_white_name]()
    ai_black = AVAILABLE_MODELS[ai_black_name]()

    # Setup the AI models
    ai_white.setup()
    ai_black.setup()

    # Initialize the game
    game = Game()
    ai_white.game = game
    ai_black.game = game
    game.board = chess.Board()

    # Metrics accumulators for each player
    metrics = {
        'white': {
            'name': ai_white_name,
            'moves_count': 0,
            'total_cp_loss': 0,
            'position_scores': [],
            'move_qualities': {quality: 0 for quality in MOVE_QUALITY_THRESHOLDS.keys()},
            'phase_performance': {'opening': [], 'middlegame': [], 'endgame': []},
            'mate_sequences_found': 0,
            'mate_sequences_missed': 0,
            'avg_position_complexity': 0,
            'decisive_moves': 0,
        },
        'black': {
            'name': ai_black_name,
            'moves_count': 0,
            'total_cp_loss': 0,
            'position_scores': [],
            'move_qualities': {quality: 0 for quality in MOVE_QUALITY_THRESHOLDS.keys()},
            'phase_performance': {'opening': [], 'middlegame': [], 'endgame': []},
            'mate_sequences_found': 0,
            'mate_sequences_missed': 0,
            'avg_position_complexity': 0,
            'decisive_moves': 0,
        },
        'winner': None,  # Will store 'white', 'black', or 'draw'
        'outcome_reason': None,  # Will store the reason for the game ending
    }

    total_moves = 0
    # Play until game over or move limit reached
    while not game.board.is_game_over() and total_moves < MOVE_LIMIT:
        total_moves += 1
        current_phase = get_game_phase(game.board)
        
        # Determine whose turn it is
        if game.board.turn == chess.WHITE:
            ai_player = ai_white
            player_metrics = metrics['white']
            perspective = chess.WHITE
        else:
            ai_player = ai_black
            player_metrics = metrics['black']
            perspective = chess.BLACK

        # Get Stockfish's evaluation before the move
        info_before = engine.analyse(game.board, limit=chess.engine.Limit(depth=ANALYSIS_DEPTH))
        score_before = info_before["score"].pov(perspective)
        
        # Convert score to centipawns
        if score_before.is_mate():
            best_score_cp = 10000 if score_before.mate() > 0 else -10000
        else:
            best_score_cp = score_before.score()

        # Store position score
        player_metrics['position_scores'].append(best_score_cp)

        # Play the move
        move = ai_player.play()
        if move is None:  # Handle case where AI can't make a move
            break
        game.board.push(move)

        # Get Stockfish's evaluation after the move
        info_after = engine.analyse(game.board, limit=chess.engine.Limit(depth=ANALYSIS_DEPTH))
        score_after = info_after["score"].pov(perspective)
        
        if score_after.is_mate():
            actual_score_cp = 10000 if score_after.mate() > 0 else -10000
        else:
            actual_score_cp = score_after.score()

        # Calculate centipawn loss
        cp_loss = max(0, best_score_cp - actual_score_cp)

        # Update metrics
        player_metrics['moves_count'] += 1
        player_metrics['total_cp_loss'] += cp_loss
        
        # Classify move quality
        move_quality = classify_move_quality(cp_loss)
        player_metrics['move_qualities'][move_quality] += 1
        
        # Track performance by game phase
        player_metrics['phase_performance'][current_phase].append(cp_loss)

        # Check for mate sequences
        if score_before.is_mate() and not score_after.is_mate():
            player_metrics['mate_sequences_missed'] += 1
        elif not score_before.is_mate() and score_after.is_mate() and score_after.mate() > 0:
            player_metrics['mate_sequences_found'] += 1

        # Track decisive moves (evaluation change > 200 cp)
        if abs(actual_score_cp - best_score_cp) > 200:
            player_metrics['decisive_moves'] += 1

    # Determine game outcome and winner
    if game.board.is_checkmate():
        metrics['outcome_reason'] = 'checkmate'
        metrics['winner'] = 'black' if game.board.turn == chess.WHITE else 'white'
    elif game.board.is_stalemate():
        metrics['outcome_reason'] = 'stalemate'
        metrics['winner'] = 'draw'
    elif game.board.is_insufficient_material():
        metrics['outcome_reason'] = 'insufficient_material'
        metrics['winner'] = 'draw'
    elif game.board.is_fifty_moves():
        metrics['outcome_reason'] = 'fifty_moves'
        metrics['winner'] = 'draw'
    elif game.board.is_repetition():
        metrics['outcome_reason'] = 'repetition'
        metrics['winner'] = 'draw'
    elif total_moves >= MOVE_LIMIT:
        metrics['outcome_reason'] = 'move_limit'
        # For move limit, determine winner based on final evaluation
        final_eval = engine.analyse(game.board, limit=chess.engine.Limit(depth=ANALYSIS_DEPTH))
        final_score = final_eval["score"].pov(chess.WHITE)
        if final_score.is_mate():
            if final_score.mate() > 0:
                metrics['winner'] = 'white'
            else:
                metrics['winner'] = 'black'
        elif abs(final_score.score()) < 50:  # Within 0.5 pawn, consider it a draw
            metrics['winner'] = 'draw'
        elif final_score.score() > 0:
            metrics['winner'] = 'white'
        else:
            metrics['winner'] = 'black'
    else:
        metrics['outcome_reason'] = 'other'
        metrics['winner'] = 'draw'  # Default to draw for other cases

    # Calculate final metrics
    for color in ['white', 'black']:
        m = metrics[color]
        moves = m['moves_count']
        if moves > 0:
            m['acpl'] = m['total_cp_loss'] / moves
            m['move_quality_percentages'] = {
                quality: (count / moves) * 100 
                for quality, count in m['move_qualities'].items()
            }
            
            for phase in ['opening', 'middlegame', 'endgame']:
                phase_moves = m['phase_performance'][phase]
                m['phase_performance'][phase] = np.mean(phase_moves) if phase_moves else 0
            
            if len(m['position_scores']) > 1:
                m['position_volatility'] = np.std(m['position_scores'])
            else:
                m['position_volatility'] = 0
            
            m['decisive_move_percentage'] = (m['decisive_moves'] / moves) * 100

    metrics['total_moves'] = total_moves
    print(f"Completed game: {ai_white_name} vs {ai_black_name}. Result: {metrics['winner']} ({metrics['outcome_reason']})")
    return metrics

# Example usage: simulate multiple games and aggregate performance
ais = ["Random AI", "Sunfish AI", "Greedy AI", "Transformer AI", "Tree Search Transformer", 
       "Score CNN", "GreedyExploration AI", "MCTS AI", "Q-Learning AI", "Stockfish AI"]

# Number of games each AI plays against each other
N = 1  # Reduced number of games for faster execution

# Before the tournament
for ai_name in ais:
    if ai_name not in AVAILABLE_MODELS:
        print(f"Warning: {ai_name} not found in AVAILABLE_MODELS")
    else:
        try:
            model = AVAILABLE_MODELS[ai_name]()
            model.setup()
            print(f"{ai_name} loaded successfully")
        except Exception as e:
            print(f"Error loading {ai_name}: {e}")

# Results dictionary to accumulate metrics
results = {ai: {
    'games_played': 0,
    'games_won': 0,
    'games_lost': 0,
    'games_drawn': 0,
    'total_moves': 0,
    'total_acpl': 0,
    'move_qualities': {quality: 0 for quality in MOVE_QUALITY_THRESHOLDS.keys()},
    'phase_performance': {'opening': 0, 'middlegame': 0, 'endgame': 0},
    'phase_moves': {'opening': 0, 'middlegame': 0, 'endgame': 0},
    'mate_sequences': {'found': 0, 'missed': 0},
    'position_volatility': [],
    'decisive_moves': 0
} for ai in ais}

# Play games between each pair of AIs
for ai_white in ais:
    for ai_black in ais:
        if ai_white == ai_black:
            continue
        
        for _ in range(N):
            try:
                metrics = evaluate_game(ai_white, ai_black)
                
                # Record game result
                game_result = {
                    "white": ai_white,
                    "black": ai_black,
                    "winner": metrics['winner'],
                    "outcome_reason": metrics['outcome_reason'],
                    "metrics": metrics
                }
                
                save_evaluation_results(game_result)
                
                # Update AI stats with win/loss/draw
                if metrics['winner'] == 'white':
                    results[ai_white]['games_won'] += 1
                    results[ai_black]['games_lost'] += 1
                elif metrics['winner'] == 'black':
                    results[ai_white]['games_lost'] += 1
                    results[ai_black]['games_won'] += 1
                else:  # draw
                    results[ai_white]['games_drawn'] += 1
                    results[ai_black]['games_drawn'] += 1
                
                # Update white's metrics
                results[ai_white]['games_played'] += 1
                results[ai_white]['total_moves'] += metrics['white']['moves_count']
                results[ai_white]['total_acpl'] += metrics['white']['acpl'] * metrics['white']['moves_count'] if metrics['white']['moves_count'] > 0 else 0
                
                for quality in MOVE_QUALITY_THRESHOLDS.keys():
                    results[ai_white]['move_qualities'][quality] += metrics['white']['move_qualities'][quality]
                
                results[ai_white]['mate_sequences']['found'] += metrics['white']['mate_sequences_found']
                results[ai_white]['mate_sequences']['missed'] += metrics['white']['mate_sequences_missed']
                
                if 'position_volatility' in metrics['white']:
                    results[ai_white]['position_volatility'].append(metrics['white']['position_volatility'])
                
                results[ai_white]['decisive_moves'] += metrics['white']['decisive_moves']
                
                # Update phase performance for white
                for phase in ['opening', 'middlegame', 'endgame']:
                    if isinstance(metrics['white']['phase_performance'][phase], list):
                        phase_moves = len(metrics['white']['phase_performance'][phase])
                        if phase_moves > 0:
                            avg_phase_loss = sum(metrics['white']['phase_performance'][phase]) / phase_moves
                            results[ai_white]['phase_performance'][phase] += avg_phase_loss * phase_moves
                            results[ai_white]['phase_moves'][phase] += phase_moves
                    else:
                        # If already averaged in evaluate_game
                        if isinstance(metrics['white']['phase_performance'][phase], (int, float, np.number)) and metrics['white']['phase_performance'][phase] > 0:
                            # We already have the average, but need to know how many moves
                            # Estimate the number of moves based on the total moves in this phase
                            estimated_phase_moves = metrics['white']['moves_count'] // 3  # Rough estimate
                            results[ai_white]['phase_performance'][phase] += metrics['white']['phase_performance'][phase] * estimated_phase_moves
                            results[ai_white]['phase_moves'][phase] += estimated_phase_moves
                
                # Update black's metrics similarly
                results[ai_black]['games_played'] += 1
                results[ai_black]['total_moves'] += metrics['black']['moves_count']
                results[ai_black]['total_acpl'] += metrics['black']['acpl'] * metrics['black']['moves_count'] if metrics['black']['moves_count'] > 0 else 0
                
                for quality in MOVE_QUALITY_THRESHOLDS.keys():
                    results[ai_black]['move_qualities'][quality] += metrics['black']['move_qualities'][quality]
                
                results[ai_black]['mate_sequences']['found'] += metrics['black']['mate_sequences_found']
                results[ai_black]['mate_sequences']['missed'] += metrics['black']['mate_sequences_missed']
                
                if 'position_volatility' in metrics['black']:
                    results[ai_black]['position_volatility'].append(metrics['black']['position_volatility'])
                
                results[ai_black]['decisive_moves'] += metrics['black']['decisive_moves']
                
                # Update phase performance for black
                for phase in ['opening', 'middlegame', 'endgame']:
                    if isinstance(metrics['black']['phase_performance'][phase], list):
                        phase_moves = len(metrics['black']['phase_performance'][phase])
                        if phase_moves > 0:
                            avg_phase_loss = sum(metrics['black']['phase_performance'][phase]) / phase_moves
                            results[ai_black]['phase_performance'][phase] += avg_phase_loss * phase_moves
                            results[ai_black]['phase_moves'][phase] += phase_moves
                    else:
                        # If already averaged in evaluate_game
                        if isinstance(metrics['black']['phase_performance'][phase], (int, float, np.number)) and metrics['black']['phase_performance'][phase] > 0:
                            # We already have the average, but need to know how many moves
                            # Estimate the number of moves based on the total moves in this phase
                            estimated_phase_moves = metrics['black']['moves_count'] // 3  # Rough estimate
                            results[ai_black]['phase_performance'][phase] += metrics['black']['phase_performance'][phase] * estimated_phase_moves
                            results[ai_black]['phase_moves'][phase] += estimated_phase_moves
            except Exception as e:
                print(f"Error in game between {ai_white} and {ai_black}: {e}")
                continue

# Calculate final averages for phase performance
for ai in ais:
    for phase in ['opening', 'middlegame', 'endgame']:
        if results[ai]['phase_moves'][phase] > 0:
            results[ai]['phase_performance'][phase] /= results[ai]['phase_moves'][phase]

# Print comprehensive performance analysis for each AI
print("\nComprehensive AI Performance Analysis")
print("=" * 50)

for ai in ais:
    if results[ai]['games_played'] > 0:
        r = results[ai]
        moves = r['total_moves']
        print(f"\n{ai}:")
        print(f"Games played: {r['games_played']}")
        print(f"Win/Loss/Draw: {r['games_won']}/{r['games_lost']}/{r['games_drawn']}")
        print(f"Win rate: {(r['games_won'] / r['games_played']) * 100:.1f}%")
        print(f"Average moves per game: {moves / r['games_played']:.2f}")
        print(f"Average centipawn loss: {r['total_acpl'] / moves:.2f}") if moves > 0 else print("Average centipawn loss: N/A")
        
        print("\nMove Quality Distribution:")
        for quality in MOVE_QUALITY_THRESHOLDS.keys():
            percentage = (r['move_qualities'][quality] / moves) * 100 if moves > 0 else 0
            print(f"  {quality}: {percentage:.1f}%")
        
        print("\nPhase Performance (Average CP Loss):")
        for phase in ['opening', 'middlegame', 'endgame']:
            print(f"  {phase}: {r['phase_performance'][phase]:.2f}")
        
        print("\nMate Sequences:")
        print(f"  Found: {r['mate_sequences']['found']}")
        print(f"  Missed: {r['mate_sequences']['missed']}")
        
        print(f"\nPosition Volatility: {np.mean(r['position_volatility']):.2f}") if r['position_volatility'] else print(f"\nPosition Volatility: N/A")
        print(f"Decisive Moves per Game: {r['decisive_moves'] / r['games_played']:.2f}")
    else:
        print(f"\n{ai}: No games played.")

# After the tournament
print("\nGames played by each AI pair:")
game_pairs = {}
for ai_white in ais:
    for ai_black in ais:
        if ai_white != ai_black:
            key = f"{ai_white} vs {ai_black}"
            game_pairs[key] = 0

# Count games from results file
with open(stockfish_eval_path, "r") as f:
    all_games = json.load(f)
    for game in all_games:
        key = f"{game['white']} vs {game['black']}"
        if key in game_pairs:
            game_pairs[key] += 1

# Print the counts
for pair, count in game_pairs.items():
    print(f"{pair}: {count} games")

# Close the engine after analysis is done
engine.close()
