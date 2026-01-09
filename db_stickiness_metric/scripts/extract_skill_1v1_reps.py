"""
Extract Skill 1v1 Reps - Script 1
==================================

Extract individual WR-DB paired reps from 2024 West Practice 3, Session 4
("Bigs INDY / Skill 1 on 1") using activity detection, station clustering,
and Hungarian assignment.

Input:  data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet
Output: outputs/reps_skill_1v1.parquet

Runtime: ~2-3 minutes
Memory:  ~500MB peak
"""

import pyarrow.parquet as pq
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import warnings
import os
import sys

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths (relative to scripts folder)
PARQUET_PATH = '../../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'
OUTPUT_PATH = '../outputs/reps_skill_1v1.parquet'

SESSION_ID = 4  # "Bigs INDY / Skill 1 on 1"

# Activity detection
ACTIVE_SPEED_THRESHOLD = 1.5      # yds/s
MIN_ACTIVE_DURATION = 1.0         # seconds
MERGE_IDLE_GAP = 0.3              # seconds
MIN_POSITION_VARIANCE = 4.0       # yards
MIN_MAX_SPEED = 3.5               # yds/s

# Station clustering
STATION_RADIUS = 12.0             # yards (DBSCAN eps)
MIN_STATION_SAMPLES = 3           # min reps per station

# Pairing constraints
MAX_START_DISTANCE = 8.0          # yards
MAX_AVG_SEPARATION = 12.0         # yards
MIN_OVERLAP_PCT = 0.70            # 70% frame coverage

# Cost function weights
WEIGHT_AVG_SEP = 0.50
WEIGHT_START_SEP = 0.30
WEIGHT_SHADOWING = 0.20

# Confidence thresholds
CONF_HIGH = {'start': 4.0, 'avg': 10.0}
CONF_MED = {'start': 6.0, 'avg': 12.0}

print('=' * 80)
print('EXTRACT SKILL 1v1 REPS - SCRIPT 1')
print('=' * 80)
print(f'\nTarget: Session {SESSION_ID} ("Bigs INDY / Skill 1 on 1")')
print(f'\nConfiguration:')
print(f'  Activity: speed > {ACTIVE_SPEED_THRESHOLD} yds/s for > {MIN_ACTIVE_DURATION}s')
print(f'  Stations: DBSCAN with eps={STATION_RADIUS}y, min_samples={MIN_STATION_SAMPLES}')
print(f'  Pairing: start < {MAX_START_DISTANCE}y, avg < {MAX_AVG_SEPARATION}y')

# ============================================================================
# STEP 1: LOAD SESSION 4 DATA WITH COLUMN PROJECTION
# ============================================================================

print('\n' + '-' * 80)
print('STEP 1: Loading session 4 data with column projection')
print('-' * 80)

# Check if file exists
if not os.path.exists(PARQUET_PATH):
    print(f'ERROR: Parquet file not found at {PARQUET_PATH}')
    print('Please ensure the data file is in the correct location.')
    sys.exit(1)

print(f'Reading from: {PARQUET_PATH}')

# Read with available columns only
print('Reading session 4 data...')

table = pq.read_table(
    PARQUET_PATH,
    columns=['ts', 'zebra_id', 'gsis_id', 'x', 'y', 's', 'a', 'dir', 'session_id', 'entity_type'],
    filters=[('session_id', '=', SESSION_ID)]
)

df = table.to_pandas()
print(f'Loaded {len(df):,} frames from session {SESSION_ID}')

# Use zebra_id as player identifier (unique tracking device ID)
df['player_name'] = df['zebra_id'].astype(str)

