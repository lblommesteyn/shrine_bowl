# MAN COVERAGE STICKINESS METRIC - IMPLEMENTATION PLAN

**Competition**: Shrine Bowl × SūmerSports Analytics Competition
**Objective**: Build an objective "Man Coverage Stickiness" metric for defensive backs using practice tracking data
**Primary Drill**: 2024 West Practice 3, Session 4 ("Bigs INDY / Skill 1 on 1")
**Date**: 2026-01-04

---

## EXECUTIVE SUMMARY

This plan designs a "Man Coverage Stickiness" metric for defensive backs using the **"Bigs INDY / Skill 1 on 1"** drill from 2024_West_Practice_3.parquet. The metric measures how well DBs maintain tight coverage throughout a route using three sub-scores:

1. **Phase Score (45%)**: Maintaining proximity and leverage consistency
2. **Reaction Score (30%)**: Responding quickly to WR route breaks
3. **Recovery Score (25%)**: Closing separation gaps with speed

Results will be stabilized using **Bayesian shrinkage** with college stats as priors, validated via split-half reliability, and presented in a **10-slide deck**.

**Expected Output**: 150-250 reps, 10-15 DBs with 8+ reps each, comprehensive validation metrics.

---

## A) REP SEGMENTATION APPROACH

### Algorithm: Multi-Station Concurrent Rep Extraction

```
INPUT: 2024_West_Practice_3.parquet (session_id == 4, ~1.2M rows estimated)
OUTPUT: Individual WR-DB paired reps with timestamps and confidence scores

STEP 1: Load and Filter (Memory-Safe)
  - Use pyarrow.parquet.read_table() with column projection
  - Columns: ['ts', 'college_gsis_id', 'x', 'y', 's', 'a', 'dir', 'o',
              'session_id', 'entity_type', 'player_name', 'position']
  - Filter: session_id == 4, entity_type == 'player'
  - Convert to pandas ONLY after filtering (~40K rows expected)

STEP 2: Position Classification
  - WRs: position IN ['WR', 'TE', 'RB']
  - DBs: position IN ['DC', 'DS', 'IB', 'CB', 'S', 'DB']
  - Deduplicate on (timestamp, player_name)

STEP 3: Activity Burst Detection (Per WR)
  For each WR player:
    - Sort by timestamp
    - Mark frames as "active" where speed > 1.5 yds/s
    - Identify burst start/end using state transitions
    - Filter bursts:
      * Duration >= 1.0 seconds (10 frames @ 10Hz)
      * Position variance >= 4.0 yards (must actually move)
      * Max speed >= 3.5 yds/s (meaningful route)
    - Merge bursts separated by < 0.3s idle gap

STEP 4: Station Clustering (Spatial)
  - Extract start positions (x, y) from all WR bursts
  - DBSCAN clustering:
    * eps = 12.0 yards (station radius)
    * min_samples = 3 reps
  - Assign station_id to each burst
  - Handle noise points: assign to nearest cluster center
  - Expected: 3-6 concurrent stations

STEP 5: WR-DB Pairing (Hungarian Assignment within Time Windows)
  For each station:
    For each time_block (10-second windows of concurrent reps):

      # Get candidate DBs
      - Filter DBs whose tracking overlaps with time_block
      - Spatial gate: DB must be within 20 yards of station center at start

      # Build cost matrix
      For each WR_rep in time_block:
        For each DB_candidate:
          - Merge WR and DB trajectories on timestamp (tolerance = 0.1s)
          - Calculate separation at each frame
          - Check constraints:
            * Overlap: DB frames must cover >= 70% of WR route
            * Start distance: <= 8.0 yards
            * Average separation: <= 12.0 yards
          - Compute velocity correlation (shadowing score)
          - Compute cost:
            cost = 0.50 * avg_sep + 0.30 * start_sep + 0.20 * (1 - vel_corr) * 10
          - Store cost[i, j] = cost (or inf if constraints violated)

      # Solve assignment
      - Use scipy.optimize.linear_sum_assignment(cost_matrix)
      - Record valid matches (cost < inf)

STEP 6: Confidence Scoring
  For each matched rep:
    - High confidence: start_sep < 4y AND avg_sep < 10y
    - Medium confidence: start_sep < 6y AND avg_sep < 12y
    - Low confidence: otherwise
    - Filter: Keep only High + Medium for analysis
```

