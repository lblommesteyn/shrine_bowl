import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np # Added for quadrant calculation
import ast

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
        'legend.fontsize': 10,
        'legend.title_fontsize': 11,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.color': '#cccccc'
    })

set_clean_style()

# Paths
results_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"

print("Loading results...")
df = pd.read_csv(results_path)
print(f"Data Loaded: {len(df)} rows")

if df.empty:
    print("No data.")
    exit()

# 1. Bar Chart: All Receivers (WR/TE/RB)
plt.figure(figsize=(12, 8))
# Filter for min 1 rep
qualified = df.groupby('WR').size()
qualified_names = qualified[qualified >= 1].index

avg_sep = df[df['WR'].isin(qualified_names)].groupby('WR')['Sep_at_Break'].mean().sort_values(ascending=False)

sns.barplot(x=avg_sep.values, y=avg_sep.index, palette='magma')

plt.title(f'Separation Efficiency: Avg Separation at Break (n={len(avg_sep)})', fontsize=14, fontweight='bold')
plt.xlabel('Avg Separation (yards)', fontsize=12)
plt.ylabel('Receiver', fontsize=12)
plt.tight_layout()

save_path_bar = os.path.join(output_dir, "viz_bar.png")
plt.savefig(save_path_bar)
print(f"Saved bar chart to {save_path_bar}")

# 2. Metric Explainer: Separation vs Time (Physical Viz)
sample_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\sample_rep_trace.csv"
if os.path.exists(sample_path):
    rep_df = pd.read_csv(sample_path)
    # Smooth separation
    rep_df['sep_smooth'] = rep_df['separation'].rolling(window=5, center=True).mean()
    
    plt.figure(figsize=(10, 5))
    
    # Identify a "Break" point
    # Synthetic data is centered on 0.0 as the break
    break_time = 0.0
    
    # Plot curve
    sns.lineplot(data=rep_df, x='time', y='sep_smooth', linewidth=3, color='#1f77b4')
    
    # Add vertical line at Break
    plt.axvline(x=break_time, color='red', linestyle='--', linewidth=2, label='Break Point (t=0)')
    
    # Annotate Sep at Break
    sep_at_break = rep_df[rep_df['time'] >= break_time]['sep_smooth'].iloc[0]
    plt.plot(break_time, sep_at_break, 'ro', markersize=10)
    plt.text(break_time + 0.1, sep_at_break, f"Sep @ Break\n{sep_at_break:.1f} yds", 
             color='red', fontweight='bold', fontsize=12)
    
    # Annotate Closing Burst (+1s)
    burst_time = break_time + 1.0
    if burst_time <= rep_df['time'].max():
        sep_burst = rep_df[rep_df['time'] >= burst_time]['sep_smooth'].iloc[0]
        plt.plot(burst_time, sep_burst, 'ko', markersize=10)
        plt.text(burst_time + 0.1, sep_burst, f"Sep @ +1s\n{sep_burst:.1f} yds", 
                 color='black', fontweight='bold', fontsize=12)
        
        # Arrow for burst
        plt.annotate('', xy=(burst_time, sep_burst), xytext=(break_time, sep_at_break),
                     arrowprops=dict(arrowstyle="->", color="gray", linestyle="dashed"))
        plt.text((break_time+burst_time)/2, (sep_at_break+sep_burst)/2 - 0.5, "Closing Burst\n(DB Recovery)", 
                 ha='center', color='gray', fontsize=10)

    plt.title('Separation Efficiency: The Physical Metric', fontsize=16, fontweight='bold')
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Separation (yards)', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    save_path_explainer = os.path.join(output_dir, "viz_metric_explainer.png")
    plt.savefig(save_path_explainer)
    print(f"Saved metric explainer to {save_path_explainer}")
else:
    print("Sample rep trace not found, skipping metric explainer.")

# 3. Closing Burst (Recovery) Scatter
# X: Sep @ Break, Y: Closing Burst
plt.figure(figsize=(10, 6))

# 3. Enhanced Closing Burst Scatter (Hybrid: Raw Reps + Player Averages)
plt.figure(figsize=(12, 9))

# Filter to qualified DBs only
burst_df = df[(df['Closing_Burst'].abs() < 10) & (df['Sep_at_Break'] < 10)].copy()

# A. Plot Background Raw Reps
sns.scatterplot(data=burst_df, x='Sep_at_Break', y='Closing_Burst', 
                color='gray', alpha=0.15, s=20, linewidth=0, zorder=1)

# B. Calculate and Plot Player Averages
db_agg = burst_df.groupby('DB').agg(
    Avg_Sep=('Sep_at_Break', 'mean'),
    Avg_Burst=('Closing_Burst', 'mean'),
    Reps=('Sep_at_Break', 'count')
).reset_index()

# Filter for min reps
db_agg = db_agg[db_agg['Reps'] >= 3]

# Define Quadrants for color
def get_quadrant(row):
    if row['Avg_Sep'] < 2.0:
        return 'Lockdown' if row['Avg_Burst'] > 0 else 'Lost Step'
    else:
        return 'Recovery' if row['Avg_Burst'] > 0 else 'Blown'

db_agg['Type'] = db_agg.apply(get_quadrant, axis=1)

# Plot Averages
# Highlight Beanie Bishop specifically
is_bishop = db_agg['DB'] == 'Beanie Bishop'
others = db_agg[~is_bishop]
bishop = db_agg[is_bishop]

# Plot Others
sns.scatterplot(data=others, x='Avg_Sep', y='Avg_Burst', 
                hue='Type', style='Type', s=150, palette='Set1', edgecolor='white', linewidth=1.5, zorder=10, legend=False)