# Filter to only WR/DB positions using gsis_id mapping to college stats
print('\nFiltering to WR/DB positions only...')
college_stats_path = '../../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'
if os.path.exists(college_stats_path):
    college_stats = pd.read_csv(college_stats_path)

    # Get valid WR/DB gsis_ids
    wr_db_positions = ['WR', 'TE', 'CB', 'S', 'DB', 'DC', 'DS', 'IB']
    valid_gsis = college_stats[college_stats['position'].isin(wr_db_positions)]['college_gsis_id'].unique()

    # Convert gsis_id in df to numeric for comparison
    df['gsis_id_num'] = pd.to_numeric(df['gsis_id'], errors='coerce')

    # Filter to only valid positions (or keep rows without gsis_id to not lose tracking data)
    before_filter = len(df['player_name'].unique())
    df = df[(df['gsis_id_num'].isin(valid_gsis)) | (df['gsis_id'].isna())].copy()
    after_filter = len(df['player_name'].unique())

    print(f'Filtered from {before_filter} to {after_filter} players (removed QBs, OL, DL, LBs)')
else:
    print('WARNING: College stats not found, skipping position filtering')

# We'll infer WR vs DB from movement patterns later
print('Note: Using zebra_id as player identifier')
print('Position (WR vs DB) will be inferred from activity patterns')

# ============================================================================
# STEP 2: PREPROCESS AND DEDUPLICATE
# ============================================================================

print('\n' + '-' * 80)
print('STEP 2: Preprocessing and deduplication')
print('-' * 80)

# Convert timestamp
df['ts'] = pd.to_datetime(df['ts'])

# Convert timestamp to seconds since start
start_time = df['ts'].min()
df['timestamp'] = (df['ts'] - start_time).dt.total_seconds()

# Deduplicate
df_raw = df.copy()
df = df.sort_values(['timestamp', 'player_name']).copy()
df = df.drop_duplicates(subset=['timestamp', 'player_name'], keep='first')

print(f'After dedup: {len(df):,} rows')
print(f'Removed: {len(df_raw) - len(df):,} duplicates ({100*(len(df_raw)-len(df))/len(df_raw):.1f}%)')

# Calculate speed first (need it for position inference)
if 's' in df.columns:
    df['speed'] = df['s']
else:
    print('Calculating speed from position changes...')
    df = df.sort_values(['player_name', 'timestamp'])
    df['dx'] = df.groupby('player_name')['x'].diff()
    df['dy'] = df.groupby('player_name')['y'].diff()
    df['dt'] = df.groupby('player_name')['timestamp'].diff()
    df['speed'] = np.sqrt(df['dx']**2 + df['dy']**2) / df['dt']
    df['speed'] = df['speed'].fillna(0)

# Infer WR vs DB from activity patterns using fast pandas groupby
print('\nInferring WR vs DB roles from activity patterns...')

# Use groupby aggregations instead of loop (much faster)
activity_df = df.groupby('player_name').agg({
    'speed': ['max', 'mean'],
    'timestamp': 'count'
}).reset_index()

activity_df.columns = ['player_name', 'max_speed', 'avg_speed', 'n_frames']

# Simple heuristic: Top half by max speed = likely WRs, bottom half = likely DBs
activity_df['speed_score'] = activity_df['max_speed'] * 0.7 + activity_df['avg_speed'] * 0.3
activity_df = activity_df.sort_values('speed_score', ascending=False).reset_index(drop=True)

n_players = len(activity_df)
wr_threshold_idx = n_players // 2

activity_df['position_group'] = 'DB'
activity_df.loc[:wr_threshold_idx-1, 'position_group'] = 'WR'
activity_df['position'] = activity_df['position_group']

# Merge back
df = df.merge(activity_df[['player_name', 'position_group', 'position']], on='player_name', how='left')

n_wr = (df['position_group'] == 'WR').sum()
n_db = (df['position_group'] == 'DB').sum()
print(f'Inferred positions: {n_wr / len(df) * 100:.1f}% WR ({activity_df[activity_df["position_group"]=="WR"]["player_name"].nunique()} players), {n_db / len(df) * 100:.1f}% DB ({activity_df[activity_df["position_group"]=="DB"]["player_name"].nunique()} players)')

