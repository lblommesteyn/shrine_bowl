import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os

# Settings
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"
data_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\team_1_matched.csv"
analysis_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"

print("Loading data...")
df_full = pd.read_csv(data_path)
df_full['ts'] = pd.to_datetime(df_full['ts'])

df_res = pd.read_csv(analysis_path)

# Find a "Tight Coverage" Rep (Separation between 0.5 and 2.5 yards)
# This looks more like actual defending than a 15-yard bust.
valid_reps = df_res[(df_res['Sep_at_Break'] > 0.5) & (df_res['Sep_at_Break'] < 2.5)].sort_values('Sep_at_Break', ascending=True)
if valid_reps.empty:
    print("No tight coverage reps found. widening search...")
    valid_reps = df_res[df_res['Sep_at_Break'] < 5.0].sort_values('Sep_at_Break', ascending=True)
if valid_reps.empty:
    print("No valid reps found.")
    exit()

best_rep = valid_reps.iloc[0]
wr_name = best_rep['WR']
db_name = best_rep['DB']
break_time = pd.to_datetime(best_rep['Break_Time'])

print(f"Animating Rep: {wr_name} vs {db_name} around {break_time}")

# Extract 5 seconds around break time
start_time = break_time - pd.Timedelta(seconds=2)
end_time = break_time + pd.Timedelta(seconds=2)

subset = df_full[
    (df_full['ts'] >= start_time) & 
    (df_full['ts'] <= end_time) & 
    (df_full['player_name'].isin([wr_name, db_name]))
].copy()

# Animation
fig, ax = plt.subplots(figsize=(10, 6))

def update(frame_time):
    ax.clear()
    
    # Frame Data
    current_data = subset[subset['ts'] == frame_time]
    
    # Static Background (approx field)
    ax.set_xlim(subset['x'].min() - 5, subset['x'].max() + 5)
    ax.set_ylim(subset['y'].min() - 5, subset['y'].max() + 5)
    ax.set_title(f"{wr_name} vs {db_name}\nTime: {frame_time.time()}", fontsize=14)
    ax.set_xlabel("Yards")
    ax.set_ylabel("Yards")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # Plot Players
    for _, row in current_data.iterrows():
        color = 'blue' if row['player_name'] == wr_name else 'red'
        ax.scatter(row['x'], row['y'], c=color, s=200, label=row['position'], edgecolors='black')
        # Add buffer to seeing the "pairing"
        ax.plot([row['x'], row['x']], [row['y'], row['y']], c='gray', alpha=0.1) 

    # Draw line between them to show the pairing
    if len(current_data) == 2:
        p1 = current_data.iloc[0]
        p2 = current_data.iloc[1]
        dist = ((p1['x']-p2['x'])**2 + (p1['y']-p2['y'])**2)**0.5
        ax.plot([p1['x'], p2['x']], [p1['y'], p2['y']], 'k--', alpha=0.5, label=f"Sep: {dist:.1f}y")
        
    ax.legend(loc='upper right')

# Get unique timestamps for frames
timestamps = sorted(subset['ts'].unique())

ani = animation.FuncAnimation(fig, update, frames=timestamps, interval=100)

save_path = os.path.join(output_dir, "viz_play_anim.gif")
ani.save(save_path, writer='pillow', fps=10)
print(f"Saved animation to {save_path}")
