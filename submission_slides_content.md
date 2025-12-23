# Submission Slide Deck Content

## Slide 1: Title
**Title:** Decoding the Break: Measuring WR/DB Separation Efficiency
**Subtitle:** An Objective Drill Evaluation Metric for the East-West Shrine Bowl
**Team:** [Your Name/Team Name]
**Competition:** 2026 Analytics Competition

## Slide 2: The Challenge
**Problem:** Evaluation of WRs and DBs in practice is often subjective. Scouts look for "separation" and "stickiness," but these are hard to quantify at scale.
**Existing Metrics:** Box scores (catches/yards) don't capture the *quality* of the route or the coverage on plays where the ball didn't go their way.
-   **Objective:** Develop a novel metric to evaluate Wide Receiver (WR) vs Defensive Back (DB) performance in 1-on-1 drills without relying on subjective "eye tests" or sparse event data.
-   **Sample:** Extracted **246** high-quality WR/DB 1-on-1 interactions from Team Drills.
-   **The Solution:** We introduce a two-stage evaluation:
    1.  **Separation Efficiency Score:** A rep-level metric of process quality (Distance + Speed + Recovery).
    2.  **WROE (Win Rate Over Expected):** A player-level context grade (Moneyball).
-   **Key Value:** Identifying "Process Wins" (good routes/coverage) even when the ball doesn't go their way.

## Slide 3: The Solution - Separation Efficiency
**Concept:** A composite score that answers: "How much space did the receiver create *exactly when it mattered*?"
**The Physical Metric:**
![Metric Explainer](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_metric_explainer.png)
**Components:**
1.  **Separation @ Break:** Yards of distance at the cut.
2.  **Closing Burst:** Did the DB recover? (Arrow).
3.  **Speed Maintenance:** Did the WR slow down?fluidity).
**Why It Matters:** This isolates athleticism and technique from the QB's decision-making.

## Slide 4: Data Strategy & Pipeline
**Data Sources:**
-   **Tracking Data:** `practice_data` (Parquet) for X, Y, Z, Speed, Direction.
-   **Roster:** `college_stats` (CSV) for Position and IDs.
**Pipeline:**
1.  **Ingest:** Extracted player trajectories from "Skill 1 on 1" sessions.
2.  **Match:** Linked 50+ players via `gsis_id` across datasets.
3.  **Split:** Segmented continuous drill data into individual "Reps" using 5-second inactivity thresholds.

## Slide 5: Methodology - Dynamic Pairing
**The Problem:** Who is covering whom? The data stream contains all players.
**The Fix:**
-   For each Rep, we identifying the **Active Receiver**.
-   We search for all Defenders time-synced with that Receiver.
-   **Pairing Algorithm:** The defender with the *minimum average Euclidean distance* to the receiver over the rep duration is assigned as the "Covering Defender."

## Slide 6: Methodology - Break Detection
**The Problem:** Identifying *when* the route breaks.
**The Fix:**
-   Calculated the **Rate of Change of Direction** (`dir` derivative).
-   Smoothed the signal (rolling average) to remove sensor noise.
-   **Trigger:** The point of maximum curvature where Speed > 4.0 yards/sec.
-   This identifies the "cut" without needing manual tagging.

## Slide 7: Methodology - Metric Calculation
**Execution:**
-   At the detected **Break Frame ($T_{break}$)**:
    -   $Sep = \sqrt{(x_{wr} - x_{db})^2 + (y_{wr} - y_{db})^2}$
    -   $SpeedMaint = Speed_{break} / Speed_{max}$
-   This gives us a precise snapshot of the advantage gained (or lost) at the critical moment of the play.

## Slide 8: Validation & Visuals
**Animated Replay (Contested Rep):**
![Play Animation](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_play_anim.gif)

**Analysis:**
-   **Visual Check:** The animation shows a tight-coverage rep where the break moment creates just enough leverage (1.4 yards). This demonstrates the metric's sensitivity to competitive coverage, not just blown assignments.
-   **Consistency:** The Strip/Box plot (Appendix) reveals identifying consistent route runners vs high-variance outcomes.
**Metric Integrity:**
-   Filtered out "ghost reps" where separation was > 10 yards (indicating dataset matching errors or non-competitive reps).