# Calculate velocity if not already present
if 'vx' not in df.columns:
    df = df.sort_values(['player_name', 'timestamp'])
    df['vx'] = df.groupby('player_name')['x'].diff() / df.groupby('player_name')['timestamp'].diff()
    df['vy'] = df.groupby('player_name')['y'].diff() / df.groupby('player_name')['timestamp'].diff()
    df['vx'] = df['vx'].fillna(0)
    df['vy'] = df['vy'].fillna(0)

# Calculate speed if not present or recalculate for consistency
if 's' not in df.columns or df['s'].isna().any():
    df['speed'] = np.sqrt(df['vx']**2 + df['vy']**2)
else:
    df['speed'] = df['s']

# Identify players
wrs = sorted(df[df['position_group'] == 'WR']['player_name'].unique())
dbs = sorted(df[df['position_group'] == 'DB']['player_name'].unique())

print(f'\nPlayers identified:')
print(f'  WRs: {len(wrs)} players')
print(f'  DBs: {len(dbs)} players')

if len(wrs) == 0 or len(dbs) == 0:
    print('ERROR: No WRs or DBs found in session 4!')
    print('Check position mapping or session_id filter.')
    sys.exit(1)

# ============================================================================
# STEP 3: EXTRACT ACTIVITY BURSTS (WR REPS)
# ============================================================================

print('\n' + '-' * 80)
print('STEP 3: Extracting WR activity bursts')
print('-' * 80)

def extract_activity_bursts(player_df, player_name):
    """Extract activity bursts from player tracking data."""
    bursts = []

    pdf = player_df.sort_values('timestamp').reset_index(drop=True)
    pdf['active'] = pdf['speed'] > ACTIVE_SPEED_THRESHOLD

    # Find transitions
    pdf['active_shift'] = pdf['active'].shift(1, fill_value=False)
    pdf['start_burst'] = (~pdf['active_shift']) & (pdf['active'])
    pdf['end_burst'] = (pdf['active_shift']) & (~pdf['active'])

    # Track burst segments
    burst_id = 0
    in_burst = False
    burst_start_idx = None

    for idx, row in pdf.iterrows():
        if row['start_burst']:
            in_burst = True
            burst_start_idx = idx
        elif row['end_burst'] or (idx == len(pdf) - 1 and in_burst):
            # End of burst
            burst_end_idx = idx - 1 if row['end_burst'] else idx
            burst_segment = pdf.loc[burst_start_idx:burst_end_idx]

            duration = burst_segment['timestamp'].max() - burst_segment['timestamp'].min()

            if duration >= MIN_ACTIVE_DURATION:
                # Check position variance (must actually move)
                x_range = burst_segment['x'].max() - burst_segment['x'].min()
                y_range = burst_segment['y'].max() - burst_segment['y'].min()
                max_speed = burst_segment['speed'].max()

                if (x_range >= MIN_POSITION_VARIANCE or y_range >= MIN_POSITION_VARIANCE) and \
                   max_speed >= MIN_MAX_SPEED:
                    bursts.append({
                        'player': player_name,
                        'burst_id': burst_id,
                        'start_idx': burst_start_idx,
                        'end_idx': burst_end_idx,
                        'start_ts': burst_segment['timestamp'].min(),
                        'end_ts': burst_segment['timestamp'].max(),
                        'duration': duration,
                        'start_x': burst_segment.iloc[0]['x'],
                        'start_y': burst_segment.iloc[0]['y'],
                        'end_x': burst_segment.iloc[-1]['x'],
                        'end_y': burst_segment.iloc[-1]['y'],
                        'max_speed': max_speed,
                        'n_frames': len(burst_segment),
                        'x_range': x_range,
                        'y_range': y_range
                    })
                    burst_id += 1

            in_burst = False

    return bursts

