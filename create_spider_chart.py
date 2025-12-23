import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import pi
import os

# Settings
results_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"

print("Loading results...")
try:
    df = pd.read_csv(results_path)
except FileNotFoundError:
    print("Files not found.")
    exit()

if 'Break_Angle' not in df.columns:
    print("Break_Angle column missing. Re-run analysis.")
    exit()

# 1. Aggregate Stats per WR
# Filter meaningful reps
df = df[df['Sep_at_Break'] < 10] 

wr_stats = df.groupby('WR').agg(
    Avg_Sep=('Sep_at_Break', 'mean'),
    Max_Speed=('Max_Speed', 'max'),
    Fluidity=('Speed_Maint', 'mean'),
    Sharpness=('Break_Angle', 'mean'),
    Reps=('Sep_at_Break', 'count')
).reset_index()

# Filter low sample size
wr_stats = wr_stats[wr_stats['Reps'] >= 3]

if wr_stats.empty:
    print("Not enough data for spider chart.")
    exit()

# 2. Normalize Stats (0-100 Percentile)
def percentile_rank(col):
    return col.rank(pct=True) * 100

wr_stats['Separation_Pct'] = percentile_rank(wr_stats['Avg_Sep'])
wr_stats['Max_Speed_Pct'] = percentile_rank(wr_stats['Max_Speed'])
wr_stats['Speed_Maint_Pct'] = percentile_rank(wr_stats['Fluidity'])
wr_stats['Break_Angle_Pct'] = percentile_rank(wr_stats['Sharpness'])

# 3. Plot Spider Chart
# Define Categories and Labels
# Mapping to "Scout-speak"
categories = ['Separation_Pct', 'Max_Speed_Pct', 'Speed_Maint_Pct', 'Break_Angle_Pct']
labels = ['Separation\n(Win Rate)', 'Vertical Speed\n(Deep Threat)', 'Change-of\nDirection', 'Break\nSuddenness']

N = len(categories)
angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]

# Choose Players
# Limit to specific intriguing profiles for clarity (Top 3)
target_players = ['Jadon Janke', 'Tahj Washington', 'Lideatrick Griffin']
# Check if they exist, otherwise top 3
available_targets = [p for p in target_players if p in wr_stats['WR'].values]
if len(available_targets) < 3:
    top_performers = wr_stats.sort_values('Separation_Pct', ascending=False).head(3)
else:
    top_performers = wr_stats[wr_stats['WR'].isin(available_targets)]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

# Archetype Labels
archetypes = {
    'Jadon Janke': 'Complete WR',
    'Tahj Washington': 'Speedster',
    'Lideatrick Griffin': 'Route Technician'
}
# Style Config
# Focus on Janke
focus_player = 'Jadon Janke'

for i, (idx, row) in enumerate(top_performers.iterrows()):
    values = row[categories].tolist()
    values += values[:1]
    
    wr_name = row['WR']
    # Defines distinct styles for each player to fix "Gray Overlap" issue
    styles = {
        'Jadon Janke': {'color': '#1f77b4', 'ls': '-', 'lw': 3, 'label': 'Jadon Janke\n(Elite)'}, # Blue Solid
        'Tahj Washington': {'color': '#d62728', 'ls': '--', 'lw': 2, 'label': 'Tahj Washington\n(Speedster)'}, # Red Dashed
        'Lideatrick Griffin': {'color': '#2ca02c', 'ls': ':', 'lw': 2, 'label': 'Lideatrick Griffin\n(Technician)'} # Green Dotted
    }
    
    style = styles.get(wr_name, {'color': 'gray', 'ls': '-', 'lw': 1, 'label': wr_name})
    
    ax.plot(angles, values, linewidth=style['lw'], linestyle=style['ls'], label=style['label'], color=style['color'], alpha=0.9)
    if wr_name == 'Jadon Janke':
        ax.fill(angles, values, color=style['color'], alpha=0.15)

# Setup Axes
ax.set_theta_offset(pi / 2)
ax.set_theta_direction(-1)

plt.xticks(angles[:-1], labels, size=12, weight='bold')

# Y-Tick Labels (Percentiles)
ax.set_rlabel_position(0)
plt.yticks([25, 50, 75], ["25", "50", "75"], color="grey", size=10)
plt.ylim(0, 100)

# Legend - Move to top right but cleaner
plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1.0), fontsize=9, title="Player (Style)")

plt.title("Player Style Profiles\n(Metric Percentiles)", size=14, weight='bold', y=1.05)

# Add Style Table to the right (Manual Table)
# Positioning depends on Figure size. Let's rely on standard legend + maybe text below.
# Actually, simpler is better.
# Just use the Legend properly labeled.

plt.subplots_adjust(right=0.7) # Make room for legend/text on right

# Restore Descriptions (Color-Coded to match Lines)
# Janke (Blue) - Moved Up & Simplified as requested
plt.figtext(0.82, 0.65, "Jadon Janke:\nElite Separator", 
            fontsize=9, ha='center', fontweight='bold', color='#1f77b4',
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='#1f77b4', boxstyle='round,pad=0.5'))

# Washington (Red)
plt.figtext(0.82, 0.35, "Tahj Washington:\nSpeedster\n(Elite Vertical, Avg Cuts)", 
            fontsize=9, ha='center', fontweight='bold', color='#d62728',
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='#d62728', boxstyle='round,pad=0.5'))

# Griffin (Green)
plt.figtext(0.82, 0.2, "Lideatrick Griffin:\nTechnician\n(Elite Cuts, Avg Speed)", 
            fontsize=9, ha='center', fontweight='bold', color='#2ca02c',
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='#2ca02c', boxstyle='round,pad=0.5'))

plt.subplots_adjust(right=0.75)

output_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\viz_spider.png"
# plt.tight_layout() # Conflict with subplot_adjust
plt.savefig(output_path, dpi=300)
print(f"Saved spider chart to {output_path}")
print("Featured Players:", top_performers['WR'].tolist())
