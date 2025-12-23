import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.effects as effects
import os
import numpy as np

# Settings
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"
data_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\team_1_matched.csv"
analysis_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"

def set_style():
    plt.style.use('dark_background')
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Roboto', 'DejaVu Sans'],
        'figure.dpi': 300,
        'axes.facecolor': '#1a1a1a', # Slightly lighter dark
        'figure.facecolor': '#1a1a1a'
    })

def create_pro_trace_viz():
    print("Loading data...")
    df_full = pd.read_csv(data_path)
    df_full['ts'] = pd.to_datetime(df_full['ts'])
    df_res = pd.read_csv(analysis_path)
    
    # 1. Filter for a "Double Move" or Complex Route (High Angle + Delay?)
    # Or just a REALLY deep sharp cut (The "Post" or "Corner")
    # Angle > 90 AND Depth > 12 AND Sep > 2.0
    valid_reps = df_res[
        (df_res['Break_Angle'] > 100) & 
        (df_res['Route_Depth'] > 10) &
        (df_res['Sep_at_Break'] > 2.0)
    ].sort_values('Sep_at_Break', ascending=False)
    
    if valid_reps.empty:
        # Fallback to just Sharp Angle
        valid_reps = df_res[df_res['Break_Angle'] > 110].sort_values('Sep_at_Break', ascending=False)
        
    best_rep = valid_reps.iloc[0]
    wr_name = best_rep['WR']
    db_name = best_rep['DB']
    break_time = pd.to_datetime(best_rep['Break_Time'])
    
    # 2. Extract Data - FULL HISTORY (Show the Release!)
    # Go back 3.5 seconds to capture the start of the rep
    start_time = break_time - pd.Timedelta(seconds=3.5)
    end_time = break_time + pd.Timedelta(seconds=0.8)
    
    subset = df_full[
        (df_full['ts'] >= start_time) & 
        (df_full['ts'] <= end_time) & 
        (df_full['player_name'].isin([wr_name, db_name]))
    ].copy()
    
    # Check if we have enough data, strict filter might clip start
    if subset.empty:
        start_time = break_time - pd.Timedelta(seconds=2.0)
        subset = df_full[(df_full['ts'] >= start_time) & (df_full['ts'] <= end_time) & (df_full['player_name'].isin([wr_name, db_name]))]

    # 3. Moment of Truth
    moment = break_time + pd.Timedelta(seconds=0.5)
    available_ts = subset['ts'].unique()
    closest_ts = min(available_ts, key=lambda x: abs(x - moment))
    current_data = subset[subset['ts'] == closest_ts]
    
    # 4. Plot - "Pro Trace" Style
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # A. Field (Subtle Grid)
    x_min, x_max = subset['x'].min(), subset['x'].max()
    y_min, y_max = subset['y'].min(), subset['y'].max()
    
    start_yard = int(x_min // 5) * 5
    end_yard = int(x_max // 5) * 5 + 5
    for x in range(start_yard, end_yard + 5, 5):
        ax.axvline(x, color='#ccffcc', linewidth=0.5, zorder=1, alpha=0.3) # Matrix Greenish
        # Numbers
        ax.text(x, y_min + 1, str(int(x)), color='#ccffcc', fontsize=10, ha='center', alpha=0.3)

    # B. Trails - SOLID and LONG
    # WR: Electric Blue, DB: Hot Pink
    c_wr = '#00E5FF'
    c_db = '#FF4081'
    
    for player, color, label in [(wr_name, c_wr, 'WR'), (db_name, c_db, 'DB')]:
        player_path = subset[
            (subset['player_name'] == player) & 
            (subset['ts'] <= closest_ts)
        ].sort_values('ts')
        
        # Draw the FULL path as a slightly transparent thick line (The History)
        ax.plot(player_path['x'], player_path['y'], color=color, linewidth=2, alpha=0.4, linestyle='-', zorder=2)
        
        # Draw the "Recent" path (last 1s) as solid bright
        recent_path = player_path[player_path['ts'] > (closest_ts - pd.Timedelta(seconds=1.0))]
        ax.plot(recent_path['x'], recent_path['y'], color=color, linewidth=4, alpha=1.0, zorder=3)
        
        # Draw "Ghost Nodes" every 0.5s to show speed/position over time
        # Timestamps are frequent (0.1s). Plot every 5th point.
        points = player_path.iloc[::5]
        ax.scatter(points['x'], points['y'], color=color, s=20, alpha=0.6, zorder=3)

    # C. Current Positions
    wr_pos = current_data[current_data['player_name'] == wr_name].iloc[0]
    db_pos = current_data[current_data['player_name'] == db_name].iloc[0]
    
    # Detailed Markers
    for p_pos, c, l in [(wr_pos, c_wr, 'WR'), (db_pos, c_db, 'DB')]:
        ax.scatter(p_pos['x'], p_pos['y'], color=c, s=400, edgecolor='white', linewidth=2, zorder=10)
        ax.text(p_pos['x'], p_pos['y'] + 1.2, l, color=c, fontweight='bold', ha='center', fontsize=12)

    # D. Separation 
    mid_x = (wr_pos['x'] + db_pos['x']) / 2
    mid_y = (wr_pos['y'] + db_pos['y']) / 2
    dist = np.sqrt((wr_pos['x'] - db_pos['x'])**2 + (wr_pos['y'] - db_pos['y'])**2)
    
    ax.plot([wr_pos['x'], db_pos['x']], [wr_pos['y'], db_pos['y']], 
            color='white', linestyle='--', linewidth=1.5, zorder=9)
    
    ax.text(mid_x, mid_y, f"{dist:.2f} yds", 
            ha='center', va='center', fontsize=11, fontweight='bold', color='black',
            bbox=dict(facecolor='#00E5FF', edgecolor='white', boxstyle='round,pad=0.3', alpha=1.0))

    # E. Annotate Break Point (The "Move")
    # Find break time in path
    try:
        break_pt = subset[subset['ts'] == min(available_ts, key=lambda x: abs(x - break_time))].iloc[0]
        # Just use WR break point
        if break_pt['player_name'] == db_name: 
             # Find WR in same frame
             break_pt = subset[(subset['ts'] == break_pt['ts']) & (subset['player_name'] == wr_name)].iloc[0]
             
        ax.scatter(break_pt['x'], break_pt['y'], color='yellow', marker='x', s=200, linewidth=3, zorder=11)
        ax.text(break_pt['x'], break_pt['y'] - 1.5, "BREAK\nPOINT", color='yellow', ha='center', fontsize=10, fontweight='bold')
    except:
        pass

    ax.set_title(f"TRACE: {best_rep['Break_Type'].upper()} | DEPTH: {best_rep['Route_Depth']:.1f}y", 
                 fontsize=16, fontweight='bold', color='white')
    
    # Zoom to fit path
    path_min_x = subset['x'].min()
    path_max_x = subset['x'].max()
    center_y = (subset['y'].min() + subset['y'].max()) / 2
    
    # Ensure aspect ratio is reasonable
    width = path_max_x - path_min_x
    if width < 15: width = 15
    
    ax.set_xlim(path_min_x - 2, path_min_x + width + 2)
    ax.set_ylim(center_y - (width/2 * 0.6), center_y + (width/2 * 0.6))            
    ax.axis('off')
    
    plt.tight_layout()
    save_path = os.path.join(output_dir, "viz_play_anim_static.png")
    plt.savefig(save_path, facecolor='#1a1a1a')
    print(f"Saved pro trace visual to {save_path}")

if __name__ == "__main__":
    set_style()
    create_pro_trace_viz()