# Extract bursts for all WRs
all_wr_bursts = []
for wr_name in wrs:
    wr_df = df[df['player_name'] == wr_name]
    bursts = extract_activity_bursts(wr_df, wr_name)
    all_wr_bursts.extend(bursts)

df_wr_bursts = pd.DataFrame(all_wr_bursts)

if len(df_wr_bursts) == 0:
    print('ERROR: No WR activity bursts detected!')
    print('Check activity thresholds.')
    sys.exit(1)

print(f'Extracted {len(df_wr_bursts)} WR activity bursts')
print(f'  Duration: {df_wr_bursts["duration"].mean():.2f}s (mean), {df_wr_bursts["duration"].median():.2f}s (median)')
print(f'  Max speed: {df_wr_bursts["max_speed"].mean():.2f} yds/s (mean)')
print(f'  Frames: {df_wr_bursts["n_frames"].mean():.1f} (mean)')

# Merge nearby bursts (< 0.3s gap)
print(f'\nMerging bursts with idle gaps < {MERGE_IDLE_GAP}s...')
df_wr_bursts = df_wr_bursts.sort_values(['player', 'start_ts']).reset_index(drop=True)

merged_bursts = []
i = 0
while i < len(df_wr_bursts):
    current = df_wr_bursts.iloc[i].to_dict()

    # Look ahead for same player
    j = i + 1
    while j < len(df_wr_bursts):
        next_burst = df_wr_bursts.iloc[j]
        if next_burst['player'] != current['player']:
            break

        gap = next_burst['start_ts'] - current['end_ts']
        if gap <= MERGE_IDLE_GAP:
            # Merge
            current['end_ts'] = next_burst['end_ts']
            current['end_x'] = next_burst['end_x']
            current['end_y'] = next_burst['end_y']
            current['duration'] = current['end_ts'] - current['start_ts']
            current['max_speed'] = max(current['max_speed'], next_burst['max_speed'])
            j += 1
        else:
            break

    merged_bursts.append(current)
    i = j

df_wr_reps = pd.DataFrame(merged_bursts)
df_wr_reps = df_wr_reps.reset_index(drop=True)
df_wr_reps['rep_id'] = df_wr_reps.index

print(f'After merging: {len(df_wr_reps)} WR reps')
print(f'  Duration: {df_wr_reps["duration"].mean():.2f}s (mean)')

# ============================================================================
# STEP 4: ASSIGN STATIONS (CLUSTER WR START POSITIONS)
# ============================================================================

print('\n' + '-' * 80)
print('STEP 4: Assigning drill stations via DBSCAN clustering')
print('-' * 80)

# Cluster WR start positions
start_positions = df_wr_reps[['start_x', 'start_y']].values

# Use DBSCAN for station clustering
clustering = DBSCAN(eps=STATION_RADIUS, min_samples=MIN_STATION_SAMPLES).fit(start_positions)
df_wr_reps['station_id'] = clustering.labels_

# Handle noise points (label = -1) by assigning to nearest cluster
noise_mask = df_wr_reps['station_id'] == -1
if noise_mask.sum() > 0:
    print(f'  {noise_mask.sum()} noise points detected, assigning to nearest cluster...')
    valid_stations = df_wr_reps[df_wr_reps['station_id'] >= 0]

    if len(valid_stations) > 0:
        station_centers = valid_stations.groupby('station_id')[['start_x', 'start_y']].mean().values
        noise_positions = df_wr_reps.loc[noise_mask, ['start_x', 'start_y']].values
        distances = cdist(noise_positions, station_centers)
        nearest_stations = distances.argmin(axis=1)
        df_wr_reps.loc[noise_mask, 'station_id'] = nearest_stations

n_stations = df_wr_reps['station_id'].nunique()
print(f'Identified {n_stations} drill stations')

