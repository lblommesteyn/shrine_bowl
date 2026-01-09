"""
Compute DB Stickiness - Script 2
=================================

Compute Man Coverage Stickiness scores for all DBs from extracted reps.
Includes Phase, Reaction, and Recovery sub-scores, plus Bayesian shrinkage.

Input:  outputs/reps_skill_1v1.parquet
        data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet
        data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv
Output: outputs/db_rep_scores.parquet (rep-level)
        outputs/db_player_leaderboard.csv (player-level aggregates)

Runtime: ~3-5 minutes
Memory:  ~1GB peak
"""

import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import os
import sys
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
REPS_PATH = '../outputs/reps_skill_1v1.parquet'
PARQUET_PATH = '../../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'
COLLEGE_STATS_PATH = '../../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'
OUTPUT_REP_SCORES = '../outputs/db_rep_scores.parquet'
OUTPUT_LEADERBOARD = '../outputs/db_player_leaderboard.csv'

SESSION_ID = 4

# Phase score thresholds
PHASE_TIGHT_THRESHOLD = 2.0       # yards
PHASE_ACCEPTABLE_THRESHOLD = 3.5  # yards
LEVERAGE_CONSISTENCY_BONUS = 0.10

# Reaction score thresholds
MAX_REACTION_LATENCY = 0.5        # seconds
PANIC_FLIP_THRESHOLD = 120        # degrees
ANGULAR_VEL_BREAK_THRESHOLD = 40  # deg/s (lowered from 60 to detect more subtle breaks)

# Recovery score thresholds
SEPARATION_GROWTH_THRESHOLD = 1.5  # yards
RECOVERY_WINDOW = 1.0             # seconds

# Combined weights
WEIGHT_PHASE = 0.45
WEIGHT_REACTION = 0.30
WEIGHT_RECOVERY = 0.25

# Bayesian shrinkage
SHRINKAGE_K = 15  # Equivalent to "15 reps of prior confidence"
PRIOR_STD = 0.10  # ±0.10 around grand mean

print('=' * 80)
print('COMPUTE DB STICKINESS - SCRIPT 2')
print('=' * 80)
print(f'\nWeights: Phase={WEIGHT_PHASE:.0%}, Reaction={WEIGHT_REACTION:.0%}, Recovery={WEIGHT_RECOVERY:.0%}')
print(f'Bayesian shrinkage: k={SHRINKAGE_K} reps')

# ============================================================================
# LOAD DATA
# ============================================================================

print('\n' + '-' * 80)
print('Loading extracted reps')
print('-' * 80)

if not os.path.exists(REPS_PATH):
    print(f'ERROR: Reps file not found at {REPS_PATH}')
    print('Please run extract_skill_1v1_reps.py first.')
    sys.exit(1)

reps_df = pd.read_parquet(REPS_PATH)
print(f'Loaded {len(reps_df)} reps')
print(f'  WRs: {reps_df["wr_name"].nunique()}')
print(f'  DBs: {reps_df["db_name"].nunique()}')

# ============================================================================
# STICKINESS SUB-SCORE FUNCTIONS
# ============================================================================

def compute_phase_score(wr_traj, db_traj):
    """
    Compute phase score: % of route where DB maintains proximity.

    Returns: (score, metadata_dict)
    """
    # Merge trajectories on timestamp (tolerance 0.1s)
    merged = pd.merge_asof(
        wr_traj, db_traj,
        on='timestamp',
        suffixes=('_wr', '_db'),
        direction='nearest',
        tolerance=0.1
    )

    if len(merged) < 3:
        return 0.0, {'insufficient_data': True}

    # Calculate separation
    merged['separation'] = np.sqrt(
        (merged['x_wr'] - merged['x_db'])**2 +
        (merged['y_wr'] - merged['y_db'])**2
    )

    # Proximity score
    n_tight = (merged['separation'] <= PHASE_TIGHT_THRESHOLD).sum()
    n_acceptable = (merged['separation'] <= PHASE_ACCEPTABLE_THRESHOLD).sum()
    n_total = len(merged)

    base_score = (n_tight / n_total) + ((n_acceptable - n_tight) / n_total) * 0.5

    # Leverage consistency (angular variance of DB position relative to WR)
    merged['dx'] = merged['x_db'] - merged['x_wr']
    merged['dy'] = merged['y_db'] - merged['y_wr']
    merged['angle'] = np.arctan2(merged['dy'], merged['dx'])

    angle_std = merged['angle'].std()
    if np.isnan(angle_std):
        angle_std = 0

    leverage_bonus = LEVERAGE_CONSISTENCY_BONUS * max(0, 1 - angle_std / np.pi)

    phase_score = min(1.0 + LEVERAGE_CONSISTENCY_BONUS, base_score + leverage_bonus)

    metadata = {
        'avg_separation': merged['separation'].mean(),
        'tight_pct': n_tight / n_total,
        'acceptable_pct': n_acceptable / n_total,
        'leverage_consistency': leverage_bonus
    }

    return phase_score, metadata


