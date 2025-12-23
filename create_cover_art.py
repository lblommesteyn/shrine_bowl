import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Settings
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"
data_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\team_1_matched.csv"
analysis_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"

def set_style():
    plt.style.use('dark_background')
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'figure.dpi': 300,
        'axes.facecolor': '#000000', # Pure black for cover
        'figure.facecolor': '#000000'
    })

def create_cover_art():
    print("Generating Cover Art...")
    if not os.path.exists(data_path):
        print("Data not found.")
        return

    df_full = pd.read_csv(data_path)
    df_full['ts'] = pd.to_datetime(df_full['ts'])
    df_res = pd.read_csv(analysis_path)
    
    # Pick the best "Visual" rep (High separation, sharp cut)
    valid_reps = df_res[
        (df_res['Break_Angle'] > 90) & 
        (df_res['Route_Depth'] > 12)
    ].sort_values('Sep_at_Break', ascending=False)
    
    if valid_reps.empty:
         valid_reps = df_res.sort_values('Sep_at_Break', ascending=False)

    best_rep = valid_reps.iloc[0]
    wr_name = best_rep['WR']
    db_name = best_rep['DB']
    break_time = pd.to_datetime(best_rep['Break_Time'])
    
    # Get a long window (2.5s) to show the full route development
    start_time = break_time - pd.Timedelta(seconds=2.0)
    end_time = break_time + pd.Timedelta(seconds=0.5)
    
    subset = df_full[
        (df_full['ts'] >= start_time) & 
        (df_full['ts'] <= end_time) & 
        (df_full['player_name'].isin([wr_name, db_name]))
    ].copy()
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Flatten time to 0-1 range for alpha
    subset['time_norm'] = (subset['ts'] - start_time).dt.total_seconds()
    duration = (end_time - start_time).total_seconds()
    subset['alpha'] = subset['time_norm'] / duration
    subset['alpha'] = subset['alpha'].clip(0.1, 1.0) # Min alpha 0.1
    
    # Plot WR (Cyan)
    wr_path = subset[subset['player_name'] == wr_name].sort_values('ts')
    ax.scatter(wr_path['x'], wr_path['y'], c='#00FFFF', s=100, alpha=wr_path['alpha'].values, edgecolors='none')
    
    # Plot DB (Magenta)
    db_path = subset[subset['player_name'] == db_name].sort_values('ts')
    ax.scatter(db_path['x'], db_path['y'], c='#FF00FF', s=100, alpha=db_path['alpha'].values, edgecolors='none')
    
    # Clean up (No Axis, No Text)
    ax.axis('off')
    
    # Zoom nicely
    x_min, x_max = subset['x'].min(), subset['x'].max()
    y_min, y_max = subset['y'].min(), subset['y'].max()
    margin = 5
    ax.set_xlim(x_min - margin, x_max + margin)
    ax.set_ylim(y_min - margin, y_max + margin)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "viz_cover_art.png")
    plt.savefig(save_path, facecolor='#000000', bbox_inches='tight', pad_inches=0)
    print(f"Saved cover art to {save_path}")

if __name__ == "__main__":
    set_style()
    create_cover_art()