for station_id in sorted(df_wr_reps['station_id'].unique()):
    station_reps = df_wr_reps[df_wr_reps['station_id'] == station_id]
    center_x = station_reps['start_x'].mean()
    center_y = station_reps['start_y'].mean()
    print(f'  Station {station_id}: {len(station_reps)} reps, center ({center_x:.1f}, {center_y:.1f})')

# ============================================================================
# STEP 5: PAIR WR-DB USING HUNGARIAN ASSIGNMENT
# ============================================================================

print('\n' + '-' * 80)
print('STEP 5: Pairing WR-DB using Hungarian assignment')
print('-' * 80)

def compute_pair_cost(wr_rep, db_seg, wr_data, db_data):
    """
    Compute pairing cost between WR rep and DB segment.
    Returns (cost, metrics_dict) or (np.inf, None) if invalid.
    """
    # Handle both dict and namedtuple access
    if hasattr(wr_rep, 'start_ts'):
        wr_start = wr_rep.start_ts
        wr_end = wr_rep.end_ts
    else:
        wr_start = wr_rep['start_ts']
        wr_end = wr_rep['end_ts']

    # Get overlapping time window
    t_start = max(wr_start, db_seg['timestamp'].min())
    t_end = min(wr_end, db_seg['timestamp'].max())

    if t_end <= t_start:
        return np.inf, None

    # Filter to overlap window
    wr_window = wr_data[(wr_data['timestamp'] >= t_start) & (wr_data['timestamp'] <= t_end)]
    db_window = db_data[(db_data['timestamp'] >= t_start) & (db_data['timestamp'] <= t_end)]

    # Merge on timestamp
    merged = pd.merge(
        wr_window[['timestamp', 'x', 'y', 'vx', 'vy']],
        db_window[['timestamp', 'x', 'y', 'vx', 'vy']],
        on='timestamp',
        suffixes=('_wr', '_db')
    )

    if len(merged) == 0:
        return np.inf, None

    # Check overlap percentage
    overlap_pct = len(merged) / len(wr_window)
    if overlap_pct < MIN_OVERLAP_PCT:
        return np.inf, None

    # Calculate separation
    merged['sep'] = np.sqrt((merged['x_wr'] - merged['x_db'])**2 + (merged['y_wr'] - merged['y_db'])**2)

    # Check hard constraints
    d_start = merged.iloc[0]['sep']
    if d_start > MAX_START_DISTANCE:
        return np.inf, None

    avg_sep = merged['sep'].mean()
    if avg_sep > MAX_AVG_SEPARATION:
        return np.inf, None

    # Calculate shadowing score (velocity correlation)
    if len(merged) > 1:
        vx_corr = np.corrcoef(merged['vx_wr'], merged['vx_db'])[0, 1]
        vy_corr = np.corrcoef(merged['vy_wr'], merged['vy_db'])[0, 1]
        shadowing_score = (vx_corr + vy_corr) / 2
        if np.isnan(shadowing_score):
            shadowing_score = 0
    else:
        shadowing_score = 0

    # Compute cost (lower is better)
    cost = (WEIGHT_AVG_SEP * avg_sep +
            WEIGHT_START_SEP * d_start +
            WEIGHT_SHADOWING * (1 - shadowing_score) * 10)

    metrics = {
        'd_start': d_start,
        'avg_sep': avg_sep,
        'd_end': merged.iloc[-1]['sep'],
        'min_sep': merged['sep'].min(),
        'max_sep': merged['sep'].max(),
        'shadowing': shadowing_score,
        'overlap_pct': overlap_pct,
        'n_frames': len(merged)
    }

    return cost, metrics

# Process each station separately
all_matches = []