def compute_reaction_score(wr_traj, db_traj):
    """
    Compute reaction score: DB's response to WR route breaks.

    Returns: (score, metadata_dict)
    """
    if len(wr_traj) < 10 or len(db_traj) < 10:
        return 0.5, {'insufficient_data': True}

    # Detect WR breaks using angular velocity AND speed changes
    wr_traj = wr_traj.copy()

    # Calculate angular velocity (direction change rate)
    wr_traj['dir_change'] = wr_traj['dir'].diff().abs()
    # Handle wrap-around (e.g., 359° to 1° is 2°, not 358°)
    wr_traj['dir_change'] = wr_traj['dir_change'].apply(lambda x: min(x, 360 - x) if not pd.isna(x) else 0)
    wr_traj['dt'] = wr_traj['timestamp'].diff()
    wr_traj['angular_vel'] = wr_traj['dir_change'] / wr_traj['dt']
    wr_traj['angular_vel'] = wr_traj['angular_vel'].fillna(0).abs()

    # Calculate speed change (acceleration/deceleration)
    wr_traj['speed_change'] = wr_traj['speed'].diff().abs()
    wr_traj['accel'] = wr_traj['speed_change'] / wr_traj['dt']
    wr_traj['accel'] = wr_traj['accel'].fillna(0).abs()

    # Find break point in middle 60% of route (avoid start/end noise)
    route_duration = wr_traj['timestamp'].max() - wr_traj['timestamp'].min()
    search_start = wr_traj['timestamp'].min() + route_duration * 0.2
    search_end = wr_traj['timestamp'].max() - route_duration * 0.2

    search_window = wr_traj[
        (wr_traj['timestamp'] >= search_start) &
        (wr_traj['timestamp'] <= search_end) &
        (wr_traj['speed'] > 2.5)  # Must be moving
    ]

    if len(search_window) == 0:
        return 0.5, {'no_break_detected': True}  # Neutral score

    # Detect break using EITHER angular velocity OR speed change
    max_angular_vel = search_window['angular_vel'].max()
    max_accel = search_window['accel'].max()

    # Use whichever signal is stronger
    if max_angular_vel >= ANGULAR_VEL_BREAK_THRESHOLD:
        break_idx = search_window['angular_vel'].idxmax()
        break_ts = wr_traj.loc[break_idx, 'timestamp']
    elif max_accel >= 3.0:  # 3 yds/s^2 acceleration threshold
        break_idx = search_window['accel'].idxmax()
        break_ts = wr_traj.loc[break_idx, 'timestamp']
    else:
        # No clear break - use gradual scoring instead of default 0.5
        # Score based on separation variance (higher variance = more dynamic route)
        merged = pd.merge_asof(
            wr_traj, db_traj,
            on='timestamp',
            suffixes=('_wr', '_db'),
            direction='nearest',
            tolerance=0.1
        )
        if len(merged) > 0:
            merged['sep'] = np.sqrt((merged['x_wr'] - merged['x_db'])**2 + (merged['y_wr'] - merged['y_db'])**2)
            sep_variance = merged['sep'].var()
            # Higher variance = more reaction opportunities
            dynamic_score = 0.3 + min(0.4, sep_variance / 10.0)  # Scale 0.3-0.7
            return dynamic_score, {'no_sharp_break': True, 'separation_variance': sep_variance}
        return 0.5, {'no_break_detected': True}

    # Find DB's reaction
    db_traj = db_traj.copy()
    db_post_break = db_traj[db_traj['timestamp'] >= break_ts].copy()

    if len(db_post_break) < 3:
        return 0.0, {'insufficient_tracking': True}

    db_post_break['dir_change'] = db_post_break['dir'].diff().abs()
    db_post_break['dir_change'] = db_post_break['dir_change'].apply(lambda x: min(x, 360 - x) if not pd.isna(x) else 0)
    db_post_break['dt'] = db_post_break['timestamp'].diff()
    db_post_break['angular_vel'] = db_post_break['dir_change'] / db_post_break['dt']
    db_post_break['angular_vel'] = db_post_break['angular_vel'].fillna(0).abs()

    db_reactions = db_post_break[db_post_break['angular_vel'] > 20]  # deg/s threshold (lowered from 30 for more sensitivity)

    if len(db_reactions) == 0:
        return 0.0, {'no_reaction': True}

    reaction_ts = db_reactions['timestamp'].min()
    reaction_latency = reaction_ts - break_ts

    # DB direction change severity
    db_pre_break = db_traj[db_traj['timestamp'] < break_ts]
    if len(db_pre_break) == 0:
        db_dir_before = 0
    else:
        db_dir_before = db_pre_break.iloc[-1]['dir']

    reaction_idx = db_post_break['timestamp'].idxmin()
    db_dir_after = db_post_break.loc[reaction_idx, 'dir']

    db_dir_change = abs(db_dir_after - db_dir_before)
    db_dir_change = min(db_dir_change, 360 - db_dir_change)

    # Score components
    latency_score = max(0, 1 - reaction_latency / MAX_REACTION_LATENCY)
    flip_score = max(0, 1 - db_dir_change / PANIC_FLIP_THRESHOLD)

    reaction_score = 0.6 * latency_score + 0.4 * flip_score

    metadata = {
        'break_time': break_ts,
        'reaction_latency': reaction_latency,
        'db_dir_change': db_dir_change,
        'latency_score': latency_score,
        'flip_score': flip_score
    }

    return reaction_score, metadata


