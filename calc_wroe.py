import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Settings
input_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"

print("Loading results...")
try:
    df = pd.read_csv(input_path)
except FileNotFoundError:
    print("Waiting for full_analysis_results.csv to be generated...")
    exit()

print(f"Loaded {len(df)} reps.")

# 1. Labeling Wins
# User suggested: Check distribution.
median_sep = df['Sep_at_Break'].median()
print(f"Median Separation: {median_sep:.2f} yards")

# Configurable Threshold: Let's use 1.5 yds as originally planned, closer to "Open"
WIN_THRESHOLD = 1.5
df['Win'] = (df['Sep_at_Break'] >= WIN_THRESHOLD).astype(int)
print(f"Win Rate (Threshold {WIN_THRESHOLD}y): {df['Win'].mean():.2%}")

# 2. Feature Engineering
# Relative Alignment are already in columns Start_dx, Start_dy
# Route Depth is Route_Depth
# Break_Angle is Break_Angle. Let's bin it.

def bin_break_angle(angle):
    if angle < 45: return 'Soft' # 0-45
    elif angle < 90: return 'Medium' # 45-90
    else: return 'Hard' # >90 (Out/In sharp cuts)

df['Break_Type'] = df['Break_Angle'].apply(bin_break_angle)

# One-Hot Encode
df_model = pd.get_dummies(df, columns=['Break_Type'], drop_first=True)

# Define Features
features = ['Start_dx', 'Start_dy', 'Route_Depth']
# Add generated columns
features += [c for c in df_model.columns if 'Break_Type_' in c]
print("Features used:", features)

# Handle NaNs (just in case)
df_model = df_model.dropna(subset=features)

# 3. Modeling (Train/Val Split)
X = df_model[features]
y = df_model['Win']

# Standardize continuous features for Logistic Regression coefficients to be comparable
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_scaled = pd.DataFrame(X_scaled, columns=features)

sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
for train_index, val_index in sss.split(X_scaled, y):
    X_train, X_val = X_scaled.iloc[train_index], X_scaled.iloc[val_index]
    y_train, y_val = y.iloc[train_index], y.iloc[val_index]

clf = LogisticRegression(random_state=42, C=1.0) # Standard L2 penalty
clf.fit(X_train, y_train)

# Validation Metrics
val_preds_prob = clf.predict_proba(X_val)[:, 1]
val_preds = (val_preds_prob > 0.5).astype(int)

auc = roc_auc_score(y_val, val_preds_prob)
acc = accuracy_score(y_val, val_preds)
print(f"\nModel Performance (Validation):")
print(f"AUC: {auc:.3f}")
print(f"Accuracy: {acc:.3f}")
print("Coefficients:")
coefs = dict(zip(features, clf.coef_[0]))
for f, c in coefs.items():
    print(f"  {f}: {c:.3f}")

# 4. Grading (WROE)
# Predict on ALL data for grading
all_preds_prob = clf.predict_proba(X_scaled)[:, 1]
df['Expected_Win_Prob'] = all_preds_prob

# Aggregation
summary = df.groupby('WR').agg(
    Reps=('Win', 'count'),
    Wins=('Win', 'sum'),
    Exp_Wins=('Expected_Win_Prob', 'sum')
).reset_index()

# Filter Min Reps
summary = summary[summary['Reps'] >= 5]

summary['Actual_Win_Rate'] = summary['Wins'] / summary['Reps']
summary['Avg_Exp_Win_Rate'] = summary['Exp_Wins'] / summary['Reps']
summary['WROE'] = summary['Actual_Win_Rate'] - summary['Avg_Exp_Win_Rate']

summary = summary.sort_values('WROE', ascending=False)
print("\nTop 5 WRs by WROE:")
print(summary[['WR', 'Reps', 'Actual_Win_Rate', 'Avg_Exp_Win_Rate', 'WROE']].head())

# Save Grading
summary.to_csv(os.path.join(output_dir, "wroe_results.csv"), index=False)

# 5. Visuals
# 5. Visuals
def set_clean_style():
    sns.set_theme(style="white")
    plt.rcParams.update({
        'figure.dpi': 300,
        'figure.figsize': (10, 6),
        'font.size': 12,
        'axes.titlesize': 14,
        'axes.titleweight': 'bold',
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.color': '#cccccc'
    })

set_clean_style()

# A. Composite Verdict Dashboard (Bar + Scatter)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

