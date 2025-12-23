import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Paths
results_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"
stats_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\shrine_bowl_players_college_stats.csv"
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"

print("Loading data...")
df_res = pd.read_csv(results_path)
df_stats = pd.read_csv(stats_path)

# 1. Feature Engineering: Try to find "Deep Sep" correlation
# Load full results to get Route Depth info
full_df = pd.read_csv(results_path)

# Filter for Deep Routes (>10y)
deep_df = full_df[full_df['Route_Depth'] > 10].copy()

# Metric: Avg Separation on Deep Routes
if deep_df.empty:
    print("No deep routes found.")
    wr_stats = df_res.groupby('WR')['Sep_at_Break'].mean().reset_index()
    wr_stats.rename(columns={'WR': 'player_name', 'Sep_at_Break': 'Avg_Separation'}, inplace=True)
    metric_col = 'Avg_Separation'
    target_col = 'receiving_yards'
    title_text = "Metric Independence (General Sep)"
else:
    wr_stats = deep_df.groupby('WR')['Sep_at_Break'].mean().reset_index()
    wr_stats.rename(columns={'WR': 'player_name', 'Sep_at_Break': 'Deep_Avg_Separation'}, inplace=True)
    metric_col = 'Deep_Avg_Separation'
    target_col = 'yards_per_reception' # Hypothesis: Deep Sep -> High YPR
    title_text = "Context Matters: Deep Sep Translates"

# Merge with College Stats
# Group college stats by player first (summing seasons)
# Calculate YPR manually if needed
cols_to_sum = ['receptions', 'receiving_yards']
available_cols = [c for c in cols_to_sum if c in df_stats.columns]

if len(available_cols) < 2:
    print("Missing receptions or yards columns.")
    exit()

college_production = df_stats.groupby('player_name')[available_cols].sum().reset_index()
# Calculate YPR
college_production['yards_per_reception'] = college_production['receiving_yards'] / college_production['receptions']
college_production['yards_per_reception'] = college_production['yards_per_reception'].fillna(0) # Handle 0 receptions

merged = pd.merge(wr_stats, college_production, on='player_name')

if merged.empty:
    print("No matches.")
    exit()

# Filter for min samples (to reduce noise)
# Count reps
rep_counts = deep_df.groupby('WR').size().reset_index(name='Reps')
rep_counts.rename(columns={'WR': 'player_name'}, inplace=True)
merged = pd.merge(merged, rep_counts, on='player_name')
merged = merged[merged['Reps'] >= 2] # At least 2 deep reps

print(f"Matched {len(merged)} players for correlation.")

# Set style
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

# Plot: Deep Separation vs YPR
plt.figure(figsize=(10, 7))

# Calculate R2
from sklearn.linear_model import LinearRegression
X = merged[metric_col].values.reshape(-1, 1)
y = merged[target_col].values
reg = LinearRegression().fit(X, y)
r2 = reg.score(X, y)

# Color Logic based on R2
plot_color = '#2ca02c' if r2 > 0.1 else '#5D3A9B' 

sns.regplot(data=merged, x=metric_col, y=target_col, 
            color=plot_color, ci=None, scatter_kws={'s': 80, 'alpha': 0.7}, line_kws={'linewidth': 2})

# Annotations
plt.text(0.05, 0.9, f"R² = {r2:.2f}", transform=plt.gca().transAxes, fontsize=14, fontweight='bold', color=plot_color)

# Label Outliers
top_sep = merged.sort_values(metric_col, ascending=False).iloc[0]
top_prod = merged.sort_values(target_col, ascending=False).iloc[0]

labels_to_plot = [top_sep, top_prod]
seen = set()
for row in labels_to_plot:
    if row['player_name'] in seen: continue
    seen.add(row['player_name'])
    plt.text(row[metric_col], row[target_col] + 0.5, row['player_name'], 
             fontsize=10, fontweight='bold', ha='center', color='black')

plt.title(f"{title_text}: Deep Sep vs College YPR", fontsize=16, fontweight='bold', pad=20)
plt.xlabel('Avg Separation on Deep Routes (>10y)', fontsize=13)
plt.ylabel('College Yards Per Reception (YPR)', fontsize=13)

# Remove Descriptive Sidebar text as requested (Redundant with slide bullets)
# plt.subplots_adjust(right=0.8) 
# Text blocks removed.

plt.grid(True, linestyle='--', alpha=0.5)

save_path = os.path.join(output_dir, "viz_correlation.png")
plt.savefig(save_path, dpi=300)
print(f"Saved correlation plot to {save_path}. R2: {r2}")