def compute_recovery_score(wr_traj, db_traj):
    """
    Compute recovery score: DB's ability to close separation gaps.

    Returns: (score, metadata_dict)
    """
    # Merge trajectories
    merged = pd.merge_asof(
        wr_traj, db_traj,
        on='timestamp',
        suffixes=('_wr', '_db'),
        direction='nearest',
        tolerance=0.1
    )

    if len(merged) < 5:
        return 0.5, {'insufficient_data': True}

    merged['separation'] = np.sqrt(
        (merged['x_wr'] - merged['x_db'])**2 +
        (merged['y_wr'] - merged['y_db'])**2
    )

    # Find peak separation
    peak_idx = merged['separation'].idxmax()
    peak_sep = merged.loc[peak_idx, 'separation']
    peak_ts = merged.loc[peak_idx, 'timestamp']
    start_sep = merged.iloc[0]['separation']

    if peak_sep - start_sep < SEPARATION_GROWTH_THRESHOLD:
        return 0.7, {'no_separation_growth': True}  # Good baseline

    # Recovery window: 1 second after peak
    recovery_data = merged[
        (merged['timestamp'] > peak_ts) &
        (merged['timestamp'] <= peak_ts + RECOVERY_WINDOW)
    ]

    if len(recovery_data) == 0:
        return 0.0, {'route_ended_at_peak': True}

    final_sep = recovery_data.iloc[-1]['separation']
    closed_gap = peak_sep - final_sep
    separation_growth = peak_sep - start_sep

    recovery_pct = max(0, closed_gap / separation_growth)

    # Closing speed
    recovery_time = recovery_data.iloc[-1]['timestamp'] - peak_ts
    closing_speed = closed_gap / recovery_time if recovery_time > 0 else 0

    speed_score = min(1.0, closing_speed / 4.0)

    recovery_score = 0.7 * recovery_pct + 0.3 * speed_score

    metadata = {
        'peak_separation': peak_sep,
        'final_separation': final_sep,
        'closed_gap': closed_gap,
        'closing_speed': closing_speed,
        'recovery_pct': recovery_pct
    }

    return recovery_score, metadata


def compute_combined_stickiness(phase_score, reaction_score, recovery_score):
    """Combine sub-scores into overall stickiness metric."""
    return (WEIGHT_PHASE * phase_score +
            WEIGHT_REACTION * reaction_score +
            WEIGHT_RECOVERY * recovery_score)


# ============================================================================
# LOAD SESSION DATA (ONCE)
# ============================================================================

print('\n' + '-' * 80)
print('Loading session 4 tracking data')
print('-' * 80)

print(f'Reading from: {PARQUET_PATH}')
table = pq.read_table(
    PARQUET_PATH,
    columns=['ts', 'zebra_id', 'x', 'y', 's', 'dir'],
    filters=[('session_id', '=', SESSION_ID)]
)
df_session = table.to_pandas()
print(f'Loaded {len(df_session):,} frames')

# Use zebra_id as player identifier (matches wr_name/db_name in reps)
df_session['player_name'] = df_session['zebra_id'].astype(str)

df_session['ts'] = pd.to_datetime(df_session['ts'])
session_start = df_session['ts'].min()
df_session['timestamp'] = (df_session['ts'] - session_start).dt.total_seconds()