# --- Chart 1: The Elite (Bar Chart) ---
# Filter Top 7 WROE
top_7 = summary.head(7).sort_values('WROE', ascending=True) # Sort for horiz bar
colors = ['#2ca02c' if x > 0 else '#d62728' for x in top_7['WROE']]

ax1.barh(top_7['WR'], top_7['WROE'], color=colors, edgecolor='black', alpha=0.8)
ax1.set_title("THE ELITE: Top Separators", fontsize=14, fontweight='bold')
ax1.set_xlabel("Win Rate Over Expected (WROE)", fontsize=12)
ax1.axvline(0, color='black', linewidth=1)
ax1.grid(axis='x', alpha=0.3)

# Add value labels
for i, (val, name) in enumerate(zip(top_7['WROE'], top_7['WR'])):
    ax1.text(val + 0.005, i, f"+{val:.1%}", va='center', fontweight='bold', fontsize=11)

# --- Chart 2: The System (Scatter) ---
# Background Zones
x_vals = np.linspace(0, 1, 100)
ax2.fill_between(x_vals, x_vals, 1, color='#e6f5e6', alpha=0.5) # Green
ax2.fill_between(x_vals, 0, x_vals, color='#fdeaea', alpha=0.5) # Red
ax2.plot([0, 1], [0, 1], color='#666666', linestyle='--', linewidth=1.5)

# Scatter (No labels, just distribution)
sns.scatterplot(
    data=summary, 
    x='Avg_Exp_Win_Rate', 
    y='Actual_Win_Rate', 
    size='Reps', 
    sizes=(50, 250), 
    color='#1f77b4', 
    alpha=0.7,
    edgecolor='white',
    legend=False,
    ax=ax2
)

# Text Annotations (Watermarks)
ax2.text(0.05, 0.95, "OVER-PERFORMERS", fontsize=12, fontweight='bold', color='#2ca02c', ha='left', va='top', transform=ax2.transAxes)
ax2.text(0.95, 0.05, "UNDER-PERFORMERS", fontsize=12, fontweight='bold', color='#d62728', ha='right', va='bottom', transform=ax2.transAxes)

# Label Only Top 3 Absolute Outliers on the Scatter (User Request)
summary['Dist'] = summary['Actual_Win_Rate'] - summary['Avg_Exp_Win_Rate']
top_outliers = summary.sort_values('Dist', ascending=False).head(3)

for _, row in top_outliers.iterrows():
    # Offset label slightly up
    ax2.text(row['Avg_Exp_Win_Rate'], row['Actual_Win_Rate'] + 0.02, 
             f"{row['WR']}", 
             ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1a5f1a',
             bbox=dict(facecolor='white', alpha=0.6, pad=0.2, edgecolor='none'))

ax2.set_title("THE DISTRIBUTION: Model Validation", fontsize=14, fontweight='bold')
ax2.set_xlabel("Expected Win Rate", fontsize=12)
ax2.set_ylabel("Actual Win Rate", fontsize=12)
ax2.set_xlim(0, 1)
ax2.set_ylim(0, 1)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "viz_wroe_scatter.png"), dpi=300)
print("Saved scatter plot.")

# B. Context Heatmap (Zone Difficulty)
# Refine bins for labels
# Route Depth: Short (0-5), Intermediate (6-12), Deep (13+)
df['Depth_Bin'] = pd.cut(df['Route_Depth'], bins=[-np.inf, 5, 12, np.inf], labels=['Short\n(0-5y)', 'Intermediate\n(6-12y)', 'Deep\n(13y+)'])

# Break Type Labels
# Soft (<45), Medium (45-90), Hard (>90) - handled by bin_break_angle, but let's re-map for display
df['Break_Display'] = df['Break_Type'].map({
    'Soft': 'Soft\n(<45°)',
    'Medium': 'Medium\n(45-90°)',
    'Hard': 'Hard\n(>90°)'
})

heatmap_data = df.groupby(['Depth_Bin', 'Break_Display'])['Expected_Win_Prob'].mean().unstack()
# Reorder columns if needed, but only use existing ones
desired_order = ['Soft\n(<45°)', 'Medium\n(45-90°)', 'Hard\n(>90°)']
cols_order = [c for c in desired_order if c in heatmap_data.columns]
heatmap_data = heatmap_data[cols_order]

# Update Heatmap Layout: Add Counts
# 1. Calc Counts
counts = df.groupby(['Depth_Bin', 'Break_Display']).size().unstack()
counts = counts[cols_order]

