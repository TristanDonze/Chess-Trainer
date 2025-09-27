import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Load the evaluation results
with open('data/results_stockfish.json', 'r') as f:
    results = json.load(f)

# Initialize dictionaries to store aggregated metrics
metrics = defaultdict(lambda: {
    'games': 0,
    'total_acpl': 0,
    'total_moves': 0,
    'total_blunders': 0,
    'total_excellent_moves': 0,
    'total_decisive_moves': 0,
})

# Aggregate metrics from all games
for game in results:
    white_ai = game['white']
    black_ai = game['black']
    game_metrics = game['metrics']  # Access the metrics dictionary

    # Update white's metrics
    metrics[white_ai]['games'] += 1
    metrics[white_ai]['total_acpl'] += game_metrics['white']['total_cp_loss']
    metrics[white_ai]['total_moves'] += game_metrics['white']['moves_count']
    metrics[white_ai]['total_blunders'] += game_metrics['white']['move_qualities']['blunder']
    metrics[white_ai]['total_excellent_moves'] += (game_metrics['white']['move_qualities']['brilliant'] +
                                                    game_metrics['white']['move_qualities']['excellent'])

    # Update black's metrics
    metrics[black_ai]['games'] += 1
    metrics[black_ai]['total_acpl'] += game_metrics['black']['total_cp_loss']
    metrics[black_ai]['total_moves'] += game_metrics['black']['moves_count']
    metrics[black_ai]['total_blunders'] += game_metrics['black']['move_qualities']['blunder']
    metrics[black_ai]['total_excellent_moves'] += (game_metrics['black']['move_qualities']['brilliant'] +
                                                    game_metrics['black']['move_qualities']['excellent'])

# Prepare data for plotting
ai_names = list(metrics.keys())
avg_acpl = []
blunders_per_game = []
excellent_moves_percentage = []
moves_per_game = []

for ai in ai_names:
    games = metrics[ai]['games']
    total_moves = metrics[ai]['total_moves']
    
    if games > 0:
        avg_acpl.append(metrics[ai]['total_acpl'] / total_moves)
        blunders_per_game.append(metrics[ai]['total_blunders'] / games)
        moves_per_game.append(total_moves / games)
        excellent_moves_percentage.append((metrics[ai]['total_excellent_moves'] / total_moves) * 100)
    else:
        avg_acpl.append(0)
        blunders_per_game.append(0)
        moves_per_game.append(0)
        excellent_moves_percentage.append(0)

# Create a figure with multiple subplots
plt.figure(figsize=(20, 15))

# 1. Average Centipawn Loss
plt.subplot(2, 2, 1)
bars = plt.bar(ai_names, avg_acpl, color='skyblue')
plt.title('Average Centipawn Loss by AI')
plt.xticks(rotation=45, ha='right')
plt.ylabel('Average Centipawn Loss')
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}', ha='center', va='bottom')

# 2. Blunders per Game
plt.subplot(2, 2, 2)
bars = plt.bar(ai_names, blunders_per_game, color='salmon')
plt.title('Average Blunders per Game by AI')
plt.xticks(rotation=45, ha='right')
plt.ylabel('Average Blunders per Game')
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}', ha='center', va='bottom')

# 3. Excellent Moves Percentage
plt.subplot(2, 2, 3)
bars = plt.bar(ai_names, excellent_moves_percentage, color='lightgreen')
plt.title('Excellent Moves Percentage by AI')
plt.xticks(rotation=45, ha='right')
plt.ylabel('Excellent Moves (%)')
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}%', ha='center', va='bottom')

# 4. Average Moves per Game
plt.subplot(2, 2, 4)
bars = plt.bar(ai_names, moves_per_game, color='lightcoral')
plt.title('Average Moves per Game by AI')
plt.xticks(rotation=45, ha='right')
plt.ylabel('Average Moves per Game')
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}', ha='center', va='bottom')

plt.tight_layout()
plt.savefig('stockfish_analysis.png')
plt.close()

# Print summary statistics
print("\nDetailed AI Performance Analysis")
print("=" * 50)

for ai in ai_names:
    games = metrics[ai]['games']
    total_moves = metrics[ai]['total_moves']
    
    if games > 0:
        print(f"\n{ai}:")
        print(f"Games played: {games}")
        print(f"Average moves per game: {total_moves / games:.2f}")
        print(f"Average centipawn loss: {metrics[ai]['total_acpl'] / total_moves:.2f}")
        print(f"Blunders per game: {metrics[ai]['total_blunders'] / games:.2f}")
        print(f"Excellent moves rate: {(metrics[ai]['total_excellent_moves'] / total_moves) * 100:.1f}%")
    else:
        print(f"\n{ai}: No games played.") 