### Key Parameters

```python
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
```

### Expected Output
- **150-250 reps** (based on session duration and drill intensity)
- **10-15 DBs** with 8+ reps each
- **80%+ High/Medium confidence** pairing

---

## B) STICKINESS SUB-SCORE FORMULAS

### 1. Phase Score (Proximity Maintenance)

**Definition**: Percentage of route where DB maintains tight coverage with bonus for leverage consistency.

**Formula**:
```
phase_score = (tight_pct × 1.0) + (acceptable_pct - tight_pct) × 0.5 + leverage_bonus
leverage_bonus = 0.10 × max(0, 1 - angular_std / π)
```

**Constants**:
- `PHASE_TIGHT_THRESHOLD = 2.0` yards - "tight" coverage
- `PHASE_ACCEPTABLE_THRESHOLD = 3.5` yards - "acceptable" coverage
- `LEVERAGE_CONSISTENCY_BONUS = 0.10` - max +10% for consistent positioning

**Implementation**:
```python
def compute_phase_score(wr_traj, db_traj):
    # Merge trajectories on timestamp (tolerance 0.1s)
    merged = pd.merge_asof(wr_traj, db_traj, on='timestamp',
                          suffixes=('_wr', '_db'), direction='nearest',
                          tolerance=0.1)

    # Calculate separation
    merged['separation'] = np.sqrt(
        (merged['x_wr'] - merged['x_db'])**2 +
        (merged['y_wr'] - merged['y_db'])**2
    )

    # Proximity score
    n_tight = (merged['separation'] <= 2.0).sum()
    n_acceptable = (merged['separation'] <= 3.5).sum()
    n_total = len(merged)

    base_score = (n_tight / n_total) + ((n_acceptable - n_tight) / n_total) * 0.5

    # Leverage consistency (angular variance of DB position relative to WR)
    merged['dx'] = merged['x_db'] - merged['x_wr']
    merged['dy'] = merged['y_db'] - merged['y_wr']
    merged['angle'] = np.arctan2(merged['dy'], merged['dx'])

    angle_std = merged['angle'].std()
    leverage_bonus = 0.10 * max(0, 1 - angle_std / np.pi)

    phase_score = min(1.1, base_score + leverage_bonus)

    return phase_score, {
        'avg_separation': merged['separation'].mean(),
        'tight_pct': n_tight / n_total,
        'acceptable_pct': n_acceptable / n_total,
        'leverage_consistency': leverage_bonus
    }
```

---

### 2. Reaction Score (Break Response)

**Definition**: DB's ability to react to WR direction changes (minimize response latency and flip severity).

**Formula**:
```
latency_score = max(0, 1 - reaction_latency / 0.5)
flip_score = max(0, 1 - db_dir_change / 120°)
reaction_score = 0.6 × latency_score + 0.4 × flip_score
```

**Constants**:
- `MAX_REACTION_LATENCY = 0.5` seconds
- `PANIC_FLIP_THRESHOLD = 120` degrees
- `ANGULAR_VEL_BREAK_THRESHOLD = 60` deg/s

