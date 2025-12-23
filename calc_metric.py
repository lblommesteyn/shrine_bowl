import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\concurrent_sample.csv"
print("Loading data...")
df = pd.read_csv(file_path)
df['ts'] = pd.to_datetime(df['ts'])

# Filter relevant positions
# Note: 'DC', 'DS', 'CB', 'S', 'DB' are defenders. 'WR' is receiver.
defenders = df[df['position'].isin(['DC', 'DS', 'CB', 'S', 'DB', 'FS', 'SS'])]
receivers = df[df['position'] == 'WR']

print(f"Receivers: {receivers['player_name'].unique()}")
print(f"Defenders: {defenders['player_name'].unique()}")

# Function to calculate distance
def dist(row1, row2):
    return np.sqrt((row1['x'] - row2['x'])**2 + (row1['y'] - row2['y'])**2)

results = []

# Iterate over each receiver
for wr_name in receivers['player_name'].unique():
    wr_data = receivers[receivers['player_name'] == wr_name].sort_values('ts')
    
    if wr_data.empty:
        continue
        
    # Find covering defender (min avg distance)
    best_db_name = None
    min_avg_dist = float('inf')
    
    # We only check defenders active in the same time window
    start_time = wr_data['ts'].min()
    end_time = wr_data['ts'].max()
    
    potential_dbs = defenders[
        (defenders['ts'] >= start_time) & 
        (defenders['ts'] <= end_time)
    ]['player_name'].unique()
    
    for db_name in potential_dbs:
        db_data = defenders[defenders['player_name'] == db_name].sort_values('ts')
        
        # Merge on timestamp (nearest to handle slight offsets, or exact)
        # Using exact merge since 10Hz should align if from same session
        merged = pd.merge_asof(wr_data, db_data, on='ts', suffixes=('_wr', '_db'), direction='nearest', tolerance=pd.Timedelta('0.1s'))
        
        merged['separation'] = np.sqrt((merged['x_wr'] - merged['x_db'])**2 + (merged['y_wr'] - merged['y_db'])**2)
        avg_sep = merged['separation'].mean()
        
        if avg_sep < min_avg_dist:
            min_avg_dist = avg_sep
            best_db_name = db_name
            best_merged = merged
            
    if best_db_name:
        # Detect Break
        # Use change in direction 'dir_wr'
        # 'dir' is usually 0-360. We need to handle wrap-around spread.
        # But simply looking for spike in numerical derivative of x/y velocity vector is robust.
        # Let's use 'dir' provided. 
        # Calculate change in dir
        wr_data['dir_diff'] = wr_data['dir'].diff().abs()
        # Handle 360 wrap: if diff > 180, it's 360 - diff
        wr_data['dir_diff'] = wr_data['dir_diff'].apply(lambda x: 360 - x if x > 180 else x)
        
        # Smooth it
        wr_data['dir_diff_smooth'] = wr_data['dir_diff'].rolling(5).mean()
        
        # Find peak change where speed > 5 mph (to avoid static adjustments)
        # s is likely yds/s? No, usually yards/sec or mph. Assume yds/s? 
        # Actually standard tracking is yds/s. 5 mph is approx 2.5 yds/s.
        potential_breaks = wr_data[wr_data['s'] > 2.5]
        
        if not potential_breaks.empty:
            break_idx = potential_breaks['dir_diff_smooth'].idxmax()
            break_row = wr_data.loc[break_idx]
            break_time = break_row['ts']
            
            # Get separation at break time
            sep_at_break = best_merged.loc[best_merged['ts'] == break_time, 'separation'].values
            sep_at_break = sep_at_break[0] if len(sep_at_break) > 0 else np.nan
            
            # Speed Maintenance: Speed at break / Max Speed
            max_speed = wr_data['s'].max()
            speed_at_break = break_row['s']
            speed_maint = speed_at_break / max_speed if max_speed > 0 else 0
            
            results.append({
                'WR': wr_name,
                'DB': best_db_name,
                'Avg_Sep': min_avg_dist,
                'Sep_at_Break': sep_at_break,
                'Speed_Maint': speed_maint,
                'Break_Time': break_time
            })
            
            print(f"Match: {wr_name} vs {best_db_name}")
            print(f"  Sep @ Break: {sep_at_break:.2f} yds")
            print(f"  Speed Maint: {speed_maint:.2%}")

# Summary
res_df = pd.DataFrame(results)
print("\nResults Summary:")
print(res_df)
res_df.to_csv(r"C:\Users\16476\OneDrive\Desktop\ss_sbc\sample_metrics.csv", index=False)