for station_id in sorted(df_wr_reps['station_id'].unique()):
    station_reps = df_wr_reps[df_wr_reps['station_id'] == station_id]

    print(f'\nStation {station_id}: {len(station_reps)} WR reps')

    # Group reps into time blocks (10 second windows)
    station_reps = station_reps.sort_values('start_ts').reset_index(drop=True)
    time_blocks = []
    current_block = [station_reps.iloc[0]]

    for i in range(1, len(station_reps)):
        rep = station_reps.iloc[i]
        if rep['start_ts'] - current_block[-1]['end_ts'] < 10.0:
            current_block.append(rep)
        else:
            time_blocks.append(current_block)
            current_block = [rep]
    time_blocks.append(current_block)

    print(f'  Split into {len(time_blocks)} time blocks')

    # Process each time block
    for block_idx, block in enumerate(time_blocks):
        block_df = pd.DataFrame(block)
        block_start = block_df['start_ts'].min()
        block_end = block_df['end_ts'].max()

        # Get DB candidates in this station/time window
        station_center_x = station_reps['start_x'].mean()
        station_center_y = station_reps['start_y'].mean()

        # Get all DB data in time window
        db_candidates = []
        for db_name in dbs:
            db_data = df[(df['player_name'] == db_name) &
                        (df['timestamp'] >= block_start - 1) &
                        (df['timestamp'] <= block_end + 1)]

            if len(db_data) < 5:
                continue

            # Check if DB is near station
            db_start_pos = db_data.iloc[0][['x', 'y']].values
            dist_to_station = np.sqrt((db_start_pos[0] - station_center_x)**2 +
                                     (db_start_pos[1] - station_center_y)**2)

            if dist_to_station <= STATION_RADIUS * 1.5:
                db_candidates.append((db_name, db_data))

        if len(db_candidates) == 0:
            continue

        # Build cost matrix
        n_wr = len(block_df)
        n_db = len(db_candidates)
        cost_matrix = np.full((n_wr, n_db), np.inf)
        metrics_matrix = [[None] * n_db for _ in range(n_wr)]

        for i, wr_rep in enumerate(block_df.itertuples()):
            wr_data = df[(df['player_name'] == wr_rep.player) &
                        (df['timestamp'] >= wr_rep.start_ts) &
                        (df['timestamp'] <= wr_rep.end_ts)]

            for j, (db_name, db_data) in enumerate(db_candidates):
                cost, metrics = compute_pair_cost(wr_rep, db_data, wr_data, db_data)
                cost_matrix[i, j] = cost
                metrics_matrix[i][j] = metrics

        # Solve assignment (only if there are valid pairs)
        if not np.all(np.isinf(cost_matrix)):
            try:
                wr_idx, db_idx = linear_sum_assignment(cost_matrix)

                # Record matches (only if cost is finite)
                for i, j in zip(wr_idx, db_idx):
                    if not np.isinf(cost_matrix[i, j]):
                        wr_rep = block_df.iloc[i]
                        db_name = db_candidates[j][0]
                        metrics = metrics_matrix[i][j]

                        match = {
                            'rep_id': wr_rep['rep_id'],
                            'wr_name': wr_rep['player'],
                            'db_name': db_name,
                            'start_ts': wr_rep['start_ts'],
                            'end_ts': wr_rep['end_ts'],
                            'station_id': station_id,
                            'cost': cost_matrix[i, j],
                            **metrics
                        }
                        all_matches.append(match)
            except ValueError:
                # Greedy fallback
                for i in range(n_wr):
                    best_j = None
                    best_cost = np.inf
                    for j in range(n_db):
                        if cost_matrix[i, j] < best_cost:
                            best_cost = cost_matrix[i, j]
                            best_j = j

                    if best_j is not None and not np.isinf(best_cost):
                        wr_rep = block_df.iloc[i]
                        db_name = db_candidates[best_j][0]
                        metrics = metrics_matrix[i][best_j]

                        match = {
                            'rep_id': wr_rep['rep_id'],
                            'wr_name': wr_rep['player'],
                            'db_name': db_name,
                            'start_ts': wr_rep['start_ts'],
                            'end_ts': wr_rep['end_ts'],
                            'station_id': station_id,
                            'cost': best_cost,
                            **metrics
                        }
                        all_matches.append(match)

