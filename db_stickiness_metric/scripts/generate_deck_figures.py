"""
Generate Deck Figures - Script 4
=================================

Generate all visualizations for the 10-slide deck.

Input:  outputs/db_player_leaderboard.csv
        outputs/db_rep_scores.parquet
        outputs/validation_split_half.csv
        outputs/validation_metrics.json
Output: figures/*.png (10-15 figures @ 300 DPI)

Runtime: ~1-2 minutes
Memory:  ~500MB
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from scipy.stats import pearsonr
import json
import os
import sys

# Set style
sns.set_style('whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11

print('=' * 80)
print('GENERATE DECK FIGURES - SCRIPT 4')
print('=' * 80)

# ============================================================================
# CONFIGURATION
# ============================================================================

LEADERBOARD_PATH = '../outputs/db_player_leaderboard.csv'
REP_SCORES_PATH = '../outputs/db_rep_scores.parquet'
SPLIT_HALF_PATH = '../outputs/validation_split_half.csv'
VALIDATION_PATH = '../outputs/validation_metrics.json'
FIGURES_DIR = '../figures'

# Create figures directory
os.makedirs(FIGURES_DIR, exist_ok=True)

# ============================================================================
# LOAD DATA
# ============================================================================

print('\n' + '-' * 80)
print('Loading data')
print('-' * 80)

if not os.path.exists(LEADERBOARD_PATH):
    print(f'ERROR: Leaderboard not found at {LEADERBOARD_PATH}')
    print('Please run compute_db_stickiness.py first.')
    sys.exit(1)

leaderboard = pd.read_csv(LEADERBOARD_PATH)
rep_scores = pd.read_parquet(REP_SCORES_PATH)

print(f'Loaded {len(leaderboard)} DBs')
print(f'Loaded {len(rep_scores)} reps')

# Load gsis_id to player name mapping
print('Loading player name mapping...')
import pyarrow.parquet as pq

PARQUET_PATH = '../../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'
COLLEGE_STATS_PATH = '../../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'
SESSION_ID = 4

# Get zebra_id to gsis_id mapping
table = pq.read_table(
    PARQUET_PATH,
    columns=['zebra_id', 'gsis_id'],
    filters=[('session_id', '=', SESSION_ID)]
)
gsis_mapping = table.to_pandas()
gsis_mapping['zebra_id'] = gsis_mapping['zebra_id'].astype(str)
gsis_mapping['gsis_id'] = gsis_mapping['gsis_id'].astype(str)
gsis_mapping = gsis_mapping.drop_duplicates(subset=['zebra_id']).dropna(subset=['gsis_id'])

# Get gsis_id to player name mapping from college stats
college_stats = pd.read_csv(COLLEGE_STATS_PATH)
college_stats['college_gsis_id'] = college_stats['college_gsis_id'].astype(str)
name_mapping = college_stats[['college_gsis_id', 'player_name']].drop_duplicates(subset=['college_gsis_id'])

# Merge to create zebra_id to player_name mapping
zebra_to_name = gsis_mapping.merge(
    name_mapping,
    left_on='gsis_id',
    right_on='college_gsis_id',
    how='left'
)

# Add player names to leaderboard
leaderboard['db_name'] = leaderboard['db_name'].astype(str)
leaderboard = leaderboard.merge(
    zebra_to_name[['zebra_id', 'player_name']],
    left_on='db_name',
    right_on='zebra_id',
    how='left'
)

# Use player_name where available, otherwise format as "Unknown DB #XXXX"
def create_display_name(row):
    if pd.notna(row['player_name']):
        return row['player_name']
    else:
        # Use last 4 digits of zebra_id for unmapped players
        zebra_str = str(row['db_name'])
        return f"Unknown DB #{zebra_str[-4:]}"

leaderboard['display_name'] = leaderboard.apply(create_display_name, axis=1)

print(f'Mapped {leaderboard["player_name"].notna().sum()}/{len(leaderboard)} DBs to player names')

# Filter to minimum 5 reps for quality leaderboard
MIN_REPS = 5
leaderboard_filtered = leaderboard[leaderboard['n_reps'] >= MIN_REPS].copy()
print(f'After min {MIN_REPS} reps filter: {len(leaderboard_filtered)} DBs remain')

# ONLY show players with matched names (exclude "Unknown DB" entirely)
leaderboard_with_names = leaderboard_filtered[leaderboard_filtered['player_name'].notna()].copy()
leaderboard_unknown = leaderboard_filtered[leaderboard_filtered['player_name'].isna()].copy()

print(f'  With matched names: {len(leaderboard_with_names)}')
print(f'  Excluded unknown players: {len(leaderboard_unknown)}')

# Use ONLY players with matched names for all figures
leaderboard = leaderboard_with_names
print(f'\nFinal leaderboard: {len(leaderboard)} DBs (5+ reps, matched names only)')

if os.path.exists(SPLIT_HALF_PATH):
    split_half = pd.read_csv(SPLIT_HALF_PATH)
    print(f'Loaded {len(split_half)} split-half entries')
else:
    split_half = None
    print('WARNING: Split-half data not found')

if os.path.exists(VALIDATION_PATH):
    with open(VALIDATION_PATH, 'r') as f:
        validation = json.load(f)
    print('Loaded validation metrics')
else:
    validation = None
    print('WARNING: Validation metrics not found')

# ============================================================================
# FIGURE 1: METHODOLOGY FRAMEWORK
# ============================================================================

print('\n' + '-' * 80)
print('Generating Figure 1: Stickiness Framework')
print('-' * 80)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Phase Score
ax = axes[0]
ax.text(0.5, 0.85, 'PHASE SCORE', ha='center', fontsize=14, fontweight='bold')
ax.text(0.5, 0.7, '45% Weight', ha='center', fontsize=12, color='steelblue', fontweight='bold')
ax.text(0.5, 0.55, 'Proximity Maintenance', ha='center', fontsize=11)
ax.text(0.1, 0.4, '• Tight coverage (≤2y):', fontsize=9)
ax.text(0.3, 0.35, '100% credit', fontsize=9, color='green', fontweight='bold')
ax.text(0.1, 0.25, '• Acceptable (≤3.5y):', fontsize=9)
ax.text(0.3, 0.2, '50% credit', fontsize=9, color='orange', fontweight='bold')
ax.text(0.1, 0.1, '• Leverage consistency:', fontsize=9)
ax.text(0.3, 0.05, 'Bonus +10%', fontsize=9, color='blue', fontweight='bold')
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

# Reaction Score
ax = axes[1]
ax.text(0.5, 0.85, 'REACTION SCORE', ha='center', fontsize=14, fontweight='bold')
ax.text(0.5, 0.7, '30% Weight', ha='center', fontsize=12, color='darkorange', fontweight='bold')
ax.text(0.5, 0.55, 'Break Response', ha='center', fontsize=11)
ax.text(0.1, 0.4, '• Response latency:', fontsize=9)
ax.text(0.3, 0.35, '<0.5s = best', fontsize=9, color='green', fontweight='bold')
ax.text(0.1, 0.25, '• Direction change:', fontsize=9)
ax.text(0.3, 0.2, '<120° = smooth', fontsize=9, color='green', fontweight='bold')
ax.text(0.1, 0.1, '• Formula:', fontsize=9)
ax.text(0.25, 0.05, '60% latency + 40% flip', fontsize=8, color='gray')
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

# Recovery Score
ax = axes[2]
ax.text(0.5, 0.85, 'RECOVERY SCORE', ha='center', fontsize=14, fontweight='bold')
ax.text(0.5, 0.7, '25% Weight', ha='center', fontsize=12, color='darkgreen', fontweight='bold')
ax.text(0.5, 0.55, 'Closing Speed', ha='center', fontsize=11)
ax.text(0.1, 0.4, '• Gap closed:', fontsize=9)
ax.text(0.3, 0.35, '% of separation', fontsize=9, color='green', fontweight='bold')
ax.text(0.1, 0.25, '• Closing speed:', fontsize=9)
ax.text(0.3, 0.2, '≥4 yds/s = elite', fontsize=9, color='green', fontweight='bold')
ax.text(0.1, 0.1, '• Formula:', fontsize=9)
ax.text(0.25, 0.05, '70% recovery + 30% speed', fontsize=8, color='gray')
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/methodology_stickiness_framework.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved methodology_stickiness_framework.png')

# ============================================================================
# FIGURE 2: REP EXTRACTION FLOWCHART
# ============================================================================

print('Generating Figure 2: Rep Extraction Flow')

fig, ax = plt.subplots(figsize=(12, 8))

# Define boxes
boxes = [
    {'text': 'Session 4 Data\n(37.5M frames)', 'pos': (0.5, 0.9), 'color': 'lightblue'},
    {'text': 'Activity Detection\nSpeed > 1.5 yds/s', 'pos': (0.5, 0.75), 'color': 'lightgreen'},
    {'text': f'WR Bursts\n({len(rep_scores)} reps)', 'pos': (0.5, 0.6), 'color': 'lightgreen'},
    {'text': 'Station Clustering\nDBSCAN (eps=12y)', 'pos': (0.5, 0.45), 'color': 'lightyellow'},
    {'text': 'Hungarian Assignment\nWR-DB Pairing', 'pos': (0.5, 0.3), 'color': 'lightcoral'},
    {'text': f'Matched Reps\n({len(rep_scores)} pairs)', 'pos': (0.5, 0.15), 'color': 'lightcoral'},
]

for box in boxes:
    rect = patches.FancyBboxPatch(
        (box['pos'][0] - 0.15, box['pos'][1] - 0.04),
        0.3, 0.08,
        boxstyle="round,pad=0.01",
        facecolor=box['color'],
        edgecolor='black',
        linewidth=2
    )
    ax.add_patch(rect)
    ax.text(box['pos'][0], box['pos'][1], box['text'],
            ha='center', va='center', fontsize=11, fontweight='bold')

# Arrows
arrow_props = dict(arrowstyle='->', lw=2, color='black')
for i in range(len(boxes) - 1):
    ax.annotate('', xy=(boxes[i+1]['pos'][0], boxes[i+1]['pos'][1] + 0.04),
                xytext=(boxes[i]['pos'][0], boxes[i]['pos'][1] - 0.04),
                arrowprops=arrow_props)

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')
ax.set_title('Data Pipeline: From Tracking to Matched Reps', fontsize=16, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/methodology_rep_extraction_flow.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved methodology_rep_extraction_flow.png')

# ============================================================================
# FIGURE 3: OVERALL LEADERBOARD
# ============================================================================

print('Generating Figure 3: Overall Leaderboard')

fig, ax = plt.subplots(figsize=(10, 8))

top_10 = leaderboard.head(10).copy()
y_pos = np.arange(len(top_10))

# Horizontal bars
bars = ax.barh(y_pos, top_10['stickiness_bayesian'], color='steelblue', alpha=0.8, edgecolor='black')

# Color code by rank
colors = ['gold', 'silver', '#CD7F32']  # Gold, Silver, Bronze
for i in range(min(3, len(bars))):
    bars[i].set_color(colors[i])
    bars[i].set_alpha(1.0)

# Add confidence intervals (±1 SE)
se = top_10['stickiness_std'] / np.sqrt(top_10['n_reps'])
se = se.fillna(0)
ax.errorbar(
    top_10['stickiness_bayesian'], y_pos,
    xerr=se,
    fmt='none',
    ecolor='black',
    capsize=3,
    alpha=0.6,
    linewidth=1.5
)

# Labels
ax.set_yticks(y_pos)
ax.set_yticklabels(top_10['display_name'], fontsize=11)
ax.invert_yaxis()
ax.set_xlabel('Stickiness Score (Bayesian Adjusted)', fontsize=13, fontweight='bold')
ax.set_title('Top 10 DBs by Man Coverage Stickiness', fontsize=15, fontweight='bold')
ax.set_xlim(0, max(top_10['stickiness_bayesian']) * 1.15)

# Add rep counts
for i, (idx, row) in enumerate(top_10.iterrows()):
    ax.text(row['stickiness_bayesian'] + 0.01, i,
           f"n={int(row['n_reps'])}",
           va='center', fontsize=9, color='gray')

# Add grid
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/leaderboard_overall_stickiness.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved leaderboard_overall_stickiness.png')

# ============================================================================
# FIGURE 4: SUB-SCORE LEADERBOARDS
# ============================================================================

print('Generating Figure 4: Sub-Score Leaderboards')

fig, axes = plt.subplots(1, 3, figsize=(15, 6))

subscores = [
    ('avg_phase', 'Phase Score', 'steelblue'),
    ('avg_reaction', 'Reaction Score', 'darkorange'),
    ('avg_recovery', 'Recovery Score', 'darkgreen')
]

for idx, (score_col, title, color) in enumerate(subscores):
    ax = axes[idx]

    top_5 = leaderboard.nlargest(5, score_col)
    y_pos = np.arange(len(top_5))

    ax.barh(y_pos, top_5[score_col], color=color, alpha=0.8, edgecolor='black')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_5['display_name'], fontsize=10)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlim(0, 1.0)
    ax.grid(axis='x', alpha=0.3)

    # Add values
    for i, (_, row) in enumerate(top_5.iterrows()):
        ax.text(row[score_col] + 0.02, i,
               f"{row[score_col]:.3f}",
               va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/leaderboard_subscores_comparison.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved leaderboard_subscores_comparison.png')

# ============================================================================
# FIGURE 5: SPLIT-HALF RELIABILITY
# ============================================================================

if split_half is not None and len(split_half) > 2:
    print('Generating Figure 5: Split-Half Reliability')

    fig, ax = plt.subplots(figsize=(24, 8))

    # Scatter plot
    ax.scatter(
        split_half['half1_stickiness'],
        split_half['half2_stickiness'],
        s=120,
        alpha=0.7,
        c='steelblue',
        edgecolors='black',
        linewidths=1.5
    )

    # Trendline
    z = np.polyfit(split_half['half1_stickiness'], split_half['half2_stickiness'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(
        split_half['half1_stickiness'].min(),
        split_half['half1_stickiness'].max(),
        100
    )
    r, pval = pearsonr(split_half['half1_stickiness'], split_half['half2_stickiness'])
    ax.plot(x_line, p(x_line), 'r--', linewidth=2.5, label=f'r = {r:.3f}, p = {pval:.4f}')

    # Diagonal reference (perfect reliability)
    lims = [
        np.min([ax.get_xlim(), ax.get_ylim()]),
        np.max([ax.get_xlim(), ax.get_ylim()])
    ]
    ax.plot(lims, lims, 'k:', linewidth=1.5, alpha=0.5, label='Perfect reliability')

    ax.set_xlabel('First Half Stickiness', fontsize=13, fontweight='bold')
    ax.set_ylabel('Second Half Stickiness', fontsize=13, fontweight='bold')
    ax.set_title(f'Split-Half Reliability (n={len(split_half)} DBs with 6+ reps)',
                 fontsize=15, fontweight='bold')
    ax.legend(fontsize=12, loc='lower right')
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/validation_split_half_reliability.png', dpi=300, bbox_inches='tight')
    plt.close()
    print('  ✓ Saved validation_split_half_reliability.png')
else:
    print('  ⊘ Skipping split-half figure (insufficient data)')

# ============================================================================
# FIGURE 6: SCORE DISTRIBUTIONS
# ============================================================================

print('Generating Figure 6: Score Distributions')

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Overall stickiness
ax = axes[0, 0]
ax.hist(rep_scores['stickiness'], bins=30, color='steelblue', alpha=0.7, edgecolor='black')
ax.axvline(rep_scores['stickiness'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean = {rep_scores["stickiness"].mean():.3f}')
ax.axvline(rep_scores['stickiness'].median(), color='green', linestyle='--', linewidth=2, label=f'Median = {rep_scores["stickiness"].median():.3f}')
ax.set_xlabel('Stickiness Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
ax.set_title('Overall Stickiness Distribution', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(alpha=0.3)

# Phase
ax = axes[0, 1]
ax.hist(rep_scores['phase_score'], bins=30, color='steelblue', alpha=0.7, edgecolor='black')
ax.axvline(rep_scores['phase_score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean = {rep_scores["phase_score"].mean():.3f}')
ax.set_xlabel('Phase Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
ax.set_title('Phase Score Distribution', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(alpha=0.3)

# Reaction
ax = axes[1, 0]
ax.hist(rep_scores['reaction_score'], bins=30, color='darkorange', alpha=0.7, edgecolor='black')
ax.axvline(rep_scores['reaction_score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean = {rep_scores["reaction_score"].mean():.3f}')
ax.set_xlabel('Reaction Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
ax.set_title('Reaction Score Distribution', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(alpha=0.3)

# Recovery
ax = axes[1, 1]
ax.hist(rep_scores['recovery_score'], bins=30, color='darkgreen', alpha=0.7, edgecolor='black')
ax.axvline(rep_scores['recovery_score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean = {rep_scores["recovery_score"].mean():.3f}')
ax.set_xlabel('Recovery Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
ax.set_title('Recovery Score Distribution', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/analysis_score_distributions.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved analysis_score_distributions.png')

# ============================================================================
# FIGURE 7: SUBSCORE SCATTER MATRIX
# ============================================================================

print('Generating Figure 7: Sub-Score Correlations')

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Phase vs Reaction
ax = axes[0]
ax.scatter(leaderboard['avg_phase'], leaderboard['avg_reaction'], s=80, alpha=0.6, edgecolors='black')
r, _ = pearsonr(leaderboard['avg_phase'], leaderboard['avg_reaction'])
ax.set_xlabel('Phase Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Reaction Score', fontsize=11, fontweight='bold')
ax.set_title(f'Phase vs Reaction (r={r:.3f})', fontsize=13, fontweight='bold')
ax.grid(alpha=0.3)

# Phase vs Recovery
ax = axes[1]
ax.scatter(leaderboard['avg_phase'], leaderboard['avg_recovery'], s=80, alpha=0.6, edgecolors='black', color='green')
r, _ = pearsonr(leaderboard['avg_phase'], leaderboard['avg_recovery'])
ax.set_xlabel('Phase Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Recovery Score', fontsize=11, fontweight='bold')
ax.set_title(f'Phase vs Recovery (r={r:.3f})', fontsize=13, fontweight='bold')
ax.grid(alpha=0.3)

# Reaction vs Recovery
ax = axes[2]
ax.scatter(leaderboard['avg_reaction'], leaderboard['avg_recovery'], s=80, alpha=0.6, edgecolors='black', color='orange')
r, _ = pearsonr(leaderboard['avg_reaction'], leaderboard['avg_recovery'])
ax.set_xlabel('Reaction Score', fontsize=11, fontweight='bold')
ax.set_ylabel('Recovery Score', fontsize=11, fontweight='bold')
ax.set_title(f'Reaction vs Recovery (r={r:.3f})', fontsize=13, fontweight='bold')
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/analysis_subscore_correlations.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved analysis_subscore_correlations.png')

# ============================================================================
# FIGURE 8: BAYESIAN SHRINKAGE EFFECT
# ============================================================================

print('Generating Figure 8: Bayesian Shrinkage Effect')

fig, ax = plt.subplots(figsize=(10, 8))

# Plot raw vs Bayesian scores
for idx, row in leaderboard.iterrows():
    ax.plot([row['n_reps'], row['n_reps']],
           [row['raw_stickiness'], row['stickiness_bayesian']],
           'k-', alpha=0.3, linewidth=1)

# Scatter
scatter1 = ax.scatter(leaderboard['n_reps'], leaderboard['raw_stickiness'],
                     s=100, c='lightcoral', alpha=0.7, edgecolors='black',
                     linewidths=1.5, label='Raw Score')
scatter2 = ax.scatter(leaderboard['n_reps'], leaderboard['stickiness_bayesian'],
                     s=100, c='steelblue', alpha=0.7, edgecolors='black',
                     linewidths=1.5, label='Bayesian Score')

ax.set_xlabel('Number of Reps', fontsize=13, fontweight='bold')
ax.set_ylabel('Stickiness Score', fontsize=13, fontweight='bold')
ax.set_title('Bayesian Shrinkage Effect (Low-sample DBs Regress to Prior)', fontsize=15, fontweight='bold')
ax.legend(fontsize=12, loc='best')
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/analysis_bayesian_shrinkage.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved analysis_bayesian_shrinkage.png')

# ============================================================================
# FIGURE 9: SAMPLE SIZE BY DB
# ============================================================================

print('Generating Figure 9: Sample Size Distribution')

fig, ax = plt.subplots(figsize=(10, 6))

db_sorted = leaderboard.sort_values('n_reps', ascending=False)
x_pos = np.arange(len(db_sorted))

bars = ax.bar(x_pos, db_sorted['n_reps'], color='steelblue', alpha=0.8, edgecolor='black')

# Color code by threshold
for i, reps in enumerate(db_sorted['n_reps']):
    if reps >= 10:
        bars[i].set_color('green')
    elif reps >= 8:
        bars[i].set_color('orange')
    else:
        bars[i].set_color('lightcoral')

ax.axhline(10, color='green', linestyle='--', linewidth=2, label='10+ reps (high confidence)', alpha=0.7)
ax.axhline(8, color='orange', linestyle='--', linewidth=2, label='8+ reps (good)', alpha=0.7)
ax.axhline(5, color='red', linestyle='--', linewidth=2, label='5+ reps (minimum)', alpha=0.7)

ax.set_xlabel('DB Rank (by sample size)', fontsize=13, fontweight='bold')
ax.set_ylabel('Number of Reps', fontsize=13, fontweight='bold')
ax.set_title('Rep Count Distribution Across DBs', fontsize=15, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/analysis_sample_sizes.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved analysis_sample_sizes.png')

# ============================================================================
# SUMMARY
# ============================================================================

print('\n' + '=' * 80)
print('FIGURE GENERATION SUMMARY')
print('=' * 80)

figures_created = [
    'methodology_stickiness_framework.png',
    'methodology_rep_extraction_flow.png',
    'leaderboard_overall_stickiness.png',
    'leaderboard_subscores_comparison.png',
    'validation_split_half_reliability.png',
    'analysis_score_distributions.png',
    'analysis_subscore_correlations.png',
    'analysis_bayesian_shrinkage.png',
    'analysis_sample_sizes.png'
]

print(f'\nGenerated {len(figures_created)} figures in {FIGURES_DIR}/')
for fig in figures_created:
    filepath = f'{FIGURES_DIR}/{fig}'
    if os.path.exists(filepath):
        size_kb = os.path.getsize(filepath) / 1024
        print(f'  ✓ {fig} ({size_kb:.1f} KB)')

print('\n' + '=' * 80)
print('FIGURE GENERATION COMPLETE')
print('=' * 80)
print(f'\nAll figures saved to: {FIGURES_DIR}/')
print('\nReady for deck building!')