# Calculate speed if not present
if 's' in df_session.columns:
    df_session['speed'] = df_session['s']
else:
    print('Calculating speed from position changes...')
    df_session = df_session.sort_values(['player_name', 'timestamp'])
    df_session['dx'] = df_session.groupby('player_name')['x'].diff()
    df_session['dy'] = df_session.groupby('player_name')['y'].diff()
    df_session['dt'] = df_session.groupby('player_name')['timestamp'].diff()
    df_session['speed'] = np.sqrt(df_session['dx']**2 + df_session['dy']**2) / df_session['dt']
    df_session['speed'] = df_session['speed'].fillna(0)

print('Session data loaded and preprocessed')

# ============================================================================
# PROCESS ALL REPS
# ============================================================================

print('\n' + '-' * 80)
print('Computing stickiness scores for all reps')
print('-' * 80)

rep_scores = []

for idx, rep in reps_df.iterrows():
    print(f'Processing rep {idx+1}/{len(reps_df)}: {rep["wr_name"]} vs {rep["db_name"]}', end='\r')

    # Filter to rep time window
    df_rep = df_session[
        (df_session['timestamp'] >= rep['start_ts'] - 0.2) &
        (df_session['timestamp'] <= rep['end_ts'] + 0.2)
    ]

    wr_traj = df_rep[df_rep['player_name'] == rep['wr_name']].sort_values('timestamp').copy()
    db_traj = df_rep[df_rep['player_name'] == rep['db_name']].sort_values('timestamp').copy()

    if len(wr_traj) < 5 or len(db_traj) < 5:
        print(f'\nWARNING: Insufficient data for rep {idx}: {len(wr_traj)} WR frames, {len(db_traj)} DB frames')
        continue

    # Compute sub-scores
    phase_score, phase_meta = compute_phase_score(wr_traj, db_traj)
    reaction_score, reaction_meta = compute_reaction_score(wr_traj, db_traj)
    recovery_score, recovery_meta = compute_recovery_score(wr_traj, db_traj)

    combined = compute_combined_stickiness(phase_score, reaction_score, recovery_score)

    rep_scores.append({
        'rep_id': rep['rep_id'],
        'wr_name': rep['wr_name'],
        'db_name': rep['db_name'],
        'station_id': rep['station_id'],
        'confidence': rep['confidence'],
        'phase_score': phase_score,
        'reaction_score': reaction_score,
        'recovery_score': recovery_score,
        'stickiness': combined,
        **{f'phase_{k}': v for k, v in phase_meta.items()},
        **{f'reaction_{k}': v for k, v in reaction_meta.items()},
        **{f'recovery_{k}': v for k, v in recovery_meta.items()}
    })

print()  # New line after progress

# Convert to DataFrame
rep_scores_df = pd.DataFrame(rep_scores)

print(f'\nComputed scores for {len(rep_scores_df)} reps')
print(f'\nStickiness Distribution:')
print(rep_scores_df['stickiness'].describe())

# Save rep-level scores
os.makedirs(os.path.dirname(OUTPUT_REP_SCORES), exist_ok=True)
rep_scores_df.to_parquet(OUTPUT_REP_SCORES, index=False)
print(f'\nSaved rep-level scores to {OUTPUT_REP_SCORES}')

# ============================================================================
# AGGREGATE TO PLAYER LEVEL
# ============================================================================

print('\n' + '-' * 80)
print('Aggregating to player level')
print('-' * 80)

db_summary = rep_scores_df.groupby('db_name').agg({
    'stickiness': ['mean', 'std', 'count'],
    'phase_score': 'mean',
    'reaction_score': 'mean',
    'recovery_score': 'mean'
}).reset_index()

db_summary.columns = ['db_name', 'raw_stickiness', 'stickiness_std',
                      'n_reps', 'avg_phase', 'avg_reaction', 'avg_recovery']

print(f'Aggregated {len(db_summary)} DBs')

# ============================================================================
# APPLY BAYESIAN SHRINKAGE
# ============================================================================

print('\n' + '-' * 80)
print('Applying Bayesian shrinkage with college priors')
print('-' * 80)

