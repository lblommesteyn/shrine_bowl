# Man Coverage Stickiness Metric

**Competition**: Shrine Bowl × SūmerSports Analytics Competition
**Objective**: Build an objective "Man Coverage Stickiness" metric for defensive backs
**Data Source**: 2024 West Practice 3, Session 4 ("Bigs INDY / Skill 1 on 1")

---

## 📊 Overview

This project develops a comprehensive **Man Coverage Stickiness** metric that quantifies how well defensive backs maintain tight man coverage during 1v1 drills. The metric combines three components:

1. **Phase Score (45%)** - Maintaining proximity and leverage consistency
2. **Reaction Score (30%)** - Responding quickly to route breaks
3. **Recovery Score (25%)** - Closing separation gaps with speed

Scores are aggregated using **Bayesian shrinkage** with college stats as priors to stabilize estimates for low-sample players.

---

## 📁 Project Structure

```
db_stickiness_metric/
├── scripts/
│   ├── extract_skill_1v1_reps.py       # Script 1: Rep extraction
│   ├── compute_db_stickiness.py        # Script 2: Score computation
│   ├── validate_translation.py         # Script 3: Validation
│   └── generate_deck_figures.py        # Script 4: Visualizations
├── outputs/
│   ├── reps_skill_1v1.parquet          # Extracted WR-DB paired reps
│   ├── db_rep_scores.parquet           # Rep-level stickiness scores
│   ├── db_player_leaderboard.csv       # Player-level aggregates + ranks
│   ├── validation_metrics.json         # Validation statistics
│   └── validation_split_half.csv       # Split-half reliability data
├── figures/
│   ├── methodology_*.png               # Methodology diagrams
│   ├── leaderboard_*.png               # Leaderboard visualizations
│   ├── validation_*.png                # Validation plots
│   └── analysis_*.png                  # Analysis figures
├── STICKINESS_IMPLEMENTATION_PLAN.md   # Detailed implementation plan
└── README.md                           # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Required packages:
  ```bash
  pip install pandas numpy pyarrow scikit-learn scipy matplotlib seaborn
  ```

### Data Requirements

Place the following files in the parent `data/` directory:

```
../data/Shrine Bowl Data/
├── practice_data/
│   └── 2024_West_Practice_3.parquet
└── shrine_bowl_players_college_stats.csv
```

### Running the Pipeline

Execute all scripts in order from the `db_stickiness_metric/` directory:

```bash
# Navigate to project directory
cd db_stickiness_metric

# Script 1: Extract 1v1 reps (2-3 minutes)
python scripts/extract_skill_1v1_reps.py

# Script 2: Compute stickiness scores (3-5 minutes)
python scripts/compute_db_stickiness.py

# Script 3: Validate metric (30 seconds)
python scripts/validate_translation.py

# Script 4: Generate figures (1-2 minutes)
python scripts/generate_deck_figures.py
```

**Total runtime**: ~7-11 minutes
**Memory required**: ~2GB RAM

---

## 📈 Outputs

### 1. Extracted Reps (`outputs/reps_skill_1v1.parquet`)

**Schema**:
- `rep_id`: Unique rep identifier
- `wr_name`, `db_name`: Player names
- `start_ts`, `end_ts`: Rep time window (seconds)
- `station_id`: Drill station assignment
- `confidence`: High/Medium pairing confidence
- `d_start`, `avg_sep`, `d_end`: Separation metrics (yards)
- `shadowing`: Velocity correlation score
- `overlap_pct`: Temporal coverage (%)

**Expected size**: 150-250 reps, 80%+ High/Medium confidence

### 2. Rep-Level Scores (`outputs/db_rep_scores.parquet`)

**Schema**:
- All columns from `reps_skill_1v1.parquet`
- `phase_score`, `reaction_score`, `recovery_score`: Sub-scores [0, 1]
- `stickiness`: Combined score (weighted average)
- `phase_*`: Phase score metadata (avg_separation, tight_pct, leverage_consistency)
- `reaction_*`: Reaction metadata (break_time, latency, db_dir_change)
- `recovery_*`: Recovery metadata (peak_separation, closing_speed, recovery_pct)

### 3. Player Leaderboard (`outputs/db_player_leaderboard.csv`)

**Schema**:
- `rank`: Overall rank by Bayesian stickiness
- `db_name`: Defensive back name
- `n_reps`: Sample size
- `raw_stickiness`: Mean stickiness (practice only)
- `stickiness_std`: Standard deviation
- `stickiness_bayesian`: Bayesian-adjusted score
- `avg_phase`, `avg_reaction`, `avg_recovery`: Mean sub-scores
- `prior_stickiness`: College stats prior
- `shrinkage_weight`: Weight on practice data (n/(n+15))

**Top 10 DBs** are ranked by `stickiness_bayesian`.

### 4. Validation Metrics (`outputs/validation_metrics.json`)

**Contents**:
- **Split-half reliability**: Correlation between first/second half of reps
  - Correlation, p-value, n_dbs, Spearman-Brown corrected reliability
- **College stats correlation**: Correlation with PBUs, INTs, tackles
  - Validates construct validity (coverage skills)
- **Sub-score independence**: Correlation matrix
  - Confirms Phase/Reaction/Recovery measure distinct dimensions
- **Sample size**: Total reps, DBs, DBs with 8+/10+ reps

### 5. Figures (`figures/`)

**Methodology** (Slides 2-5):
- `methodology_stickiness_framework.png`: 3-component diagram
- `methodology_rep_extraction_flow.png`: Data pipeline flowchart

**Leaderboards** (Slides 6-7):
- `leaderboard_overall_stickiness.png`: Top 10 DBs with confidence intervals
- `leaderboard_subscores_comparison.png`: Top 5 per component

**Validation** (Slide 8):
- `validation_split_half_reliability.png`: Reliability scatter plot

**Analysis**:
- `analysis_score_distributions.png`: Histograms of all scores
- `analysis_subscore_correlations.png`: Scatter matrix
- `analysis_bayesian_shrinkage.png`: Raw vs Bayesian scores
- `analysis_sample_sizes.png`: Rep counts per DB

---

## 🧮 Metric Formulas

### Phase Score

**Measures**: % of route where DB maintains proximity with leverage consistency

```
tight_pct = % frames with separation ≤ 2.0 yards
acceptable_pct = % frames with separation ≤ 3.5 yards

