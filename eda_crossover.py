import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Load data
file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\crossover_matched.csv"
print("Loading data...")
df = pd.read_csv(file_path)

print(f"Total rows: {len(df)}")
print("Columns:", df.columns.tolist())

# 1. Inspect Plays (Session IDs)
# We need to distinct "reps". Usually 'session_id' or time gaps define a rep.
# Let's count rows per session_id + player to see duration.
print("\nUnique Session IDs:", df['session_id'].nunique())
df['ts'] = pd.to_datetime(df['ts'])

# Group by session and player to get start/end times
play_stats = df.groupby(['session_id', 'player_name']).agg(
    start_time=('ts', 'min'),
    end_time=('ts', 'max'),
    num_frames=('ts', 'count')
).reset_index()

play_stats['duration'] = (play_stats['end_time'] - play_stats['start_time']).dt.total_seconds()

print("\nPlay Duration Stats (seconds):")
print(play_stats['duration'].describe())

# 2. Visualize one Session
# Pick a session with at least 2 players (WR and DB)
# Let's find a session with a WR and a DB
sessions_with_wr_db = []
for session, group in df.groupby('session_id'):
    positions = group['position'].unique()
    has_wr = any('WR' in pos for pos in positions)
    has_db = any(pos in ['CB', 'S', 'DB', 'DS', 'FS', 'SS'] for pos in positions)
    if has_wr and has_db:
        sessions_with_wr_db.append(session)
        if len(sessions_with_wr_db) >= 1: # Just need one for now
            break

if sessions_with_wr_db:
    target_session = sessions_with_wr_db[0]
    print(f"\nVisualizing Session: {target_session}")
    
    session_data = df[df['session_id'] == target_session]
    
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=session_data, x='x', y='y', hue='position', style='player_name', s=10)
    plt.title(f"Trajectories for Session {target_session}")
    plt.xlabel("X (yards)")
    plt.ylabel("Y (yards)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.axis('equal') # Field proportions
    
    # Save plot
    plt.savefig(r"C:\Users\16476\OneDrive\Desktop\ss_sbc\session_plot.png")
    print("Saved plot to session_plot.png")
    
    # Print data for this session
    print(session_data[['player_name', 'position', 'x', 'y', 's', 'a', 'ts']].head(10))
else:
    print("Could not find a session with both WR and DB.")
