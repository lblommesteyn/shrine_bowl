"""
Validate Translation - Script 3
================================

Validate stickiness metric:
1. Split-half reliability (internal consistency)
2. Correlation with college stats (construct validity)

Input:  outputs/db_rep_scores.parquet
        outputs/db_player_leaderboard.csv
        data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv
Output: outputs/validation_metrics.json
        outputs/validation_split_half.csv

Runtime: ~30 seconds
Memory:  <100MB
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import json
import os
import sys

print('=' * 80)
print('VALIDATE TRANSLATION - SCRIPT 3')
print('=' * 80)

# ============================================================================
# CONFIGURATION
# ============================================================================

REP_SCORES_PATH = '../outputs/db_rep_scores.parquet'
LEADERBOARD_PATH = '../outputs/db_player_leaderboard.csv'
COLLEGE_STATS_PATH = '../../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'
OUTPUT_METRICS = '../outputs/validation_metrics.json'
OUTPUT_SPLIT_HALF = '../outputs/validation_split_half.csv'

MIN_REPS_SPLIT = 6  # Minimum reps for split-half analysis (lowered from 10 to include more DBs)

# ============================================================================
# LOAD DATA
# ============================================================================

print('\n' + '-' * 80)
print('Loading data')
print('-' * 80)

if not os.path.exists(REP_SCORES_PATH):
    print(f'ERROR: Rep scores not found at {REP_SCORES_PATH}')
    print('Please run compute_db_stickiness.py first.')
    sys.exit(1)

rep_scores = pd.read_parquet(REP_SCORES_PATH)
leaderboard = pd.read_csv(LEADERBOARD_PATH)

print(f'Loaded {len(rep_scores)} rep scores')
print(f'Loaded {len(leaderboard)} DB leaderboard entries')

# ============================================================================
# VALIDATION 1: SPLIT-HALF RELIABILITY
# ============================================================================

print('\n' + '-' * 80)
print('Computing split-half reliability')
print('-' * 80)

# Filter to DBs with sufficient reps
db_counts = rep_scores['db_name'].value_counts()
qualified_dbs = db_counts[db_counts >= MIN_REPS_SPLIT].index

print(f'DBs with {MIN_REPS_SPLIT}+ reps: {len(qualified_dbs)}')

if len(qualified_dbs) < 3:
    print(f'WARNING: Only {len(qualified_dbs)} DBs with {MIN_REPS_SPLIT}+ reps')
    print('Split-half reliability may be unreliable. Consider lowering MIN_REPS_SPLIT.')

split_half_data = []

np.random.seed(42)  # Reproducible

for db_name in qualified_dbs:
    db_reps = rep_scores[rep_scores['db_name'] == db_name].copy()

    # Randomly split into two halves
    db_reps['half'] = np.random.choice([1, 2], size=len(db_reps))

    half1 = db_reps[db_reps['half'] == 1]
    half2 = db_reps[db_reps['half'] == 2]

    if len(half1) == 0 or len(half2) == 0:
        continue

    half1_stickiness = half1['stickiness'].mean()
    half2_stickiness = half2['stickiness'].mean()

    half1_phase = half1['phase_score'].mean()
    half2_phase = half2['phase_score'].mean()

    half1_reaction = half1['reaction_score'].mean()
    half2_reaction = half2['reaction_score'].mean()

    half1_recovery = half1['recovery_score'].mean()
    half2_recovery = half2['recovery_score'].mean()

    split_half_data.append({
        'db_name': db_name,
        'n_reps': len(db_reps),
        'half1_stickiness': half1_stickiness,
        'half2_stickiness': half2_stickiness,
        'half1_phase': half1_phase,
        'half2_phase': half2_phase,
        'half1_reaction': half1_reaction,
        'half2_reaction': half2_reaction,
        'half1_recovery': half1_recovery,
        'half2_recovery': half2_recovery
    })

split_df = pd.DataFrame(split_half_data)

if len(split_df) == 0:
    print('ERROR: No DBs qualified for split-half analysis')
    r_split = 0.0
    p_split = 1.0
else:
    # Correlation for overall stickiness
    r_split, p_split = pearsonr(split_df['half1_stickiness'], split_df['half2_stickiness'])

    # Correlations for sub-scores
    r_phase, p_phase = pearsonr(split_df['half1_phase'], split_df['half2_phase'])
    r_reaction, p_reaction = pearsonr(split_df['half1_reaction'], split_df['half2_reaction'])
    r_recovery, p_recovery = pearsonr(split_df['half1_recovery'], split_df['half2_recovery'])

    print(f'\nSplit-Half Reliability (n={len(split_df)} DBs):')
    print(f'  Overall Stickiness: r = {r_split:.3f}, p = {p_split:.4f}')
    print(f'  Phase Score:        r = {r_phase:.3f}, p = {p_phase:.4f}')
    print(f'  Reaction Score:     r = {r_reaction:.3f}, p = {p_reaction:.4f}')
    print(f'  Recovery Score:     r = {r_recovery:.3f}, p = {p_recovery:.4f}')

    # Spearman-Brown prophecy formula for full reliability estimate
    # r_full = 2 * r_half / (1 + r_half)
    r_full = 2 * r_split / (1 + r_split) if r_split > -1 else 0
    print(f'\nSpearman-Brown corrected reliability: {r_full:.3f}')

    # Save split-half data
    split_df.to_csv(OUTPUT_SPLIT_HALF, index=False)
    print(f'\nSaved split-half data to {OUTPUT_SPLIT_HALF}')

# ============================================================================
# VALIDATION 2: COLLEGE STATS CORRELATION
# ============================================================================

print('\n' + '-' * 80)
print('Computing correlation with college stats')
print('-' * 80)

if not os.path.exists(COLLEGE_STATS_PATH):
    print(f'WARNING: College stats not found at {COLLEGE_STATS_PATH}')
    print('Skipping college stats validation.')
    r_pbu, p_pbu = 0.0, 1.0
    r_int, p_int = 0.0, 1.0
    r_tackles, p_tackles = 0.0, 1.0
    validation_df = pd.DataFrame()

else:
    # Load parquet to get gsis_id mapping for each DB
    import pyarrow.parquet as pq

    PARQUET_PATH = '../../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'
    SESSION_ID = 4

    print('Loading gsis_id mapping from parquet...')
    table = pq.read_table(
        PARQUET_PATH,
        columns=['zebra_id', 'gsis_id'],
        filters=[('session_id', '=', SESSION_ID)]
    )
    gsis_mapping = table.to_pandas()
    gsis_mapping['zebra_id'] = gsis_mapping['zebra_id'].astype(str)
    gsis_mapping = gsis_mapping.drop_duplicates(subset=['zebra_id']).dropna(subset=['gsis_id'])

    # Ensure db_name in leaderboard is also string
    leaderboard['db_name'] = leaderboard['db_name'].astype(str)

    # Add gsis_id to leaderboard
    leaderboard_with_gsis = leaderboard.merge(
        gsis_mapping,
        left_on='db_name',
        right_on='zebra_id',
        how='left'
    )

    print(f'Matched {leaderboard_with_gsis["gsis_id"].notna().sum()}/{len(leaderboard)} DBs with gsis_id')

    # Load and aggregate college stats
    college_stats = pd.read_csv(COLLEGE_STATS_PATH)

    # Filter to DBs and aggregate
    db_college = college_stats[
        college_stats['position'].isin(['DC', 'DS', 'IB', 'CB', 'S', 'DB'])
    ].copy()

    db_college_agg = db_college.groupby('college_gsis_id').agg({
        'defense_pass_breakups': 'sum',
        'defense_interceptions': 'sum',
        'defense_total_tackles': 'sum',
        'defense_tackles_for_loss': 'sum'
    }).reset_index()

    # Convert college_gsis_id to string to match gsis_id type
    db_college_agg['college_gsis_id'] = db_college_agg['college_gsis_id'].astype(str)

    # Also convert gsis_id in leaderboard to string (in case it's not already)
    leaderboard_with_gsis['gsis_id'] = leaderboard_with_gsis['gsis_id'].astype(str)

    # Merge with leaderboard using gsis_id
    validation_df = leaderboard_with_gsis.merge(
        db_college_agg,
        left_on='gsis_id',
        right_on='college_gsis_id',
        how='inner'
    )

    print(f'Matched {len(validation_df)} DBs with college stats')

    if len(validation_df) < 3:
        print('WARNING: Insufficient matches for correlation analysis')
        r_pbu, p_pbu = 0.0, 1.0
        r_int, p_int = 0.0, 1.0
        r_tackles, p_tackles = 0.0, 1.0
        r_tfl, p_tfl = 0.0, 1.0

    else:
        # Correlations
        r_pbu, p_pbu = pearsonr(
            validation_df['stickiness_bayesian'],
            validation_df['defense_pass_breakups']
        )

        r_int, p_int = pearsonr(
            validation_df['stickiness_bayesian'],
            validation_df['defense_interceptions']
        )

        r_tackles, p_tackles = pearsonr(
            validation_df['stickiness_bayesian'],
            validation_df['defense_total_tackles']
        )

        r_tfl, p_tfl = pearsonr(
            validation_df['stickiness_bayesian'],
            validation_df['defense_tackles_for_loss']
        )

        print(f'\nCollege Stats Correlations (n={len(validation_df)}):')
        print(f'  Pass Breakups:  r = {r_pbu:.3f}, p = {p_pbu:.4f}')
        print(f'  Interceptions:  r = {r_int:.3f}, p = {p_int:.4f}')
        print(f'  Total Tackles:  r = {r_tackles:.3f}, p = {p_tackles:.4f}')
        print(f'  Tackles for Loss: r = {r_tfl:.3f}, p = {p_tfl:.4f}')

        print(f'\nInterpretation:')
        print(f'  - Positive correlation with PBUs/INTs = good (coverage skills)')
        print(f'  - Negative correlation with tackles = good (less targeted)')

# ============================================================================
# VALIDATION 3: SUB-SCORE INDEPENDENCE
# ============================================================================

print('\n' + '-' * 80)
print('Checking sub-score independence')
print('-' * 80)

# Correlation matrix of sub-scores
phase_reaction_corr = leaderboard[['avg_phase', 'avg_reaction']].corr().iloc[0, 1]
phase_recovery_corr = leaderboard[['avg_phase', 'avg_recovery']].corr().iloc[0, 1]
reaction_recovery_corr = leaderboard[['avg_reaction', 'avg_recovery']].corr().iloc[0, 1]

print(f'\nSub-Score Correlations:')
print(f'  Phase-Reaction:   r = {phase_reaction_corr:.3f}')
print(f'  Phase-Recovery:   r = {phase_recovery_corr:.3f}')
print(f'  Reaction-Recovery: r = {reaction_recovery_corr:.3f}')

print(f'\nInterpretation:')
print(f'  - Low correlations (r < 0.5) suggest independent dimensions')
print(f'  - High correlations (r > 0.7) suggest redundancy')

# ============================================================================
# SAVE VALIDATION METRICS
# ============================================================================

print('\n' + '-' * 80)
print('Saving validation metrics')
print('-' * 80)

validation_results = {
    'split_half_reliability': {
        'correlation': float(r_split) if not np.isnan(r_split) else 0.0,
        'p_value': float(p_split) if not np.isnan(p_split) else 1.0,
        'n_dbs': int(len(split_df)),
        'min_reps': int(MIN_REPS_SPLIT),
        'spearman_brown_corrected': float(r_full) if len(split_df) > 0 else 0.0
    },
    'college_production_correlation': {
        'pbu_correlation': float(r_pbu) if not np.isnan(r_pbu) else 0.0,
        'pbu_p_value': float(p_pbu) if not np.isnan(p_pbu) else 1.0,
        'int_correlation': float(r_int) if not np.isnan(r_int) else 0.0,
        'int_p_value': float(p_int) if not np.isnan(p_int) else 1.0,
        'tackles_correlation': float(r_tackles) if not np.isnan(r_tackles) else 0.0,
        'tackles_p_value': float(p_tackles) if not np.isnan(p_tackles) else 1.0,
        'n_dbs': int(len(validation_df))
    },
    'subscores_independence': {
        'phase_reaction_corr': float(phase_reaction_corr),
        'phase_recovery_corr': float(phase_recovery_corr),
        'reaction_recovery_corr': float(reaction_recovery_corr)
    },
    'sample_size': {
        'total_reps': int(len(rep_scores)),
        'total_dbs': int(len(leaderboard)),
        'dbs_with_10plus_reps': int((leaderboard['n_reps'] >= 10).sum()),
        'dbs_with_8plus_reps': int((leaderboard['n_reps'] >= 8).sum())
    }
}

os.makedirs(os.path.dirname(OUTPUT_METRICS), exist_ok=True)
with open(OUTPUT_METRICS, 'w') as f:
    json.dump(validation_results, f, indent=2)

print(f'Saved validation metrics to {OUTPUT_METRICS}')

# ============================================================================
# SUMMARY
# ============================================================================

print('\n' + '=' * 80)
print('VALIDATION SUMMARY')
print('=' * 80)

print(f'\n1. SPLIT-HALF RELIABILITY')
print(f'   Correlation: r = {r_split:.3f} (p = {p_split:.4f})')
if r_split > 0.7:
    print(f'   ✓ EXCELLENT - Metric is highly reliable')
elif r_split > 0.5:
    print(f'   ✓ GOOD - Metric shows moderate reliability')
elif r_split > 0.3:
    print(f'   ~ FAIR - Metric shows some reliability')
else:
    print(f'   ✗ POOR - Metric may be unreliable')

print(f'\n2. COLLEGE STATS VALIDITY')
print(f'   PBU correlation: r = {r_pbu:.3f} (p = {p_pbu:.4f})')
print(f'   INT correlation: r = {r_int:.3f} (p = {p_int:.4f})')
if r_pbu > 0.3 or r_int > 0.3:
    print(f'   ✓ Positive correlation with coverage stats')
else:
    print(f'   ~ Weak correlation with college stats')

print(f'\n3. SUB-SCORE INDEPENDENCE')
max_corr = max(abs(phase_reaction_corr), abs(phase_recovery_corr), abs(reaction_recovery_corr))
if max_corr < 0.5:
    print(f'   ✓ Sub-scores are independent (max r = {max_corr:.3f})')
elif max_corr < 0.7:
    print(f'   ~ Sub-scores show moderate correlation (max r = {max_corr:.3f})')
else:
    print(f'   ✗ Sub-scores may be redundant (max r = {max_corr:.3f})')

print(f'\n4. SAMPLE SIZE')
print(f'   Total reps: {len(rep_scores)}')
print(f'   Total DBs: {len(leaderboard)}')
print(f'   DBs with 10+ reps: {(leaderboard["n_reps"] >= 10).sum()}')
if len(rep_scores) >= 150:
    print(f'   ✓ Good sample size')
elif len(rep_scores) >= 100:
    print(f'   ~ Adequate sample size')
else:
    print(f'   ✗ Small sample size - results may be unstable')

print('\n' + '=' * 80)
print('VALIDATION COMPLETE')
print('=' * 80)
print(f'\nNext step: Run generate_deck_figures.py')
print(f'  python scripts/generate_deck_figures.py')