**Implementation**:
```python
def compute_reaction_score(wr_traj, db_traj):
    # Detect WR breaks using angular velocity
    wr_traj = wr_traj.copy()
    wr_traj['angular_vel'] = wr_traj['dir'].diff() / wr_traj['timestamp'].diff()
    wr_traj['angular_vel'] = wr_traj['angular_vel'].abs()

    # Find break point in middle 60% of route (avoid start/end noise)
    route_duration = wr_traj['timestamp'].max() - wr_traj['timestamp'].min()
    search_start = wr_traj['timestamp'].min() + route_duration * 0.2
    search_end = wr_traj['timestamp'].max() - route_duration * 0.2

    search_window = wr_traj[
        (wr_traj['timestamp'] >= search_start) &
        (wr_traj['timestamp'] <= search_end) &
        (wr_traj['s'] > 2.5)  # Must be moving
    ]

    if len(search_window) == 0 or search_window['angular_vel'].max() < 60:
        return 0.5, {'no_break_detected': True}  # Neutral score

    break_idx = search_window['angular_vel'].idxmax()
    break_ts = wr_traj.loc[break_idx, 'timestamp']

    # Find DB's reaction
    db_post_break = db_traj[db_traj['timestamp'] >= break_ts].copy()
    db_post_break['angular_vel'] = db_post_break['dir'].diff() / db_post_break['timestamp'].diff()
    db_post_break['angular_vel'] = db_post_break['angular_vel'].abs()

    db_reactions = db_post_break[db_post_break['angular_vel'] > 30]

    if len(db_reactions) == 0:
        return 0.0, {'no_reaction': True}

    reaction_ts = db_reactions['timestamp'].min()
    reaction_latency = reaction_ts - break_ts

    # Direction change severity
    reaction_idx = db_reactions['timestamp'].idxmin()
    db_dir_change = abs(db_post_break.loc[reaction_idx, 'dir'] -
                       db_traj[db_traj['timestamp'] < break_ts].iloc[-1]['dir'])
    db_dir_change = min(db_dir_change, 360 - db_dir_change)

    # Score components
    latency_score = max(0, 1 - reaction_latency / 0.5)
    flip_score = max(0, 1 - db_dir_change / 120)

    reaction_score = 0.6 * latency_score + 0.4 * flip_score

    return reaction_score, {
        'break_time': break_ts,
        'reaction_latency': reaction_latency,
        'db_dir_change': db_dir_change,
        'latency_score': latency_score,
        'flip_score': flip_score
    }
```

---

### 3. Recovery Score (Closing Speed)

**Definition**: DB's ability to close separation gaps after WR creates space.

**Formula**:
```
recovery_pct = max(0, closed_gap / separation_growth)
speed_score = min(1.0, closing_speed / 4.0)
recovery_score = 0.7 × recovery_pct + 0.3 × speed_score
```

**Constants**:
- `SEPARATION_GROWTH_THRESHOLD = 1.5` yards
- `RECOVERY_WINDOW = 1.0` seconds

**Implementation**:
```python
def compute_recovery_score(wr_traj, db_traj):
    # Merge trajectories
    merged = pd.merge_asof(wr_traj, db_traj, on='timestamp',
                          suffixes=('_wr', '_db'), direction='nearest',
                          tolerance=0.1)

    merged['separation'] = np.sqrt(
        (merged['x_wr'] - merged['x_db'])**2 +
        (merged['y_wr'] - merged['y_db'])**2
    )

    # Find peak separation
    peak_idx = merged['separation'].idxmax()
    peak_sep = merged.loc[peak_idx, 'separation']
    peak_ts = merged.loc[peak_idx, 'timestamp']
    start_sep = merged.iloc[0]['separation']

    if peak_sep - start_sep < 1.5:
        return 0.7, {'no_separation_growth': True}  # Good baseline

    # Recovery window: 1 second after peak
    recovery_data = merged[
        (merged['timestamp'] > peak_ts) &
        (merged['timestamp'] <= peak_ts + 1.0)
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

    return recovery_score, {
        'peak_separation': peak_sep,
        'final_separation': final_sep,
        'closed_gap': closed_gap,
        'closing_speed': closing_speed,
        'recovery_pct': recovery_pct
    }
```

---

### 4. Combined Stickiness Score

**Formula**:
```
stickiness = 0.45 × phase + 0.30 × reaction + 0.25 × recovery
```

