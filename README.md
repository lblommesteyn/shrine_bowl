# How to Recreate Data, Outputs, and Figures

This guide explains how to regenerate all data, intermediate outputs, and visualizations for the **Man Coverage Stickiness Metric** project.

---

## 📋 Overview

The pipeline consists of **4 sequential scripts** that:
1. Extract 1v1 rep pairings from raw tracking data
2. Compute stickiness scores (phase, reaction, recovery components)
3. Validate metric reliability and construct validity
4. Generate publication-ready visualizations

**Total runtime**: 7-11 minutes  
**Memory required**: ~2GB RAM  
**Disk space**: ~500MB (for outputs and figures)

---

## 🗂️ Directory Structure

```
shrine_bowl/
├── data/                                    # ← Raw data (NOT in repo)
│   └── Shrine Bowl Data/
│       ├── practice_data/
│       │   └── 2024_West_Practice_3.parquet
│       └── shrine_bowl_players_college_stats.csv
│
└── db_stickiness_metric/
    ├── scripts/                             # ← All processing scripts
    │   ├── extract_skill_1v1_reps.py       # Step 1
    │   ├── compute_db_stickiness.py        # Step 2
    │   ├── validate_translation.py         # Step 3
    │   └── generate_deck_figures.py        # Step 4
    │
    ├── outputs/                             # ← Generated outputs (NOT in repo)
    │   ├── reps_skill_1v1.parquet          # Extracted rep pairings
    │   ├── db_rep_scores.parquet           # Rep-level scores
    │   ├── db_player_leaderboard.csv       # Player aggregates
    │   ├── validation_metrics.json         # Validation stats
    │   └── validation_split_half.csv       # Split-half data
    │
    ├── figures/                             # ← Generated figures (NOT in repo)
    │   ├── methodology_*.png
    │   ├── leaderboard_*.png
    │   ├── validation_*.png
    │   └── analysis_*.png
    │
    ├── run_pipeline.py                      # Master runner script
    ├── README.md                            # Main documentation
    └── STICKINESS_IMPLEMENTATION_PLAN.md   # Detailed technical plan
```

---

## 🔧 Prerequisites

### 1. Python Environment

Ensure Python 3.8+ is installed:
```bash
python --version
```

### 2. Install Dependencies

```bash
pip install pandas numpy pyarrow scikit-learn scipy matplotlib seaborn
```

**Package versions** (tested):
- pandas >= 1.3.0
- numpy >= 1.21.0
- pyarrow >= 5.0.0
- scikit-learn >= 0.24.0
- scipy >= 1.7.0
- matplotlib >= 3.4.0
- seaborn >= 0.11.0

### 3. Obtain Raw Data Files

You need two files in the `data/Shrine Bowl Data/` directory:

#### File 1: Practice Tracking Data
**Location**: `data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet`

**Schema** (expected columns):
- `ts` (float): Timestamp in seconds
- `s` (int): Session ID (filter for session_id == 4)
- `player_name` (str): Player name
- `x`, `y` (float): Position coordinates (yards)
- `v_x`, `v_y` (float): Velocity components (yards/second)
- `player_id` (int): Unique player identifier
- `team` (str): Team assignment (e.g., "WR", "DB")

**Size**: ~100-200 MB (parquet compressed)

**Source**: Provided by Shrine Bowl / SūmerSports (contact organizers if missing)

#### File 2: College Stats Reference
**Location**: `data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv`

**Schema** (expected columns):
- `player_name` (str): Player name (must match tracking data)
- `pbu` (int): Pass breakups in college
- `int` (int): Interceptions in college
- `tfl` (int): Tackles for loss in college
- `tackles` (int): Total tackles in college
- `school` (str): College name

**Size**: ~50-100 KB

**Source**: Provided by Shrine Bowl / SūmerSports (contact organizers if missing)

---

## 🚀 Running the Pipeline

### Option A: Run Full Pipeline (Recommended)

From the `db_stickiness_metric/` directory:

```bash
cd db_stickiness_metric
python run_pipeline.py
```

This will:
1. Run all 4 scripts sequentially
2. Display progress and timing for each step
3. Validate outputs at the end
4. Report any errors with recovery instructions

**Expected output**:
```
================================================================================
                    DB STICKINESS METRIC PIPELINE
================================================================================

Competition: Shrine Bowl × SūmerSports Analytics
Objective: Build Man Coverage Stickiness metric for DBs

Total estimated time: 7-11 minutes

Running full pipeline (all 4 steps)...

================================================================================
                 STEP 1/4: Script 1: Extract Skill 1v1 Reps
================================================================================
...
✓ Step 1 completed successfully in 145.2s
...
✓ ALL CHECKS PASSED
```

### Option B: Run Individual Steps

If a step fails, you can re-run just that step:

