# Shrine Bowl Analytics Data Overview

## 1. Tracking Data (The "How")
**Source:** `data/Shrine Bowl Data/practice_data/*.parquet`
**Volume:** ~58 Million Rows | 1.9 GB
This is the raw, frame-by-frame physics engine of the Shrine Bowl.

*   **Files:**
    *   `2022_West_Practice_2.snappy.parquet` (20.5M rows): Historical baseline.
    *   `2024_West_Practice_3.parquet` (37.5M rows): Current year analysis target.
*   **Granularity:** 10 Hz (approx) tracking of every player on the field.
*   **Schema (Key Cols):**
    *   `ts` (Timestamp): The heartbeat of the data.
    *   `x`, `y` (Float): Field position accurate to inches.
    *   `s` (Speed), `a` (Accel): Derived physics metrics for "Burst" calculations.
    *   `o` (Orientation), `dir` (Direction): Critical for calculating "Facing" vs "Moving" vectors (hips vs feet).
*   **Processing:**
    *   We filtered this down to **9,813,118 rows** of high-relevance "Team Drill" data (`team_1_matched.csv`) for our analysis.

## 2. Player Metadata (The "Who")
**Source:** `data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv`
**Volume:** 1,000+ Players
Contextual profile data and college production.

*   **Identity:** `player_name`, `position`, `school`, `college_gsis_id`.
*   **Physicals:** Height/Weight (not consistently present in this specific CSV, verified in other auxiliary files if available).
*   **Production:** `passing_yards`, `rushing_yards`, `receiving_yards`, `defense_interceptions`.

## 3. Derived Analytics (Our Value Add)
**Source:** `full_analysis_results.csv`
**Volume:** 246 Analyzed 1-on-1 Reps
The distilled intelligence generated from the raw millions of rows.

*   **Scope:** 246 high-quality, matched 1-on-1 interactions extracted from 11v11 team drills.
*   **Metrics:**
    *   **Separation Efficiency:** `Sep_at_Break` (Distance from DB at cut).
    *   **Route Sharpness:** `Break_Angle`.
    *   **Defender Stickiness:** `Closing_Burst` (Recovery speed).
    *   **Fluidity:** `Speed_Maint` (% of max speed retained).
    *   **Context Features:** `Start_dx`/`Start_dy` (Alignment), `Route_Depth`.

**Key Metrics (Moneyball Upgrade):**
*   **Win:** Binary label (1 if Separation > 1.5 yds).
*   **Expected Win Probability:** Model prediction ($P(Win|Context)$).
*   **WROE (Win Rate Over Expected):** The context-adjusted grade.
    *   `WROE > 0`: Beating the scheme/difficulty.
    *   `WROE < 0`: Performing below expectation.

## 4. Limitations
*   **No Ball Data:** We cannot calculate "Catch Point" separation directly.
*   **No Outcomes:** We don't know if a pass was caught, dropped, or intercepted (inferred via college stats proxy).