**Weights Justification**:
- **Phase (45%)**: Most important - staying in phase is foundation of man coverage
- **Reaction (30%)**: Critical for preventing WR from creating separation on breaks
- **Recovery (25%)**: Important but less frequent (only matters when separation grows)

---

## C) BAYESIAN SHRINKAGE (JAMES-STEIN ESTIMATOR)

### Formula

```
λ = n / (n + k)
stickiness_bayesian = λ × raw_stickiness + (1 - λ) × prior_stickiness

where:
  k = 15 (shrinkage constant - equivalent to "15 reps of prior confidence")
  prior_stickiness = grand_mean + 0.10 × college_production_score
```

### College Prior Construction

```python
# Normalize college defensive stats (z-scores)
college_production_score = (
    0.40 × PBU_z +           # Pass breakups (most direct coverage indicator)
    0.35 × INT_z +           # Interceptions (ball skills + coverage)
    0.15 × TFL_z +           # Tackles for loss (aggressiveness)
    -0.10 × Tackles_z        # Fewer tackles = less targeted (good coverage)
)

# Map to prior stickiness around grand mean
prior_stickiness = grand_mean + 0.10 × college_production_score
prior_stickiness = clip(prior_stickiness, 0, 1.0)
```

### Implementation

```python
def apply_bayesian_shrinkage(db_summary, college_stats_df):
    # Build college priors
    db_college = college_stats_df[
        college_stats_df['position'].isin(['DC', 'DS', 'IB', 'CB', 'S', 'DB'])
    ].groupby('college_gsis_id').agg({
        'defense_total_tackles': 'sum',
        'defense_pass_breakups': 'sum',
        'defense_interceptions': 'sum',
        'defense_tackles_for_loss': 'sum'
    }).reset_index()

    # Z-score normalization
    for col in ['defense_total_tackles', 'defense_pass_breakups',
                'defense_interceptions', 'defense_tackles_for_loss']:
        mean = db_college[col].mean()
        std = db_college[col].std()
        if std > 0:
            db_college[f'{col}_z'] = (db_college[col] - mean) / std
        else:
            db_college[f'{col}_z'] = 0

    # Compute college production score
    db_college['college_prior'] = (
        0.40 * db_college['defense_pass_breakups_z'] +
        0.35 * db_college['defense_interceptions_z'] +
        0.15 * db_college['defense_tackles_for_loss_z'] -
        0.10 * db_college['defense_total_tackles_z']
    )

    # Map to prior stickiness
    grand_mean = db_summary['raw_stickiness'].mean()
    prior_std = 0.10

    db_college['prior_stickiness'] = (
        grand_mean + prior_std * db_college['college_prior']
    ).clip(0, 1.0)

    # Merge and apply shrinkage
    db_summary = db_summary.merge(
        db_college[['college_gsis_id', 'prior_stickiness']],
        left_on='gsis_id', right_on='college_gsis_id', how='left'
    )
    db_summary['prior_stickiness'] = db_summary['prior_stickiness'].fillna(grand_mean)

    SHRINKAGE_K = 15
    db_summary['shrinkage_weight'] = db_summary['n_reps'] / (db_summary['n_reps'] + SHRINKAGE_K)
    db_summary['stickiness_bayesian'] = (
        db_summary['shrinkage_weight'] * db_summary['raw_stickiness'] +
        (1 - db_summary['shrinkage_weight']) * db_summary['prior_stickiness']
    )

    return db_summary
```

---

## D) 10-SLIDE DECK STRUCTURE

### Slide 1: Title
- **Title**: "Man Coverage Stickiness: Quantifying DB Route Shadowing Ability"
- **Subtitle**: "Analysis of 200+ 1v1 Reps from 2024 Shrine Bowl Practice"

### Slide 2: Methodology Overview
- **Title**: "The Stickiness Framework: Three Dimensions of Coverage"
- **Figure**: `methodology_stickiness_framework.png`
- Breakdown: Phase 45%, Reaction 30%, Recovery 25%

