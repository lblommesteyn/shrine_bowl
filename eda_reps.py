import pandas as pd
import numpy as np

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\skill_1on1_matched.csv"
print("Loading data...")
df = pd.read_csv(file_path)

print("Unique Positions:", df['position'].unique())
print("Unique Session IDs:", df['session_id'].unique())

# Sort by time
df['ts'] = pd.to_datetime(df['ts'])
df = df.sort_values(['player_name', 'ts'])

# Identify gaps (e.g., > 5 seconds) to define new reps for a player
df['time_diff'] = df.groupby('player_name')['ts'].diff().dt.total_seconds()
gap_threshold = 5.0 
df['new_rep'] = df['time_diff'] > gap_threshold

# Create rep_id per player
df['player_rep_id'] = df.groupby('player_name')['new_rep'].cumsum()

print("\nRep Stats per Player:")
rep_counts = df.groupby(['player_name', 'position'])['player_rep_id'].max()
print(rep_counts.describe())
print(rep_counts.head())

# Now we need to align these reps across players to find "Shared Reps" (1v1s)
# A shared rep is when two players are active at the same time.
# Let's bin time into 1-second intervals and count active players per position group.

df['time_bin'] = df['ts'].dt.floor('1s')
active_per_bin = df.groupby(['time_bin', 'position']).size().unstack(fill_value=0)

# Define groups
valid_wr = [p for p in active_per_bin.columns if 'WR' in p]
valid_db = [p for p in active_per_bin.columns if p in ['CB', 'S', 'DB', 'DS', 'FS', 'SS']]

print(f"\nValid WR cols: {valid_wr}")
print(f"Valid DB cols: {valid_db}")

if valid_wr and valid_db:
    active_per_bin['wr_count'] = active_per_bin[valid_wr].sum(axis=1)
    active_per_bin['db_count'] = active_per_bin[valid_db].sum(axis=1)
    
    # Find active times where both groups are present
    concurrent_active = active_per_bin[(active_per_bin['wr_count'] > 0) & (active_per_bin['db_count'] > 0)]
    print(f"\nTime bins with concurrent WR and DB activity: {len(concurrent_active)}")
    
    if not concurrent_active.empty:
        print(concurrent_active.head())
        
        # Pick a start time from the first concurrent activity
        sample_time = concurrent_active.index[0]
        print(f"\nSample Time: {sample_time}")
        
        # Extract 10 seconds of data around this time
        start_window = sample_time
        end_window = sample_time + pd.Timedelta(seconds=10)
        
        sample_df = df[(df['ts'] >= start_window) & (df['ts'] <= end_window)]
        print(f"Sample Data Rows: {len(sample_df)}")
        print("Players in sample:", sample_df['player_name'].unique())
        
        sample_df.to_csv(r"C:\Users\16476\OneDrive\Desktop\ss_sbc\concurrent_sample.csv")
        print("Saved concurrent sample to concurrent_sample.csv")
else:
    print("No WR or DB columns found in pivot.")