```bash
# Run only Step 1 (extraction)
python run_pipeline.py --step 1

# Run only Step 2 (scoring)
python run_pipeline.py --step 2

# Run only Step 3 (validation)
python run_pipeline.py --step 3

# Run only Step 4 (figures)
python run_pipeline.py --step 4
```

### Option C: Run Scripts Directly

For debugging or custom workflows:

```bash
# Step 1: Extract reps
python scripts/extract_skill_1v1_reps.py

# Step 2: Compute scores
python scripts/compute_db_stickiness.py

# Step 3: Validate
python scripts/validate_translation.py

# Step 4: Generate figures
python scripts/generate_deck_figures.py
```

---

## 📊 Understanding the Outputs

### Step 1: Rep Extraction

**Output**: `outputs/reps_skill_1v1.parquet`

**What it contains**: All extracted WR-DB pairings from the 1v1 drill

**Key columns**:
- `rep_id`: Unique identifier for each rep
- `wr_name`, `db_name`: Player names
- `start_ts`, `end_ts`: Time window (seconds into session)
- `station_id`: Which drill station (0-5)
- `confidence`: "High", "Medium", or "Low"
- `d_start`: Starting separation (yards)
- `avg_sep`: Average separation (yards)
- `d_end`: Ending separation (yards)
- `shadowing`: Velocity correlation (0-1)
- `overlap_pct`: Temporal overlap (0-100%)

**Expected statistics**:
- **Total reps**: 150-250
- **High confidence**: 60-80%
- **Medium confidence**: 15-30%
- **Low confidence**: 5-15% (filtered out in later steps)
- **Unique DBs**: 10-20

**How to inspect**:
```bash
# View first 10 reps
python -c "import pandas as pd; df = pd.read_parquet('outputs/reps_skill_1v1.parquet'); print(df.head(10))"

# Summary statistics
python -c "import pandas as pd; df = pd.read_parquet('outputs/reps_skill_1v1.parquet'); print(df.describe())"

# Confidence breakdown
python -c "import pandas as pd; df = pd.read_parquet('outputs/reps_skill_1v1.parquet'); print(df['confidence'].value_counts())"
```

---

### Step 2: Score Computation

**Output**: `outputs/db_rep_scores.parquet`

**What it contains**: All extracted reps with computed stickiness scores

**Key columns** (in addition to Step 1 columns):
- `phase_score`: Phase score [0, 1]
- `reaction_score`: Reaction score [0, 1]
- `recovery_score`: Recovery score [0, 1]
- `stickiness`: Combined score = 0.45×phase + 0.30×reaction + 0.25×recovery
- `phase_tight_pct`: % of route with separation ≤ 2.0 yards
- `phase_acceptable_pct`: % of route with separation ≤ 3.5 yards
- `phase_leverage_consistency`: Angular consistency (0-1)
- `reaction_latency`: Time to respond to break (seconds)
- `reaction_db_dir_change`: DB direction change (degrees)
- `recovery_peak_sep`: Maximum separation reached (yards)
- `recovery_closing_speed`: Speed of gap closure (yards/second)
- `recovery_pct`: % of gap closed

**Also generated**: `outputs/db_player_leaderboard.csv`

**What it contains**: Player-level aggregates and rankings

**Key columns**:
- `rank`: Overall rank (1 = best)
- `db_name`: Defensive back name
- `n_reps`: Number of reps (sample size)
- `raw_stickiness`: Mean stickiness (practice only)
- `stickiness_std`: Standard deviation
- `stickiness_bayesian`: Bayesian-adjusted score (accounts for sample size)
- `avg_phase`, `avg_reaction`, `avg_recovery`: Mean sub-scores
- `prior_stickiness`: College stats prior
- `shrinkage_weight`: Weight on practice data (n/(n+15))

**Expected statistics**:
- **Top DB stickiness**: 0.65-0.75
- **Average stickiness**: 0.45-0.55
- **Bottom DB stickiness**: 0.35-0.45
- **DBs with 10+ reps**: 8-12

**How to inspect**:
```bash
# View top 10 DBs
python -c "import pandas as pd; df = pd.read_csv('outputs/db_player_leaderboard.csv'); print(df[['rank', 'db_name', 'n_reps', 'stickiness_bayesian']].head(10))"

# View a specific player
python -c "import pandas as pd; df = pd.read_csv('outputs/db_player_leaderboard.csv'); print(df[df['db_name'].str.contains('Smith', case=False)])"

# Summary statistics
python -c "import pandas as pd; df = pd.read_csv('outputs/db_player_leaderboard.csv'); print(df[['n_reps', 'raw_stickiness', 'stickiness_bayesian']].describe())"
```

---

### Step 3: Validation

**Output**: `outputs/validation_metrics.json`

**What it contains**: Validation statistics for metric reliability