df_matches = pd.DataFrame(all_matches)
print(f'\n\nFound {len(df_matches)} WR-DB pairs')

if len(df_matches) == 0:
    print('ERROR: No valid WR-DB pairs found!')
    print('Check pairing constraints or station assignments.')
    sys.exit(1)

# ============================================================================
# STEP 6: SCORE CONFIDENCE
# ============================================================================

print('\n' + '-' * 80)
print('STEP 6: Scoring pairing confidence')
print('-' * 80)

def score_confidence(row):
    """Assign confidence level: High, Medium, or Low."""
    if (row['d_start'] < CONF_HIGH['start'] and
        row['avg_sep'] < CONF_HIGH['avg']):
        return 'High'
    elif (row['d_start'] < CONF_MED['start'] and
          row['avg_sep'] < CONF_MED['avg']):
        return 'Medium'
    else:
        return 'Low'

df_matches['confidence'] = df_matches.apply(score_confidence, axis=1)

print(f'\nConfidence distribution:')
for conf_level in ['High', 'Medium', 'Low']:
    count = (df_matches['confidence'] == conf_level).sum()
    pct = 100 * count / len(df_matches)
    print(f'  {conf_level}: {count} reps ({pct:.1f}%)')

# Filter to High + Medium confidence only
df_output = df_matches[df_matches['confidence'].isin(['High', 'Medium'])].copy()
print(f'\nFiltered to {len(df_output)} High/Medium confidence reps')

# ============================================================================
# STEP 7: SAVE RESULTS
# ============================================================================

print('\n' + '-' * 80)
print('STEP 7: Saving results')
print('-' * 80)

# Reorder columns for clarity
output_cols = [
    'rep_id', 'wr_name', 'db_name', 'start_ts', 'end_ts', 'station_id',
    'confidence', 'd_start', 'avg_sep', 'd_end',
    'min_sep', 'max_sep', 'shadowing', 'overlap_pct', 'n_frames', 'cost'
]

df_output = df_output[output_cols].copy()

# Create outputs directory if it doesn't exist
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

df_output.to_parquet(OUTPUT_PATH, index=False)

print(f'\nSaved {len(df_output)} reps to {OUTPUT_PATH}')

# ============================================================================
# STEP 8: SUMMARY STATISTICS
# ============================================================================

print('\n' + '=' * 80)
print('EXTRACTION SUMMARY')
print('=' * 80)

print(f'\nSample Size: {len(df_output)} reps')
print(f'  High confidence: {(df_output["confidence"] == "High").sum()}')
print(f'  Medium confidence: {(df_output["confidence"] == "Medium").sum()}')

print(f'\nUnique Players:')
print(f'  WRs: {df_output["wr_name"].nunique()}')
print(f'  DBs: {df_output["db_name"].nunique()}')

print(f'\nSeparation Metrics:')
print(f'  Start distance: {df_output["d_start"].mean():.2f} ± {df_output["d_start"].std():.2f} yards')
print(f'  Average separation: {df_output["avg_sep"].mean():.2f} ± {df_output["avg_sep"].std():.2f} yards')
print(f'  End distance: {df_output["d_end"].mean():.2f} ± {df_output["d_end"].std():.2f} yards')

print(f'\nShadowing Score:')
print(f'  Mean: {df_output["shadowing"].mean():.3f}')
print(f'  Median: {df_output["shadowing"].median():.3f}')

print(f'\nDBs with Most Reps:')
db_counts = df_output['db_name'].value_counts().head(10)
for db_name, count in db_counts.items():
    print(f'  {db_name}: {count} reps')

print('\n' + '=' * 80)
print('EXTRACTION COMPLETE')
print('=' * 80)
print(f'\nNext step: Run compute_db_stickiness.py')
print(f'  python scripts/compute_db_stickiness.py')