base_score = (tight_pct × 1.0) + (acceptable_pct - tight_pct) × 0.5

leverage_bonus = 0.10 × max(0, 1 - angular_std / π)

phase_score = min(1.1, base_score + leverage_bonus)
```

### Reaction Score

**Measures**: DB's response to WR route breaks (latency + flip severity)

```
latency_score = max(0, 1 - reaction_latency / 0.5)
flip_score = max(0, 1 - db_dir_change / 120°)

reaction_score = 0.6 × latency_score + 0.4 × flip_score
```

**Break detection**: Max angular velocity in middle 60% of route

### Recovery Score

**Measures**: DB's ability to close separation gaps after WR creates space

```
recovery_pct = max(0, closed_gap / separation_growth)
speed_score = min(1.0, closing_speed / 4.0)

recovery_score = 0.7 × recovery_pct + 0.3 × speed_score
```

**Recovery window**: 1 second after peak separation

### Combined Stickiness

```
stickiness = 0.45 × phase + 0.30 × reaction + 0.25 × recovery
```

**Weights rationale**:
- Phase (45%): Most important - staying in phase is foundation of man coverage
- Reaction (30%): Critical for preventing separation on breaks
- Recovery (25%): Important but less frequent (only when separation grows)

### Bayesian Shrinkage

```
λ = n / (n + 15)
stickiness_bayesian = λ × raw_stickiness + (1 - λ) × prior_stickiness

where:
  prior_stickiness = grand_mean + 0.10 × college_production_score
  college_production_score = 0.40×PBU_z + 0.35×INT_z + 0.15×TFL_z - 0.10×Tackles_z