**Key metrics**:
```json
{
  "split_half_reliability": {
    "correlation": 0.62,
    "p_value": 0.003,
    "n_dbs": 11,
    "spearman_brown_corrected": 0.76
  },
  "college_stats_correlation": {
    "pbu_correlation": 0.35,
    "int_correlation": 0.28,
    "tackles_correlation": -0.15
  },
  "subscore_independence": {
    "phase_reaction_corr": 0.38,
    "phase_recovery_corr": 0.42,
    "reaction_recovery_corr": 0.31
  },
  "sample_sizes": {
    "total_reps": 187,
    "unique_dbs": 14,
    "dbs_with_8_plus_reps": 12,
    "dbs_with_10_plus_reps": 10
  }
}
```

**Interpretation**:
- **Split-half reliability > 0.50**: Metric is stable (good)
- **College stats correlation > 0.25**: Metric correlates with known skills (good)
- **Subscore correlations < 0.50**: Components measure distinct dimensions (good)

**How to inspect**:
```bash
# View validation metrics
python -c "import json; data = json.load(open('outputs/validation_metrics.json')); print(json.dumps(data, indent=2))"

# Extract specific metric
python -c "import json; data = json.load(open('outputs/validation_metrics.json')); print(f\"Split-half reliability: {data['split_half_reliability']['spearman_brown_corrected']:.3f}\")"
```

---

### Step 4: Figures

**Output**: `figures/` directory with 9 PNG images

**Methodology figures** (Slides 2-5):
- `methodology_stickiness_framework.png`: 3-component framework diagram
- `methodology_rep_extraction_flow.png`: Data pipeline flowchart

**Leaderboard figures** (Slides 6-7):
- `leaderboard_overall_stickiness.png`: Top 10 DBs with 95% confidence intervals
- `leaderboard_subscores_comparison.png`: Top 5 per component (phase, reaction, recovery)

**Validation figure** (Slide 8):
- `validation_split_half_reliability.png`: Scatter plot of first-half vs second-half scores

**Analysis figures** (Slides 9-10):
- `analysis_score_distributions.png`: Histograms of all scores
- `analysis_subscore_correlations.png`: Scatter matrix of components
- `analysis_bayesian_shrinkage.png`: Raw vs Bayesian scores
- `analysis_sample_sizes.png`: Rep counts per DB

**Figure specifications**:
- **Resolution**: 1920×1440 pixels (high-quality for presentations)
- **Format**: PNG (lossless)
- **File size**: 200-500 KB each
- **Style**: Professional with SūmerSports branding

**How to use**:
```bash
# List all figures
ls -lh figures/

# View a specific figure
open figures/leaderboard_overall_stickiness.png  # macOS
start figures/leaderboard_overall_stickiness.png # Windows
```

---

## 🔍 Troubleshooting

### Error: "Parquet file not found"

**Cause**: Raw data files are missing

**Solution**:
1. Verify `data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet` exists
2. Verify `data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv` exists
3. Check file paths are correct (case-sensitive on Linux/Mac)
4. Contact Shrine Bowl organizers if files are unavailable

**Diagnostic command**:
```bash
# Check if files exist
ls -la ../data/Shrine\ Bowl\ Data/practice_data/
ls -la ../data/Shrine\ Bowl\ Data/shrine_bowl_players_college_stats.csv
```

---

### Error: "No WR activity bursts detected"

**Cause**: Session filter or activity detection thresholds are incorrect

**Solution**:
1. Verify session_id == 4 is correct (check `STICKINESS_IMPLEMENTATION_PLAN.md`)
2. Lower activity detection thresholds in `extract_skill_1v1_reps.py`:
   ```python
   ACTIVE_SPEED_THRESHOLD = 1.5  # Try 1.2 if too strict
   MIN_BURST_DURATION = 1.0      # Try 0.8 if too strict
   ```
3. Check column names match: `ts`, `s`, `player_name`, `x`, `y`, `v_x`, `v_y`

**Diagnostic command**:
```bash
# Check available sessions
python -c "import pandas as pd; df = pd.read_parquet('../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'); print(df['s'].unique())"

# Check player names
python -c "import pandas as pd; df = pd.read_parquet('../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'); print(df['player_name'].unique()[:20])"
```

---

### Warning: "Only X DBs with 10+ reps"

**Cause**: Low sample sizes for some players (expected in short practices)

**Solution**: This is normal. The metric uses Bayesian shrinkage to stabilize estimates for low-rep players. If you need more reps:
1. Include additional sessions (modify `extract_skill_1v1_reps.py`)
2. Lower the confidence threshold (include "Low" confidence pairs)
3. Increase time window for rep detection

---

### Low split-half reliability (r < 0.4)

**Cause**: Small sample sizes or high measurement noise

