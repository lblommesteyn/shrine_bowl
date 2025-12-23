import pandas as pd
import numpy as np

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\concurrent_sample.csv"
print("Loading data...")
df = pd.read_csv(file_path)
df['ts'] = pd.to_datetime(df['ts'])

defenders = df[df['position'].isin(['DC', 'DS', 'CB', 'S', 'DB', 'FS', 'SS'])]
receivers = df[df['position'] == 'WR']

print(f"Receivers: {len(receivers['player_name'].unique())}")
print(f"Defenders: {len(defenders['player_name'].unique())}")

results = []

for wr_name in receivers['player_name'].unique():
    wr_data = receivers[receivers['player_name'] == wr_name].sort_values('ts')
    
    # 1. Check if WR is moving (filter out static players)
    max_speed = wr_data['s'].max()
    if max_speed < 3.0: # 3 yds/s ~ 6 mph
        print(f"Skipping {wr_name} (Max speed {max_speed:.2f} < 3.0)")
        continue

    best_db_name = None
    min_avg_dist = float('inf')
    best_merged = None
    
    start_time = wr_data['ts'].min()
    end_time = wr_data['ts'].max()
    
    # Find overlapping defenders
    potential_dbs_df = defenders[
        (defenders['ts'] >= start_time) & 
        (defenders['ts'] <= end_time)
    ]
    potential_dbs = potential_dbs_df['player_name'].unique()
    
    if len(potential_dbs) == 0:
        print(f"No overlapping defenders for {wr_name}")
        continue
        
    for db_name in potential_dbs:
        db_data = defenders[defenders['player_name'] == db_name].sort_values('ts')
        
        # Merge
        merged = pd.merge_asof(wr_data, db_data, on='ts', suffixes=('_wr', '_db'), direction='nearest', tolerance=pd.Timedelta('0.1s'))
        # Filter for valid matches (where db data was found)
        merged = merged.dropna(subset=['x_db'])
        
        if merged.empty:
            continue
            
        merged['separation'] = np.sqrt((merged['x_wr'] - merged['x_db'])**2 + (merged['y_wr'] - merged['y_db'])**2)
        avg_sep = merged['separation'].mean()
        
        if avg_sep < min_avg_dist:
            min_avg_dist = avg_sep
            best_db_name = db_name
            best_merged = merged
            
    if best_db_name:
        # Detect Break
        # Calculate change in dir
        wr_data['dir_diff'] = wr_data['dir'].diff().abs()
        wr_data['dir_diff'] = wr_data['dir_diff'].apply(lambda x: 360 - x if x > 180 else x)
        wr_data['dir_diff_smooth'] = wr_data['dir_diff'].rolling(5).mean()
        
        # Valid break: speed > 3.0
        potential_breaks = wr_data[wr_data['s'] > 3.0]
        
        if not potential_breaks.empty:
            break_idx = potential_breaks['dir_diff_smooth'].idxmax()
            break_time = wr_data.loc[break_idx, 'ts']
            
            # Check if break_time is scalar or series (if duplicate index)
            if isinstance(break_time, pd.Series):
                 break_time = break_time.iloc[0]
            
            # Get separation at break time
            # Look in best_merged
            sep_row = best_merged[best_merged['ts'] == break_time]
            
            if not sep_row.empty:
                sep_at_break = sep_row['separation'].iloc[0]
            else:
                sep_at_break = np.nan
                print(f"Break time {break_time} not found in merged data for {wr_name} vs {best_db_name}")
            
            speed_maint = wr_data.loc[break_idx, 's'] / max_speed if max_speed > 0 else 0
            # Handle duplicate index if loc returns series
            if isinstance(speed_maint, pd.Series):
                speed_maint = speed_maint.iloc[0]
            
            results.append({
                'WR': wr_name,
                'DB': best_db_name,
                'Avg_Sep': min_avg_dist,
                'Sep_at_Break': sep_at_break,
                'Speed_Maint': speed_maint,
                'Break_Time': break_time
            })
            print(f"Success: {wr_name} vs {best_db_name}, Sep: {sep_at_break}")
        else:
            print(f"No valid break found for {wr_name}")
    else:
        print(f"No matching DB found for {wr_name}")

print("\nResults:")
print(pd.DataFrame(results))