# Plot Bishop (Bigger, Highlighted)
if not bishop.empty:
    plt.scatter(bishop['Avg_Sep'], bishop['Avg_Burst'], s=400, color='gold', edgecolor='black', marker='*', zorder=20, label='Beanie Bishop')

# Add Quadrant Lines
plt.axhline(y=0, color='black', linestyle='-', linewidth=2, zorder=5)
plt.axvline(x=2, color='black', linestyle='-', linewidth=2, zorder=5)

# Add Quadrant Labels (Bold, Inside Box)
# Add Quadrant Labels (Clean & Minimal)
props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='#dddddd')
plt.text(1.0, 1.5, "LOCKDOWN", fontsize=14, fontweight='bold', color='#2ca02c', ha='center', bbox=props)
plt.text(3.0, 1.5, "RECOVERY", fontsize=14, fontweight='bold', color='#1f77b4', ha='center', bbox=props)
plt.text(1.0, -1.5, "SOLID", fontsize=14, fontweight='bold', color='gray', ha='center', bbox=props)
plt.text(3.0, -1.5, "GAP CONTROL", fontsize=14, fontweight='bold', color='#d62728', ha='center', bbox=props) # Renamed from BLOWN

# Label Players (Less Clutter)
texts = []
for i, row in others.iterrows():
    # Smart Quadrant Labeling (Outliers per Section)
    # Define Center
    center_x = others['Avg_Sep'].mean()
    center_y = others['Avg_Burst'].mean()
    
    # Assign Quadrants
    # Q1: High Sep, High Burst (Recovery)
    # Q2: Low Sep, High Burst (Lockdown - The Best)
    # Q3: Low Sep, Low Burst (Sticky/Physical)
    # Q4: High Sep, Low Burst (Lost)
    
    others['dx'] = others['Avg_Sep'] - center_x
    others['dy'] = others['Avg_Burst'] - center_y
    others['Dist'] = np.sqrt(others['dx']**2 + others['dy']**2)
    
    def get_quadrant(row):
        if row['dx'] >= 0 and row['dy'] >= 0: return 'Q1'
        if row['dx'] < 0 and row['dy'] >= 0: return 'Q2'
        if row['dx'] < 0 and row['dy'] < 0: return 'Q3'
        return 'Q4'

    others['Quad'] = others.apply(get_quadrant, axis=1)
    
    # Pick Top 2 Outliers per Quadrant
    labels_to_plot = []
    
    for q in ['Q1', 'Q2', 'Q3', 'Q4']:
        top_in_quad = others[others['Quad'] == q].sort_values('Dist', ascending=False).head(2)
        labels_to_plot.extend(top_in_quad.to_dict('records'))
        
    for row in labels_to_plot:
         try: # Handle potential duplicate indices or dict/df mismatch if needed, though dict is safe
             plt.text(row['Avg_Sep'], row['Avg_Burst']+0.1, row['DB'], fontsize=9, fontweight='bold', ha='center',
                     bbox=dict(facecolor='white', alpha=0.6, pad=0.2, edgecolor='none'))
         except:
             pass

# Label Bishop
if not bishop.empty:
     plt.text(bishop['Avg_Sep'].iloc[0], bishop['Avg_Burst'].iloc[0] + 0.35, "Beanie Bishop\n(Prototype)", 
             fontsize=11, fontweight='bold', ha='center', color='black',
             bbox=dict(facecolor='#FFD700', alpha=0.4, edgecolor='black'))

plt.title('Defender Archetypes: Recovery vs Lockdown', fontsize=16, fontweight='bold', pad=15)
plt.xlabel('Initial Separation (yards)', fontsize=14, fontweight='bold')
plt.ylabel('Closing Speed (yds closed/sec)', fontsize=14, fontweight='bold')

# ADD DISTRIBUTION BAR (Bottom)
# Create a new axes at the bottom
# We'll just save this and make a separate small chart or composite it?
# Use subplots? 
# Let's adjust layout to put bar at bottom.
# Actually, let's just create a separate "Defender Distribution" bar chart 
# and the user can place it in the slide if they want, OR overlay it.
# Overlaying is hard with matplotlib spacing.
# Let's Save this main chart, then Create a separate small descriptive bar chart.

plt.tight_layout()
save_path_burst = os.path.join(output_dir, "viz_burst.png") 
plt.savefig(save_path_burst)
print(f"Saved hybrid burst plot to {save_path_burst}")

# Defender Distribution Chart
plt.figure(figsize=(10, 2))
counts = db_agg['Type'].value_counts()
total = len(db_agg)
# Order: Lockdown, Recovery, Boring, Blown
order = ['Lockdown', 'Recovery', 'Lost Step', 'Blown']
# Map to colors
color_map = {'Lockdown': 'green', 'Recovery': 'blue', 'Lost Step': 'gray', 'Blown': 'red'}

# Prepare data for stacked bar
ratios = [counts.get(k, 0)/total for k in order]
labels_dist = [f"{k}\n({v/total:.0%})" for k, v in zip(order, [counts.get(x,0) for x in order])]

left = 0
for r, color, label in zip(ratios, [color_map[k] for k in order], labels_dist):
    plt.barh(0, r, left=left, color=color, edgecolor='white', height=0.5)
    if r > 0.05: # Only label if visible
        plt.text(left + r/2, 0, label, ha='center', va='center', color='white', fontweight='bold', fontsize=10)
    left += r

plt.title("Distribution of Defender Styles", fontsize=12, fontweight='bold')
plt.axis('off')
plt.tight_layout()
save_path_burst_dist = os.path.join(output_dir, "viz_burst_dist.png")
plt.savefig(save_path_burst_dist)
print(f"Saved burst distribution to {save_path_burst_dist}")