### Slide 3: Rep Segmentation Process
- **Title**: "Data Pipeline: From 37M Frames to 200 High-Confidence Reps"
- **Figure**: `methodology_rep_extraction_flow.png`
- Flowchart showing activity detection → clustering → pairing

### Slide 4: Phase Score Deep Dive
- **Title**: "Phase Score: Maintaining Proximity Throughout the Route"
- **Figure**: `methodology_phase_score_example.png`
- Example rep with separation heatmap over time

### Slide 5: Reaction + Recovery Scores
- **Title**: "Dynamic Response: Reacting to Breaks and Closing Gaps"
- **Figure**: `methodology_reaction_recovery_comparison.png`
- Side-by-side: good vs poor reaction/recovery

### Slide 6: Overall Leaderboard
- **Title**: "Stickiness Leaderboard: Top 10 DBs (Bayesian Adjusted)"
- **Figure**: `leaderboard_overall_stickiness.png`
- Horizontal bars with confidence intervals

### Slide 7: Sub-Score Leaderboards
- **Title**: "Specialists: Who Excels at Each Component?"
- **Figure**: `leaderboard_subscores_comparison.png`
- Three mini-leaderboards (Phase/Reaction/Recovery top 5)

### Slide 8: Split-Half Reliability
- **Title**: "Validation: Is Stickiness Stable Across Reps?"
- **Figure**: `validation_split_half_reliability.png`
- Scatter plot with correlation r = 0.65-0.75

### Slide 9: 1v1 → Team Translation
- **Title**: "Does Drill Performance Predict Team Success?"
- **Figure**: `validation_drill_to_team_translation.png`
- Correlation with college stats or team drill metrics

### Slide 10: Insights & Applications
- **Title**: "Actionable Insights: What Stickiness Tells Us"
- **Figure**: `insights_stickiness_applications.png`
- Key findings + applications (draft evaluation, coaching)

---

## E) IMPLEMENTATION SCRIPTS

### Directory Structure

```
ss_sbc/
├── scripts/
│   ├── extract_skill_1v1_reps.py
│   ├── compute_db_stickiness.py
│   ├── validate_translation.py
│   └── generate_deck_figures.py
├── outputs/
│   ├── reps_skill_1v1.parquet
│   ├── db_rep_scores.parquet
│   ├── db_player_leaderboard.csv
│   ├── validation_metrics.json
│   └── validation_split_half.csv
└── figures/
    ├── methodology_*.png
    ├── leaderboard_*.png
    ├── validation_*.png
    └── insights_*.png
```

### Script 1: extract_skill_1v1_reps.py

**Purpose**: Extract and pair WR-DB reps from session 4
**Input**: 2024_West_Practice_3.parquet (37.5M rows)
**Output**: outputs/reps_skill_1v1.parquet (~200 rows)
**Runtime**: 2-3 minutes
**Memory**: ~500MB peak

**Key Steps**:
1. Load session_id==4 with column projection (pyarrow)
2. Deduplicate tracking data
3. Detect WR activity bursts (speed > 1.5 yds/s, duration > 1s)
4. Cluster stations with DBSCAN (eps=12y)
5. Pair WR-DB with Hungarian assignment
6. Score confidence (High/Med/Low)
7. Save matched reps to parquet

**Output Schema**:
```
rep_id, wr_gsis_id, db_gsis_id, wr_name, db_name,
start_ts, end_ts, station_id, confidence,
avg_separation, start_separation, overlap_pct
```

### Script 2: compute_db_stickiness.py

**Purpose**: Compute all stickiness sub-scores for each rep
**Input**: outputs/reps_skill_1v1.parquet
**Output**:
- outputs/db_rep_scores.parquet (rep-level)
- outputs/db_player_leaderboard.csv (player-level)
**Runtime**: 3-5 minutes
**Memory**: ~1GB peak

