"""
Diagnose Score Distribution Spikes
===================================

Investigate why reaction scores spike at 0.5 and recovery scores spike at 0 and 0.7

Expected default values in code:
- Reaction: 0.5 when no break detected or insufficient data
- Recovery: 0.7 when no separation growth detected
- Recovery: 0.0 when route ended at peak separation
"""

import pandas as pd
import json

print('=' * 80)
print('DIAGNOSING SCORE DISTRIBUTION SPIKES')
print('=' * 80)

# Load rep scores
rep_scores = pd.read_parquet('../outputs/db_rep_scores.parquet')

print(f'\nTotal reps: {len(rep_scores)}')

# ============================================================================
# REACTION SCORE ANALYSIS
# ============================================================================

print('\n' + '-' * 80)
print('REACTION SCORE ANALYSIS')
print('-' * 80)

# Count exact 0.5 values
exact_05 = (rep_scores['reaction_score'] == 0.5).sum()
print(f'\nReps with reaction_score = 0.5 exactly: {exact_05}/{len(rep_scores)} ({exact_05/len(rep_scores)*100:.1f}%)')

# Analyze metadata
# Expected reasons for 0.5:
# 1. insufficient_data (< 10 frames)
# 2. no_break_detected (angular_vel < 60 deg/s threshold)

# Count reaction scores by value
reaction_counts = rep_scores['reaction_score'].value_counts().sort_index()
print(f'\nMost common reaction scores:')
print(reaction_counts.head(10))

# Distribution
print(f'\nReaction score distribution:')
print(f'  Min:  {rep_scores["reaction_score"].min():.4f}')
print(f'  25%:  {rep_scores["reaction_score"].quantile(0.25):.4f}')
print(f'  50%:  {rep_scores["reaction_score"].quantile(0.50):.4f}')
print(f'  75%:  {rep_scores["reaction_score"].quantile(0.75):.4f}')
print(f'  Max:  {rep_scores["reaction_score"].max():.4f}')
print(f'  Mean: {rep_scores["reaction_score"].mean():.4f}')
print(f'  Std:  {rep_scores["reaction_score"].std():.4f}')

# ============================================================================
# RECOVERY SCORE ANALYSIS
# ============================================================================

print('\n' + '-' * 80)
print('RECOVERY SCORE ANALYSIS')
print('-' * 80)

# Count exact values
exact_00 = (rep_scores['recovery_score'] == 0.0).sum()
exact_07 = (rep_scores['recovery_score'] == 0.7).sum()

print(f'\nReps with recovery_score = 0.0 exactly: {exact_00}/{len(rep_scores)} ({exact_00/len(rep_scores)*100:.1f}%)')
print(f'Reps with recovery_score = 0.7 exactly: {exact_07}/{len(rep_scores)} ({exact_07/len(rep_scores)*100:.1f}%)')

# Expected reasons for specific values:
# 0.7 = no_separation_growth (peak_sep - start_sep < 1.5 yards)
# 0.0 = route_ended_at_peak (no recovery window data)

# Count recovery scores by value
recovery_counts = rep_scores['recovery_score'].value_counts().sort_index()
print(f'\nMost common recovery scores:')
print(recovery_counts.head(15))

# Distribution
print(f'\nRecovery score distribution:')
print(f'  Min:  {rep_scores["recovery_score"].min():.4f}')
print(f'  25%:  {rep_scores["recovery_score"].quantile(0.25):.4f}')
print(f'  50%:  {rep_scores["recovery_score"].quantile(0.50):.4f}')
print(f'  75%:  {rep_scores["recovery_score"].quantile(0.75):.4f}')
print(f'  Max:  {rep_scores["recovery_score"].max():.4f}')
print(f'  Mean: {rep_scores["recovery_score"].mean():.4f}')
print(f'  Std:  {rep_scores["recovery_score"].std():.4f}')

# ============================================================================
# INTERPRETATION
# ============================================================================

print('\n' + '=' * 80)
print('INTERPRETATION')
print('=' * 80)

print('\nREACTION SCORE SPIKE AT 0.5:')
print('  Code assigns 0.5 (neutral) when:')
print('    - Insufficient data (< 10 frames): Line 152')
print('    - No break detected (angular_vel < 60 deg/s): Line 177')
print(f'  > {exact_05} reps ({exact_05/len(rep_scores)*100:.1f}%) hit this default')

if exact_05 / len(rep_scores) > 0.7:
    print('  WARNING: >70% of reps use default score')
    print('    Possible causes:')
    print('      1. Angular velocity threshold (60 deg/s) too high')
    print('      2. Routes in 1v1 drills are mostly straight (no breaks)')
    print('      3. Tracking quality issues missing break points')
else:
    print('  OK: Expected behavior for reps without clear breaks')

print('\nRECOVERY SCORE SPIKE AT 0.7:')
print('  Code assigns 0.7 (good baseline) when:')
print('    - No separation growth (peak - start < 1.5 yards): Line 263')
print(f'  > {exact_07} reps ({exact_07/len(rep_scores)*100:.1f}%) had tight coverage throughout')

if exact_07 / len(rep_scores) > 0.3:
    print('  OK: Expected for 1v1 drills with good DB coverage')
else:
    print('  NOTICE: Less than expected - DBs may be giving up separation')

print('\nRECOVERY SCORE SPIKE AT 0.0:')
print('  Code assigns 0.0 (failure) when:')
print('    - Route ended at peak separation (no recovery data): Line 272')
print(f'  > {exact_00} reps ({exact_00/len(rep_scores)*100:.1f}%) ended without recovery window')

if exact_00 / len(rep_scores) > 0.2:
    print('  WARNING: >20% of routes end abruptly')
    print('    Possible causes:')
    print('      1. Short routes (< 1 second after peak separation)')
    print('      2. Tracking cuts off before route completion')
else:
    print('  OK: Expected for routes where WR beats DB cleanly')

print('\n' + '=' * 80)
print('RECOMMENDATIONS')
print('=' * 80)

if exact_05 / len(rep_scores) > 0.7:
    print('\n1. REACTION SCORE TUNING:')
    print('   - Consider lowering angular velocity threshold from 60 to 45 deg/s')
    print('   - Add alternative break detection (speed changes, cuts)')
    print('   - Visualize sample routes to verify break detection')

if exact_07 / len(rep_scores) > 0.5:
    print('\n2. RECOVERY SCORE TUNING:')
    print('   - Current 1.5 yard threshold may be appropriate for tight coverage')
    print('   - Consider this a positive signal (DBs maintaining tight coverage)')

if exact_00 / len(rep_scores) > 0.3:
    print('\n3. DATA QUALITY:')
    print('   - Investigate why routes end abruptly (tracking cutoff?)')
    print('   - Consider extending recovery window or handling short routes differently')

print('\n' + '=' * 80)