```

**Shrinkage constant (k=15)**: Equivalent to "15 reps of prior confidence"

---

## 🔬 Methodology

### 1. Rep Extraction (Script 1)

**Activity Detection**:
- WR bursts identified by speed > 1.5 yds/s, duration > 1.0s
- Position variance > 4.0 yards, max speed > 3.5 yds/s

**Station Clustering**:
- DBSCAN with eps=12 yards, min_samples=3
- Handles 3-6 concurrent drill stations

**WR-DB Pairing**:
- Hungarian assignment within time blocks (10-second windows)
- Cost function: 0.50×avg_sep + 0.30×start_sep + 0.20×(1-velocity_corr)×10
- Constraints: start_sep < 8y, avg_sep < 12y, overlap > 70%

**Confidence Scoring**:
- High: start < 4y AND avg < 10y
- Medium: start < 6y AND avg < 12y
- Low: otherwise (filtered out)

### 2. Score Computation (Script 2)

For each rep:
1. Reload WR/DB trajectories from parquet
2. Compute phase_score (proximity + leverage)
3. Compute reaction_score (break response)
4. Compute recovery_score (closing speed)
5. Combine: 0.45×phase + 0.30×reaction + 0.25×recovery

Aggregate by DB:
1. Mean, std, count across all reps
2. Build college prior from defensive stats
3. Apply Bayesian shrinkage (k=15)
4. Rank by Bayesian stickiness

### 3. Validation (Script 3)

**Split-Half Reliability**:
- Random split of reps for DBs with 10+ reps
- Correlation between first/second half stickiness
- Spearman-Brown correction for full reliability

**Construct Validity**:
- Correlation with college PBUs, INTs (positive = good)
- Correlation with tackles (negative = good, less targeted)

**Sub-Score Independence**:
- Correlation matrix confirms distinct dimensions
- Target: |r| < 0.5 between components

### 4. Visualization (Script 4)

**Generates 9 figures**:
- 2 methodology diagrams
- 2 leaderboard charts
- 1 validation plot
- 4 analysis figures

---

## 📊 Expected Results

### Sample Size
- **150-250 reps** extracted
- **10-15 DBs** with 8+ reps each
- **80%+ High/Medium confidence** pairs

### Score Distributions
- **Phase**: Mean ~0.40-0.60 (tight coverage is hard)
- **Reaction**: Mean ~0.40-0.60 (quick reactions valued)
- **Recovery**: Mean ~0.50-0.70 (baseline when no gap to close)
- **Combined**: Mean ~0.45-0.65

### Validation
- **Split-half reliability**: r > 0.50 (moderate-high)
- **College PBU correlation**: r > 0.30 (positive construct validity)
- **Sub-score correlations**: |r| < 0.5 (independent dimensions)

---

## 🎯 Interpretation Guide

### Stickiness Score Ranges

| Score Range | Interpretation | Description |
|-------------|----------------|-------------|
| **0.70+** | Elite | Top-tier man coverage - stays in phase, reacts quickly, recovers well |
| **0.60-0.70** | Above Average | Strong coverage skills with minor gaps |
| **0.50-0.60** | Average | Solid fundamentals but room for improvement |
| **0.40-0.50** | Below Average | Struggles with one or more components |
| **<0.40** | Poor | Significant coverage deficiencies |

### Sub-Score Profiles

**"Mirror" DBs** (High Phase, Moderate Reaction/Recovery):
- Excellent at staying in phase throughout route
- Prevent separation by maintaining leverage
- Example: Phase 0.75, Reaction 0.55, Recovery 0.60

**"Late Closer" DBs** (Moderate Phase, High Recovery):
- Allow some separation but close gaps aggressively
- Strong burst and closing speed
- Example: Phase 0.55, Reaction 0.50, Recovery 0.80

**"Reactive" DBs** (Moderate Phase, High Reaction):
- Quick to react to route breaks
- Minimal panic flips, fast response times
- Example: Phase 0.60, Reaction 0.75, Recovery 0.55

**"Gambler" DBs** (High Variance):
- Large spread in scores across reps
- Inconsistent technique or risk-taking style
- High std (>0.15)

---

## 🔧 Customization

### Adjusting Weights

Edit in `compute_db_stickiness.py`:

```python
WEIGHT_PHASE = 0.45      # Default: 45%
WEIGHT_REACTION = 0.30   # Default: 30%
WEIGHT_RECOVERY = 0.25   # Default: 25%
```

### Adjusting Thresholds

**Phase**:
```python
PHASE_TIGHT_THRESHOLD = 2.0       # Default: 2.0 yards
PHASE_ACCEPTABLE_THRESHOLD = 3.5  # Default: 3.5 yards
```

**Reaction**:
```python
MAX_REACTION_LATENCY = 0.5        # Default: 0.5 seconds
PANIC_FLIP_THRESHOLD = 120        # Default: 120 degrees
```

**Recovery**:
```python
SEPARATION_GROWTH_THRESHOLD = 1.5  # Default: 1.5 yards
RECOVERY_WINDOW = 1.0             # Default: 1.0 second
```

### Adjusting Bayesian Shrinkage

```python
SHRINKAGE_K = 15  # Default: 15 (equivalent to "15 reps of prior confidence")
```

Increase k for more shrinkage (more weight on prior), decrease for less shrinkage (more weight on practice data).

---

## 📝 Citation

If you use this metric in your analysis or presentation:

```
Man Coverage Stickiness Metric (2024)
Shrine Bowl × SūmerSports Analytics Competition
Components: Phase (45%), Reaction (30%), Recovery (25%)
Bayesian shrinkage with college defensive stats as priors
```

---

## 🐛 Troubleshooting

### Error: "Parquet file not found"

**Solution**: Ensure `2024_West_Practice_3.parquet` is in `../data/Shrine Bowl Data/practice_data/`

### Error: "No WR activity bursts detected"

**Possible causes**:
1. Session ID filter incorrect (check session_id == 4)
2. Activity thresholds too strict (lower `ACTIVE_SPEED_THRESHOLD`)
3. Column names different (check `ts`, `s`, `player_name` exist)

### Warning: "Only X DBs with 10+ reps"

**Expected**: Some practices may have fewer high-rep DBs. Lower `MIN_REPS_SPLIT` in `validate_translation.py` if needed.

### Low split-half reliability (r < 0.4)

**Possible causes**:
1. Small sample sizes (need more reps per DB)
2. High measurement noise (check score distributions for outliers)
3. Metric capturing game-to-game variance (not a flaw - coverage is situational)

---

## 📧 Contact

For questions about this implementation:
- Review the detailed plan: `STICKINESS_IMPLEMENTATION_PLAN.md`
- Check existing code patterns in parent directory (e.g., `build_team_drill_rep_table_v2.py`)

---

## 📄 License

This code is for the Shrine Bowl × SūmerSports Analytics Competition.

---

**Last Updated**: 2026-01-04
**Version**: 1.0
**Status**: ✅ Ready for execution