**Key Steps**:
1. For each rep, reload WR/DB trajectories from parquet
2. Compute phase_score (proximity + leverage)
3. Compute reaction_score (break response)
4. Compute recovery_score (closing speed)
5. Combine: 0.45×phase + 0.30×reaction + 0.25×recovery
6. Aggregate by DB (mean, std, count)
7. Apply Bayesian shrinkage with college priors
8. Rank and save leaderboard

**Output Schema (rep-level)**:
```
rep_id, db_gsis_id, db_name,
phase_score, reaction_score, recovery_score, stickiness,
avg_separation, tight_pct, leverage_consistency,
break_time, reaction_latency, db_dir_change,
peak_separation, closing_speed, recovery_pct
```

**Output Schema (player-level)**:
```
rank, db_name, gsis_id, n_reps,
raw_stickiness, stickiness_std, stickiness_bayesian,
avg_phase, avg_reaction, avg_recovery,
prior_stickiness, shrinkage_weight
```

### Script 3: validate_translation.py

**Purpose**: Validate metric reliability and predictive validity
**Input**: outputs/db_rep_scores.parquet, college stats
**Output**:
- outputs/validation_metrics.json
- outputs/validation_split_half.csv
**Runtime**: 30 seconds
**Memory**: <100MB

**Key Steps**:
1. Split-half reliability (DBs with 10+ reps)
2. Correlation with college stats (PBUs, INTs)
3. Save metrics to JSON
4. Save split-half data for plotting

**Metrics Computed**:
- Split-half correlation (r, p-value)
- Correlation with college PBUs
- Correlation with college INTs
- Sample sizes for each test

### Script 4: generate_deck_figures.py