# 2. Create annotation labels: "30%\n(N=12)"
annot_labels = heatmap_data.applymap(lambda x: f"{x:.0%}") 
for i in range(len(heatmap_data)):
    for j in range(len(heatmap_data.columns)):
        val = heatmap_data.iloc[i, j]
        count = counts.iloc[i, j]
        annot_labels.iloc[i, j] = f"{val:.0%}\n(N={count})"

plt.figure(figsize=(10, 7))
ax = sns.heatmap(
    heatmap_data, 
    annot=annot_labels, 
    fmt="",
    cmap='RdYlGn', 
    vmin=0.2, 
    vmax=0.8,
    annot_kws={"size": 11, "weight": "bold", "color": "black"}, # Smaller font
    cbar=False
)

plt.title('Win Rate & Volume by Context', fontsize=16, fontweight='bold', pad=20)
plt.xlabel('Cut Type (Angle)', fontsize=14)
plt.ylabel('Route Depth', fontsize=14)

# Keep the annotation
# Keep the annotation - Update to be factual based on User feedback
# User said: Short is 2nd highest volume and LOWEST win rate.
# Let's dynamically find the max volume and min win rate to annotate correctly or just generic.
# "Deep/Sharp = Low Win Rate" is the key insight.
# "Short/Soft = High Win Rate" (usually).
# Let's remove the specific "Highest Volume" text if it's risky and replace with a Legend-like annotation.

plt.annotate('Deep/Sharp Routes\n= The "Kill Zone"\n(Lowest Win Rates)', 
             xy=(2.5, 2.5), xytext=(1.5, 2.5), # Adjust based on 3x3 grid (0,1,2)
             arrowprops=dict(facecolor='black', shrink=0.05),
             fontsize=12, fontweight='bold', color='black', ha='center')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "viz_context_heatmap.png"), dpi=300)
print("Saved heatmap.")

# C. WROE Leaderboard Bar Chart (Horizontal for Readability)
plt.figure(figsize=(10, 6))

top_wrs = summary.head(5).copy()
top_wrs['Type'] = 'WR'

# DB Calculation
db_summary = df.groupby('DB').agg(
    Reps=('Win', 'count'),
    Allowed_Wins=('Win', 'sum'),
    Exp_Allowed_Wins=('Expected_Win_Prob', 'sum')
).reset_index()
db_summary['Actual_Loss_Rate'] = db_summary['Allowed_Wins'] / db_summary['Reps']
db_summary['Exp_Loss_Rate'] = db_summary['Exp_Allowed_Wins'] / db_summary['Reps']
db_summary['WROE'] = db_summary['Exp_Loss_Rate'] - db_summary['Actual_Loss_Rate']
db_summary = db_summary[db_summary['Reps'] >= 5].sort_values('WROE', ascending=False)

top_dbs = db_summary.head(5).copy()
top_dbs['Type'] = 'DB'
top_dbs.rename(columns={'DB': 'Player'}, inplace=True)
top_wrs.rename(columns={'WR': 'Player'}, inplace=True)

# Combine and Filter for POSITIVE WROE only (User question about -1.2%)
combined = pd.concat([top_wrs[['Player', 'WROE', 'Type', 'Reps']], top_dbs[['Player', 'WROE', 'Type', 'Reps']]])
combined = combined[combined['WROE'] > 0] # Validation: Only show winners
combined = combined.sort_values('WROE', ascending=True) # Sort for Horizontal Bar (Top at top)

# Horizontal Bar Chart
colors = ['#1f77b4' if t == 'WR' else '#d62728' for t in combined['Type']]
plt.barh(combined['Player'], combined['WROE'], color=colors, alpha=0.9, edgecolor='black')

# Labels
for i, (val, reps) in enumerate(zip(combined['WROE'], combined['Reps'])):
    plt.text(val + 0.005, i, f"+{val:.1%}", va='center', fontweight='bold', fontsize=11, color='black')

plt.title('Top Overperformers (WROE > 0)', fontsize=16, fontweight='bold')
plt.xlabel('Win Rate Over Expected', fontsize=14)
# plt.ylabel('Player', fontsize=14) # Names are self-explanatory
plt.axvline(0, color='black', linewidth=1)
plt.xlim(0, combined['WROE'].max() + 0.05) # Add breathing room for labels

# Custom Legend
from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], color='#1f77b4', lw=4, label='WR (Wins vs Exp)'),
                   Line2D([0], [0], color='#d62728', lw=4, label='DB (Prevented vs Exp)')]
plt.legend(handles=legend_elements, loc='lower right')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "viz_wroe_leaderboard.png"), dpi=300)
print("Saved leaderboard.")