**Solution**:
1. Increase sample size (more reps per DB)
2. Check for outliers in scores:
   ```bash
   python -c "import pandas as pd; df = pd.read_parquet('outputs/db_rep_scores.parquet'); print(df['stickiness'].describe())"
   ```
3. Review metric formulas in `README.md` (may need threshold adjustments)

---

### Memory error during Step 1 or 2

**Cause**: Insufficient RAM for large parquet files

**Solution**:
1. Close other applications to free RAM
2. Process in chunks (modify scripts to filter by station_id)
3. Upgrade to a machine with 4GB+ RAM

**Diagnostic command**:
```bash
# Check available memory
python -c "import psutil; print(f'Available RAM: {psutil.virtual_memory().available / 1e9:.1f} GB')"
```

---

## 🎯 Customization

### Adjusting Score Weights

Edit `scripts/compute_db_stickiness.py`:

```python
# Line ~30
WEIGHT_PHASE = 0.45      # Default: 45% (proximity + leverage)
WEIGHT_REACTION = 0.30   # Default: 30% (break response)
WEIGHT_RECOVERY = 0.25   # Default: 25% (gap closure)
```

Then re-run Step 2:
```bash
python run_pipeline.py --step 2
```

---

### Adjusting Detection Thresholds

Edit `scripts/extract_skill_1v1_reps.py`:

```python
# Phase thresholds (yards)
PHASE_TIGHT_THRESHOLD = 2.0       # Tight coverage
PHASE_ACCEPTABLE_THRESHOLD = 3.5  # Acceptable coverage

# Reaction thresholds
MAX_REACTION_LATENCY = 0.5        # Seconds
PANIC_FLIP_THRESHOLD = 120        # Degrees

# Recovery thresholds
SEPARATION_GROWTH_THRESHOLD = 1.5  # Yards
RECOVERY_WINDOW = 1.0             # Seconds
```

Then re-run Step 1:
```bash
python run_pipeline.py --step 1
```

---

### Adjusting Bayesian Shrinkage

Edit `scripts/compute_db_stickiness.py`:

```python
# Line ~50
SHRINKAGE_K = 15  # Default: 15 (equivalent to "15 reps of prior confidence")
```

**Effect**:
- **Increase k** (e.g., 20): More weight on college priors, less on practice data
- **Decrease k** (e.g., 10): More weight on practice data, less on priors

Then re-run Step 2:
```bash
python run_pipeline.py --step 2
```

---

## 📈 Expected Results

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

## 🔄 Re-running the Pipeline

### Scenario 1: Update with New Data

If you have a new practice session:
1. Place new parquet file in `data/Shrine Bowl Data/practice_data/`
2. Update session_id filter in `extract_skill_1v1_reps.py`
3. Delete old outputs: `rm -rf outputs/ figures/`
4. Run full pipeline: `python run_pipeline.py`

### Scenario 2: Adjust Metric Weights

1. Edit weights in `compute_db_stickiness.py`
2. Delete old outputs: `rm -rf outputs/db_rep_scores.parquet outputs/db_player_leaderboard.csv`
3. Re-run Step 2: `python run_pipeline.py --step 2`
4. Re-run Step 4: `python run_pipeline.py --step 4`

### Scenario 3: Regenerate Figures Only

1. Edit visualization code in `generate_deck_figures.py`
2. Delete old figures: `rm -rf figures/`
3. Re-run Step 4: `python run_pipeline.py --step 4`

---

## 📊 Interpreting Results

### Stickiness Score Ranges

| Score | Interpretation | Description |
|-------|----------------|-------------|
| **0.70+** | Elite | Top-tier man coverage - stays in phase, reacts quickly, recovers well |
| **0.60-0.70** | Above Average | Strong coverage skills with minor gaps |
| **0.50-0.60** | Average | Solid fundamentals but room for improvement |
| **0.40-0.50** | Below Average | Struggles with one or more components |
| **<0.40** | Poor | Significant coverage deficiencies |

### Player Profiles

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

---

## 📝 Next Steps

After running the pipeline:

1. **Review leaderboard**:
   ```bash
   head -20 outputs/db_player_leaderboard.csv
   ```

2. **Check validation metrics**:
   ```bash
   python -c "import json; print(json.dumps(json.load(open('outputs/validation_metrics.json')), indent=2))"
   ```

3. **View figures**:
   ```bash
   ls -lh figures/
   ```

4. **Build presentation deck** using figures/ (see PRESENTATION_DECK_FINAL.md)

5. **Customize metric** using thresholds and weights (see Customization section above)

---

## 📧 Questions?

For technical questions:
- Review `STICKINESS_IMPLEMENTATION_PLAN.md` for detailed methodology
- Check `README.md` for metric formulas and interpretation
- Review script docstrings for implementation details

---

**Last Updated**: 2026-01-09  
**Version**: 1.0  
**Status**: ✅ Ready for execution