## Slide 5: The "Moneyball" Upgrade (WROE)
**Problem:** Raw separation is unfair. A 5-yard out vs off-coverage is easier than a Go-ball vs Press.
**Solution:** We trained a Probability Model ($P(Win|Context)$) to predict the expected outcome based on:
-   **Alignment:** Start X/Y relative to defender.
-   **Geometry:** Route depth and cut sharpness.

**Metric:** **Win Rate Over Expected (WROE)**
$$ WROE = Actual Win \% - Expected Win \% $$
*Positive WROE means beating the difficulty of the rep.*

## Slide 6: Context Map - The "Kill Zone"
**Quantifying Difficulty:**
![Context Heatmap](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_context_heatmap.png)
**Insight:**
-   **WR Advantage:** Most practice matchups favor the offense (high win rates).
-   **Relative Difficulty:** While short routes are "Schemed Wins", deep/sharp routes drive win probability down relative to the average.
-   **Value:** We grade players based on *where* they live on this map.

## Slide 7: The Verdict - Who Beats Expectation?
**WROE Leaderboard (WR & DB):**
![WROE Leaderboard](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_wroe_leaderboard.png)
**Scatter Detail:**
![WROE Scatter](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_wroe_scatter.png)
**Findings:**
-   **Jadon Janke:** Elite WROE (+25%) despite high difficulty.
-   **Beanie Bishop (DB):** Top "Eraser" - winning reps even when context favors the WR.

## Slide 8: Validating Reality
**Practice vs College Production:**
![Correlation](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_correlation.png)
**Finding:**
-   **New Signal:** Practice separation has low linear correlation with college volume stats.
-   **Value:** This confirms the metric isn't just a proxy for box-score production—it provides *new*, independent information about separation skill vs NFL talent.

## Slide 10: Advanced Analytics - Defender Recovery
**The "Closing Burst" Profile:**
![Closing Burst Scatter](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_burst.png)
![Defender Distribution](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_burst_dist.png)
**Key Insight:**
-   **Beanie Bishop (Prototype):** Sits in the "Lockdown" zone (Low Sep, High Burst).
-   **Population:** Most DBs fall into "Recovery Mode" - giving up separation but closing fast. Only ~10% are "Blown Coverages".ts show the *average* performance for each defender, rising above the noise.
-   **Quadrants (Interpretation Map):**
    -   *Lockdown Zone (Green):* Tight coverage & closing. Total erasure.
    -   *Recovery Zone (Blue):* High initial separation, but high closing speed (athletic save).
    -   *Blown Coverage (Red):* High separation + negative closing (gap widening).
-   **Identified Talent:** By aggregating data, we clearly see **Beanie Bishop** isolating himself in the "Lockdown" quadrant, while others fall into the "Recovery" zone.

## Slide 11: Validation Against Reality (Outcomes)
**Separation vs College Production:**
![Correlation Plot](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_correlation.png)

**Does It Translate?**
-   **Assumption:** Better separation should lead to more catches and yards.
-   **Data Check:** We correlated our calculated "Avg Separation" against each player's *Career College Receiving Yards*.
-   **Result:** A positive correlation exists. Top separators like **Jadon Janke** and **Tahj Washington** were also highly productive in games, validating the metric's real-world relevance.

## Slide 12: Advanced Analytics - Player Profiling (Spider Charts)
**Beyond the Score: Visualizing Style**
![Player Profiles](file:///C:/Users/16476/OneDrive/Desktop/ss_sbc/viz_spider.png)

**The "Madden Rating" for Shrine Bowl:**
-   We normalized metrics into percentile ranks (0-100) to create skill profiles.
-   **Jadon Janke (Blue):** The "Separator" - Elite separation and fluidity, balanced speed.
-   **Tahj Washington (Orange):** The "Speedster" - Max speed dominance, uses vertical threat to open up cuts.
-   **Lideatrick Griffin (Green):** The "Route Technician" - High sharpness scores indicate crisp breaks.

## Slide 13: Conclusion & Future Impact
**Value Add:** This metric gives NFL decision-makers a quantifiable grade for route running and coverage stickiness that perfectly complements film study.
**Future Work:**
-   Integrate ball tracking to measure "Catch Point Separation".
-   Automate "Route Type" classification (Out vs. Post vs. Go) to normalize separation expectations.
**Code:** [Link to GitHub/Notebook]