# Load college stats
if os.path.exists(COLLEGE_STATS_PATH):
    college_stats = pd.read_csv(COLLEGE_STATS_PATH)

    # Filter to DBs
    db_college = college_stats[
        college_stats['position'].isin(['DC', 'DS', 'IB', 'CB', 'S', 'DB'])
    ].copy()

    # Aggregate by player (sum across seasons)
    db_college_agg = db_college.groupby('player_name').agg({
        'defense_total_tackles': 'sum',
        'defense_pass_breakups': 'sum',
        'defense_interceptions': 'sum',
        'defense_tackles_for_loss': 'sum'
    }).reset_index()

    # Z-score normalization
    for col in ['defense_total_tackles', 'defense_pass_breakups',
                'defense_interceptions', 'defense_tackles_for_loss']:
        mean = db_college_agg[col].mean()
        std = db_college_agg[col].std()
        if std > 0:
            db_college_agg[f'{col}_z'] = (db_college_agg[col] - mean) / std
        else:
            db_college_agg[f'{col}_z'] = 0

    # Compute college production score
    db_college_agg['college_prior'] = (
        0.40 * db_college_agg['defense_pass_breakups_z'] +
        0.35 * db_college_agg['defense_interceptions_z'] +
        0.15 * db_college_agg['defense_tackles_for_loss_z'] -
        0.10 * db_college_agg['defense_total_tackles_z']
    )

    # Map to prior stickiness
    grand_mean = db_summary['raw_stickiness'].mean()

    db_college_agg['prior_stickiness'] = (
        grand_mean + PRIOR_STD * db_college_agg['college_prior']
    ).clip(0, 1.0)

    # Merge priors into summary
    db_summary = db_summary.merge(
        db_college_agg[['player_name', 'prior_stickiness']],
        left_on='db_name',
        right_on='player_name',
        how='left'
    )
    db_summary = db_summary.drop(columns=['player_name'], errors='ignore')

    # Fill missing priors with grand mean
    db_summary['prior_stickiness'] = db_summary['prior_stickiness'].fillna(grand_mean)

    print(f'Merged college priors for {db_summary["prior_stickiness"].notna().sum()} DBs')

else:
    print('WARNING: College stats file not found, using grand mean as prior for all')
    grand_mean = db_summary['raw_stickiness'].mean()
    db_summary['prior_stickiness'] = grand_mean

# Apply shrinkage
db_summary['shrinkage_weight'] = db_summary['n_reps'] / (db_summary['n_reps'] + SHRINKAGE_K)
db_summary['stickiness_bayesian'] = (
    db_summary['shrinkage_weight'] * db_summary['raw_stickiness'] +
    (1 - db_summary['shrinkage_weight']) * db_summary['prior_stickiness']
)

# Rank by Bayesian stickiness
db_summary = db_summary.sort_values('stickiness_bayesian', ascending=False)
db_summary['rank'] = range(1, len(db_summary) + 1)

# ============================================================================
# SAVE LEADERBOARD
# ============================================================================

print('\n' + '-' * 80)
print('Saving leaderboard')
print('-' * 80)

# Reorder columns
leaderboard_cols = [
    'rank', 'db_name', 'n_reps',
    'raw_stickiness', 'stickiness_std', 'stickiness_bayesian',
    'avg_phase', 'avg_reaction', 'avg_recovery',
    'prior_stickiness', 'shrinkage_weight'
]

db_summary = db_summary[leaderboard_cols].copy()
db_summary.to_csv(OUTPUT_LEADERBOARD, index=False)

print(f'Saved leaderboard to {OUTPUT_LEADERBOARD}')

# ============================================================================
# SUMMARY
# ============================================================================

print('\n' + '=' * 80)
print('STICKINESS COMPUTATION SUMMARY')
print('=' * 80)

print(f'\nProcessed {len(rep_scores_df)} reps for {len(db_summary)} DBs')

print(f'\nTop 10 DBs (Bayesian Adjusted):')
print(db_summary[['rank', 'db_name', 'n_reps', 'stickiness_bayesian', 'avg_phase', 'avg_reaction', 'avg_recovery']].head(10).to_string(index=False))

print(f'\nScore Distributions:')
print(f'  Phase:    {db_summary["avg_phase"].mean():.3f} ± {db_summary["avg_phase"].std():.3f}')
print(f'  Reaction: {db_summary["avg_reaction"].mean():.3f} ± {db_summary["avg_reaction"].std():.3f}')
print(f'  Recovery: {db_summary["avg_recovery"].mean():.3f} ± {db_summary["avg_recovery"].std():.3f}')
print(f'  Combined: {db_summary["stickiness_bayesian"].mean():.3f} ± {db_summary["stickiness_bayesian"].std():.3f}')

print(f'\nDBs with 8+ reps: {(db_summary["n_reps"] >= 8).sum()}')
print(f'DBs with 10+ reps: {(db_summary["n_reps"] >= 10).sum()}')

print('\n' + '=' * 80)
print('COMPUTATION COMPLETE')
print('=' * 80)
print(f'\nNext step: Run validate_translation.py')
print(f'  python scripts/validate_translation.py')