**Purpose**: Generate all visualizations for deck
**Input**: All outputs from scripts 1-3
**Output**: figures/*.png (10-15 figures @ 300 DPI)
**Runtime**: 1-2 minutes
**Memory**: ~500MB

**Figures Generated**:
1. Stickiness framework diagram
2. Rep extraction flowchart
3. Phase score example (separation heatmap)
4. Reaction/recovery comparison
5. Overall leaderboard (top 10)
6. Sub-score leaderboards (3-panel)
7. Split-half reliability scatter
8. Drill-to-team translation
9. Insights summary

---

## F) DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: 2024_West_Practice_3.parquet (37.5M rows)               │
│        shrine_bowl_players_college_stats.csv (500 rows)        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCRIPT 1: extract_skill_1v1_reps.py                            │
│ • Filter session_id == 4 (1.2M → 40K rows)                     │
│ • Detect WR activity bursts                                    │
│ • Cluster stations (DBSCAN)                                    │
│ • Pair WR-DB (Hungarian)                                       │
│ • Score confidence                                             │
│ Runtime: 2-3 min | Memory: 500MB                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ INTERMEDIATE: outputs/reps_skill_1v1.parquet                   │
│ Size: 200 rows × 15 cols (~50KB)                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCRIPT 2: compute_db_stickiness.py                             │
│ • Compute phase/reaction/recovery scores                       │
│ • Combine: 0.45×phase + 0.30×reaction + 0.25×recovery          │
│ • Aggregate by DB                                              │
│ • Apply Bayesian shrinkage                                     │
│ Runtime: 3-5 min | Memory: 1GB                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ INTERMEDIATE: outputs/db_rep_scores.parquet                    │
│               outputs/db_player_leaderboard.csv                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCRIPT 3: validate_translation.py                              │
│ • Split-half reliability                                       │
│ • College stats correlation                                    │
│ Runtime: 30 sec | Memory: <100MB                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCRIPT 4: generate_deck_figures.py                             │
│ • 10-15 figures @ 300 DPI                                      │
│ Runtime: 1-2 min | Memory: <500MB                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT: figures/*.png + outputs/*.csv                          │
│ Total: <50MB disk usage                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Total Pipeline Runtime**: 7-11 minutes
**Total Memory Required**: ~2GB RAM recommended

---

## G) PERFORMANCE ESTIMATES

### Memory Usage

| Script | Peak Memory | Notes |
|--------|-------------|-------|
| extract_skill_1v1_reps.py | ~500MB | Column projection keeps parquet load small |
| compute_db_stickiness.py | ~1GB | Reloads tracking 200 times (rep-level) |
| validate_translation.py | <100MB | Works on aggregated data only |
| generate_deck_figures.py | ~500MB | Matplotlib figure buffers |

### Runtime

| Script | Runtime | Bottleneck |
|--------|---------|------------|
| extract_skill_1v1_reps.py | 2-3 min | Hungarian assignment |
| compute_db_stickiness.py | 3-5 min | 200 parquet reads |
| validate_translation.py | 30 sec | Simple aggregations |
| generate_deck_figures.py | 1-2 min | Matplotlib rendering |

### Optimization Opportunities

1. **Batch parquet reads**: Load all rep windows in one pass (5min → 1min)
2. **Cache trajectories**: Save extracted trajectories to intermediate parquet
3. **Parallelization**: Process reps in parallel with multiprocessing (4x speedup)

---

## H) KEY ASSUMPTIONS & EDGE CASES

### Assumptions

1. Session 4 is pure 1v1 man coverage drills
2. 10Hz sampling is consistent throughout
3. WR runs complete routes (not aborted)
4. College stats predict NFL coverage ability
5. Weights 45/30/25 capture relative importance

### Edge Cases

| Case | Handling |
|------|----------|
| Short routes (<1s) | Filter out in Step 3 |
| Multiple DBs on WR | Hungarian prevents, check cost matrix |
| Break at route end | Reaction returns neutral 0.5 |
| No separation growth | Recovery gives baseline 0.7 |
| DB tracking dropout | Skip if overlap < 70% |
| Missing college stats | Use grand mean as prior |
| Sample size < 5 reps | Flag as "insufficient sample" |

### Validation Checks

- **Rep count**: Expect 150-250 (investigate if <100)
- **Separation distribution**: Mean 3-8 yards (>15y indicates pairing failure)
- **Score distributions**: Mean 0.4-0.6 (avoid degenerate scores)
- **Sub-score correlations**: r < 0.5 (proving independence)

---

## I) COMMAND-LINE USAGE

```bash
# Create directories
mkdir -p scripts outputs figures

# Run full pipeline
python scripts/extract_skill_1v1_reps.py
python scripts/compute_db_stickiness.py
python scripts/validate_translation.py
python scripts/generate_deck_figures.py

# Quick check outputs
ls -lh outputs/
ls -lh figures/

# View leaderboard
head -20 outputs/db_player_leaderboard.csv

# Check validation metrics
cat outputs/validation_metrics.json
```

---

## J) SUCCESS CRITERIA

### Minimum Viable Output

- ✓ 100+ high-confidence reps extracted
- ✓ 8+ DBs with 5+ reps each
- ✓ Split-half correlation r > 0.50
- ✓ All 10 deck slides with figures
- ✓ Reproducible pipeline (<15 min end-to-end)

### Stretch Goals

- 200+ reps with 80%+ high confidence
- 12+ DBs with 8+ reps each
- Split-half correlation r > 0.65
- College stats correlation r > 0.30
- Automated player style tags (Mirror/Closer/Gambler)

---

## K) NEXT STEPS

1. ✅ **Review and approve this plan**
2. Create directory structure
3. Implement Script 1 (extraction)
4. Validate rep extraction (visual check)
5. Implement Script 2 (scoring)
6. Validate score distributions
7. Implement Script 3 (validation)
8. Implement Script 4 (figures)
9. Build 10-slide deck
10. Final QA and submission

**Estimated Total Time**: 4-6 hours of development + 1-2 hours deck building

---

*Plan created: 2026-01-04*
*Competition: Shrine Bowl × SūmerSports Analytics*
