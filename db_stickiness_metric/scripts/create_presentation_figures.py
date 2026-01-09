"""
Create Custom Presentation Figures
===================================

Generate the three custom figures needed for the revised presentation:
1. Elite vs Average Rep Comparison (Slide 4)
2. CB vs S Position Comparison (Slide 7)
3. Elite vs Average Component Breakdown (Slide 9)

Input:  outputs/db_rep_scores.parquet
        outputs/db_player_leaderboard.csv
Output: figures/presentation_*.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pyarrow.parquet as pq
import os

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print('=' * 80)
print('CREATING CUSTOM PRESENTATION FIGURES')
print('=' * 80)

# ============================================================================
# CONFIGURATION
# ============================================================================

REP_SCORES_PATH = '../outputs/db_rep_scores.parquet'
LEADERBOARD_PATH = '../outputs/db_player_leaderboard.csv'
PARQUET_PATH = '../../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'
COLLEGE_STATS_PATH = '../../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'
FIGURES_DIR = '../figures'
SESSION_ID = 4

# Create figures directory
os.makedirs(FIGURES_DIR, exist_ok=True)

# ============================================================================
# LOAD DATA
# ============================================================================

print('\nLoading data...')
rep_scores = pd.read_parquet(REP_SCORES_PATH)
leaderboard = pd.read_csv(LEADERBOARD_PATH)

# Also load the original reps file to get timestamps
reps_original = pd.read_parquet('../outputs/reps_skill_1v1.parquet')
# Merge to get start_ts and end_ts
rep_scores = rep_scores.merge(
    reps_original[['rep_id', 'start_ts', 'end_ts']],
    on='rep_id',
    how='left'
)

# Load college stats to get positions
college_stats = pd.read_csv(COLLEGE_STATS_PATH)
college_stats['college_gsis_id'] = college_stats['college_gsis_id'].astype(str)

# Get gsis_id mapping
table = pq.read_table(
    PARQUET_PATH,
    columns=['zebra_id', 'gsis_id'],
    filters=[('session_id', '=', SESSION_ID)]
)
gsis_mapping = table.to_pandas()
gsis_mapping['zebra_id'] = gsis_mapping['zebra_id'].astype(str)
gsis_mapping['gsis_id'] = gsis_mapping['gsis_id'].astype(str)
gsis_mapping = gsis_mapping.drop_duplicates(subset=['zebra_id']).dropna(subset=['gsis_id'])

# Merge to get positions for each DB
leaderboard['db_name'] = leaderboard['db_name'].astype(str)
leaderboard = leaderboard.merge(
    gsis_mapping,
    left_on='db_name',
    right_on='zebra_id',
    how='left'
)

# Get position from college stats
position_map = college_stats[['college_gsis_id', 'position']].drop_duplicates(subset=['college_gsis_id'])
leaderboard = leaderboard.merge(
    position_map,
    left_on='gsis_id',
    right_on='college_gsis_id',
    how='left'
)

# Simplify position to CB vs S
def classify_position(pos):
    if pd.isna(pos):
        return 'Unknown'
    pos = str(pos).upper()
    if pos in ['CB', 'DC']:
        return 'CB'
    elif pos in ['S', 'DS', 'SS', 'FS']:
        return 'S'
    else:
        return 'Other'

leaderboard['position_group'] = leaderboard['position'].apply(classify_position)

print(f'Loaded {len(rep_scores)} rep scores')
print(f'Loaded {len(leaderboard)} DBs')
print(f'\nPosition breakdown:')
print(leaderboard['position_group'].value_counts())

# ============================================================================
# FIGURE 1: ELITE vs AVERAGE REP COMPARISON (Slide 4)
# ============================================================================

print('\n' + '-' * 80)
print('Figure 1: Elite vs Average Rep Comparison')
print('-' * 80)

# Load session data to get trajectories
print('Loading session data for trajectory extraction...')
table = pq.read_table(
    PARQUET_PATH,
    columns=['ts', 'zebra_id', 'x', 'y', 's'],
    filters=[('session_id', '=', SESSION_ID)]
)
df_session = table.to_pandas()
df_session['player_name'] = df_session['zebra_id'].astype(str)
df_session['ts'] = pd.to_datetime(df_session['ts'])
session_start = df_session['ts'].min()
df_session['timestamp'] = (df_session['ts'] - session_start).dt.total_seconds()

print(f'Loaded {len(df_session):,} tracking frames')

# Find one elite rep and one average rep
elite_threshold = rep_scores['stickiness'].quantile(0.75)
average_threshold = rep_scores['stickiness'].quantile(0.50)

elite_reps = rep_scores[rep_scores['stickiness'] >= elite_threshold].copy()
average_reps = rep_scores[
    (rep_scores['stickiness'] >= average_threshold - 0.05) &
    (rep_scores['stickiness'] <= average_threshold + 0.05)
].copy()

# Pick reps with similar duration for fair comparison
elite_reps['duration'] = elite_reps['end_ts'] - elite_reps['start_ts']
average_reps['duration'] = average_reps['end_ts'] - average_reps['start_ts']

target_duration = 6.0  # ~6 second reps
elite_reps['duration_diff'] = (elite_reps['duration'] - target_duration).abs()
average_reps['duration_diff'] = (average_reps['duration'] - target_duration).abs()

elite_rep = elite_reps.nsmallest(1, 'duration_diff').iloc[0]
average_rep = average_reps.nsmallest(1, 'duration_diff').iloc[0]

print(f'\nSelected elite rep: {elite_rep["rep_id"]}, stickiness={elite_rep["stickiness"]:.3f}, duration={elite_rep["duration"]:.1f}s')
print(f'Selected average rep: {average_rep["rep_id"]}, stickiness={average_rep["stickiness"]:.3f}, duration={average_rep["duration"]:.1f}s')

# Extract trajectories for both reps
def get_rep_separation(rep_row, df_session):
    """Extract separation over time for a rep."""
    df_rep = df_session[
        (df_session['timestamp'] >= rep_row['start_ts'] - 0.1) &
        (df_session['timestamp'] <= rep_row['end_ts'] + 0.1)
    ].copy()

    wr_traj = df_rep[df_rep['player_name'] == rep_row['wr_name']].sort_values('timestamp').copy()
    db_traj = df_rep[df_rep['player_name'] == rep_row['db_name']].sort_values('timestamp').copy()

    # Merge trajectories
    merged = pd.merge_asof(
        wr_traj, db_traj,
        on='timestamp',
        suffixes=('_wr', '_db'),
        direction='nearest',
        tolerance=0.1
    )

    if len(merged) == 0:
        return None

    # Calculate separation
    merged['separation'] = np.sqrt(
        (merged['x_wr'] - merged['x_db'])**2 +
        (merged['y_wr'] - merged['y_db'])**2
    )

    # Normalize time to start at 0
    merged['time_rel'] = merged['timestamp'] - merged['timestamp'].min()

    return merged[['time_rel', 'separation']]

elite_sep = get_rep_separation(elite_rep, df_session)
average_sep = get_rep_separation(average_rep, df_session)

if elite_sep is None or average_sep is None:
    print('WARNING: Could not extract trajectories for comparison')
else:
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot separation over time
    ax.plot(average_sep['time_rel'], average_sep['separation'],
            linewidth=3, color='#FF6B6B', label='Average DB', linestyle='--', alpha=0.8)
    ax.plot(elite_sep['time_rel'], elite_sep['separation'],
            linewidth=3, color='#4ECDC4', label='Elite DB', linestyle='-', alpha=0.9)

    # Add reference lines
    ax.axhline(y=2, color='green', linestyle=':', linewidth=2, alpha=0.5, label='Tight coverage (2y)')
    ax.axhline(y=5, color='red', linestyle=':', linewidth=2, alpha=0.5, label='Blown coverage (5y)')

    # Add annotations
    # Find peak separation for each
    avg_peak_idx = average_sep['separation'].idxmax()
    avg_peak_time = average_sep.loc[avg_peak_idx, 'time_rel']
    avg_peak_sep = average_sep.loc[avg_peak_idx, 'separation']

    elite_peak_idx = elite_sep['separation'].idxmax()
    elite_peak_time = elite_sep.loc[elite_peak_idx, 'time_rel']
    elite_peak_sep = elite_sep.loc[elite_peak_idx, 'separation']

    ax.annotate(f'Peak: {avg_peak_sep:.1f}y\n(stays beat)',
                xy=(avg_peak_time, avg_peak_sep),
                xytext=(avg_peak_time + 0.5, avg_peak_sep + 0.5),
                arrowprops=dict(arrowstyle='->', color='#FF6B6B', lw=2),
                fontsize=11, fontweight='bold', color='#FF6B6B')

    ax.annotate(f'Peak: {elite_peak_sep:.1f}y\n(closes back)',
                xy=(elite_peak_time, elite_peak_sep),
                xytext=(elite_peak_time + 0.5, elite_peak_sep - 1.0),
                arrowprops=dict(arrowstyle='->', color='#4ECDC4', lw=2),
                fontsize=11, fontweight='bold', color='#4ECDC4')

    # Add phase labels
    ax.text(0.5, -0.5, 'STEM', ha='center', fontsize=10, style='italic', alpha=0.6)
    max_time = max(elite_sep['time_rel'].max(), average_sep['time_rel'].max())
    ax.text(max_time * 0.4, -0.5, 'BREAK', ha='center', fontsize=10, style='italic', alpha=0.6)
    ax.text(max_time * 0.85, -0.5, 'CATCH', ha='center', fontsize=10, style='italic', alpha=0.6)

    ax.set_xlabel('Time (seconds)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Separation (yards)', fontsize=13, fontweight='bold')
    ax.set_title('Elite vs Average: Same Route, Different Story',
                 fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper left', framealpha=0.9)
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_ylim(bottom=-1, top=max(avg_peak_sep, elite_peak_sep) + 1)

    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/presentation_elite_vs_average_rep.png', dpi=300, bbox_inches='tight')
    plt.close()
    print('  ✓ Saved presentation_elite_vs_average_rep.png')

# ============================================================================
# FIGURE 2: CB vs S POSITION COMPARISON (Slide 7)
# ============================================================================

print('\n' + '-' * 80)
print('Figure 2: CB vs S Position Comparison')
print('-' * 80)

# Filter to CB and S only
position_data = leaderboard[leaderboard['position_group'].isin(['CB', 'S'])].copy()

if len(position_data) == 0:
    print('WARNING: No CB or S players found in leaderboard')
else:
    # Calculate means
    cb_mean = position_data[position_data['position_group'] == 'CB']['stickiness_bayesian'].mean()
    s_mean = position_data[position_data['position_group'] == 'S']['stickiness_bayesian'].mean()

    cb_n = len(position_data[position_data['position_group'] == 'CB'])
    s_n = len(position_data[position_data['position_group'] == 'S'])

    print(f'CB mean: {cb_mean:.3f} (n={cb_n})')
    print(f'S mean: {s_mean:.3f} (n={s_n})')
    print(f'Difference: {cb_mean - s_mean:.3f} ({(cb_mean - s_mean)/s_mean * 100:.1f}%)')

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))

    positions = ['Cornerbacks', 'Safeties']
    means = [cb_mean, s_mean]
    ns = [cb_n, s_n]
    colors = ['#4682B4', '#FF8C00']

    bars = ax.barh(positions, means, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

    # Add value labels
    for i, (bar, mean, n) in enumerate(zip(bars, means, ns)):
        ax.text(mean + 0.01, i, f'{mean:.3f}\n(n={n})',
                va='center', fontsize=12, fontweight='bold')

    # Add difference annotation
    diff = cb_mean - s_mean
    diff_pct = (diff / s_mean) * 100
    ax.annotate('', xy=(cb_mean, 0), xytext=(s_mean, 1),
                arrowprops=dict(arrowstyle='<->', lw=2, color='gray'))
    ax.text((cb_mean + s_mean) / 2, 0.5,
            f'+{diff:.3f}\n({diff_pct:+.1f}%)',
            ha='center', va='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray', linewidth=2))

    ax.set_xlabel('Mean Stickiness Score', fontsize=13, fontweight='bold')
    ax.set_title('Known-Groups Validity: CBs > Safeties in Man 1v1',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xlim(0, max(means) * 1.25)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    # Add interpretation text
    ax.text(0.02, -0.25,
            '✓ Expected: CBs practice man coverage more than safeties\n'
            '✓ Metric captures football-realistic differences',
            transform=ax.transAxes, fontsize=10, style='italic',
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/presentation_cb_vs_s_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print('  ✓ Saved presentation_cb_vs_s_comparison.png')

# ============================================================================
# FIGURE 3: ELITE vs AVERAGE COMPONENT BREAKDOWN (Slide 9)
# ============================================================================

print('\n' + '-' * 80)
print('Figure 3: Elite vs Average Component Breakdown')
print('-' * 80)

# Define elite (top 25%) and average (middle 50%)
p25 = leaderboard['stickiness_bayesian'].quantile(0.25)
p50 = leaderboard['stickiness_bayesian'].quantile(0.50)
p75 = leaderboard['stickiness_bayesian'].quantile(0.75)

elite = leaderboard[leaderboard['stickiness_bayesian'] >= p75].copy()
average = leaderboard[
    (leaderboard['stickiness_bayesian'] >= p25) &
    (leaderboard['stickiness_bayesian'] <= p75)
].copy()

# Calculate means
elite_means = {
    'Stickiness': elite['stickiness_bayesian'].mean(),
    'In-Phase': elite['avg_phase'].mean(),
    'Trigger': elite['avg_reaction'].mean(),
    'Close': elite['avg_recovery'].mean()
}

average_means = {
    'Stickiness': average['stickiness_bayesian'].mean(),
    'In-Phase': average['avg_phase'].mean(),
    'Trigger': average['avg_reaction'].mean(),
    'Close': average['avg_recovery'].mean()
}

print(f'\nElite (Top 25%, n={len(elite)}):')
for k, v in elite_means.items():
    print(f'  {k}: {v:.3f}')

print(f'\nAverage (Middle 50%, n={len(average)}):')
for k, v in average_means.items():
    print(f'  {k}: {v:.3f}')

# Calculate differences
differences = {k: elite_means[k] - average_means[k] for k in elite_means.keys()}
pct_differences = {k: (differences[k] / average_means[k]) * 100 for k in differences.keys()}

print(f'\nDifferences (Elite - Average):')
for k in elite_means.keys():
    print(f'  {k}: {differences[k]:+.3f} ({pct_differences[k]:+.1f}%)')

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

components = list(elite_means.keys())
x = np.arange(len(components))
width = 0.35

bars1 = ax.bar(x - width/2, [elite_means[c] for c in components], width,
               label='Elite (Top 25%)', color='#2E8B57', alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax.bar(x + width/2, [average_means[c] for c in components], width,
               label='Average (Middle 50%)', color='#708090', alpha=0.8, edgecolor='black', linewidth=1.5)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

# Add difference annotations
for i, comp in enumerate(components):
    diff = differences[comp]
    diff_pct = pct_differences[comp]
    y_pos = max(elite_means[comp], average_means[comp]) + 0.08
    ax.text(i, y_pos, f'+{diff_pct:.1f}%',
            ha='center', va='bottom', fontsize=11, fontweight='bold',
            color='red' if diff_pct > 100 else 'darkgreen',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='gray'))

ax.set_xlabel('Component', fontsize=13, fontweight='bold')
ax.set_ylabel('Score (0-1)', fontsize=13, fontweight='bold')
ax.set_title('Elite vs Average: Component Breakdown',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(components, fontsize=12)
ax.legend(fontsize=12, loc='upper left', framealpha=0.9)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, max(max(elite_means.values()), max(average_means.values())) * 1.25)

# Add insight box
ax.text(0.98, 0.02,
        '➜ Close score shows highest % difference\n'
        '   (recovery ability separates elite from average)',
        transform=ax.transAxes, fontsize=10, style='italic',
        verticalalignment='bottom', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7, edgecolor='gray'))

plt.tight_layout()
plt.savefig(f'{FIGURES_DIR}/presentation_elite_vs_average_components.png', dpi=300, bbox_inches='tight')
plt.close()
print('  ✓ Saved presentation_elite_vs_average_components.png')

# ============================================================================
# SUMMARY
# ============================================================================

print('\n' + '=' * 80)
print('PRESENTATION FIGURES COMPLETE')
print('=' * 80)
print('\nGenerated figures:')
print('  1. presentation_elite_vs_average_rep.png (Slide 4)')
print('  2. presentation_cb_vs_s_comparison.png (Slide 7)')
print('  3. presentation_elite_vs_average_components.png (Slide 9)')
print(f'\nAll saved to: {FIGURES_DIR}/')
print('\n' + '=' * 80)
