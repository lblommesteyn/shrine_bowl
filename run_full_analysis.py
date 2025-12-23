import pandas as pd
import numpy as np
import gc

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\team_1_matched.csv"
output_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"

print("Loading data...")
df = pd.read_csv(file_path)
df['ts'] = pd.to_datetime(df['ts'])

print(f"Total rows: {len(df)}")

# Define positions
defenders_df = df[df['position'].isin(['DC', 'DS', 'CB', 'S', 'DB', 'FS', 'SS'])]
receivers_df = df[df['position'].isin(['WR', 'TE', 'RB'])]
print(f"Total Receivers (WR/TE/RB): {len(receivers_df['player_name'].unique())}")
print(f"Total DBs: {len(defenders_df['player_name'].unique())}")

results = []

# Process by player to handle reps
for wr_name in receivers_df['player_name'].unique():
    wr_data_full = receivers_df[receivers_df['player_name'] == wr_name].sort_values('ts')
    
    # Identify reps by time gap (> 5s)
    wr_data_full['time_diff'] = wr_data_full['ts'].diff().dt.total_seconds()
    wr_data_full['rep_id'] = (wr_data_full['time_diff'] > 5.0).cumsum()
    
    for rep_id, wr_rep in wr_data_full.groupby('rep_id'):
        if wr_rep.empty or len(wr_rep) < 10: # Skip tiny reps
            continue
            
        max_speed = wr_rep['s'].max()
        if max_speed < 4.0: # Skip low speed reps (walking back)
            continue
            
        # Find overlapping defenders for this rep
        start_time = wr_rep['ts'].min()
        end_time = wr_rep['ts'].max()
        
        # Optimize: Filter defenders by time window first
        relevant_dbs = defenders_df[
            (defenders_df['ts'] >= start_time) & 
            (defenders_df['ts'] <= end_time)
        ]
        
        if relevant_dbs.empty:
            continue
            
        best_db = None
        min_avg_dist = float('inf')
        best_merged = None
        
        for db_name in relevant_dbs['player_name'].unique():
            db_rep = relevant_dbs[relevant_dbs['player_name'] == db_name].sort_values('ts')
            
            # Merge
            merged = pd.merge_asof(wr_rep, db_rep, on='ts', suffixes=('_wr', '_db'), 
                                   direction='nearest', tolerance=pd.Timedelta('0.2s')) # Increased tolerance
            merged = merged.dropna(subset=['x_db'])
            
            if merged.empty:
                continue
                
            merged['separation'] = np.sqrt((merged['x_wr'] - merged['x_db'])**2 + (merged['y_wr'] - merged['y_db'])**2)
            avg_sep = merged['separation'].mean()
            
            if avg_sep < min_avg_dist:
                min_avg_dist = avg_sep
                best_db = db_name
                best_merged = merged
        
        if best_db and best_merged is not None:
             # Detect Break
            wr_rep = wr_rep.copy()
            wr_rep['dir_diff'] = wr_rep['dir'].diff().abs()
            wr_rep['dir_diff'] = wr_rep['dir_diff'].apply(lambda x: 360 - x if x > 180 else x)
            wr_rep['dir_diff_smooth'] = wr_rep['dir_diff'].rolling(5).mean()
            
            potential_breaks = wr_rep[wr_rep['s'] > 4.0]
            
            if not potential_breaks.empty:
                break_idx = potential_breaks['dir_diff_smooth'].idxmax()
                break_time = wr_rep.loc[break_idx, 'ts']
                
                # Get separation
                sep_hits = best_merged[best_merged['ts'] == break_time]
                if not sep_hits.empty:
                    sep_at_break = sep_hits['separation'].iloc[0]
                else:
                    # Fallback to nearest if exact match failed despite merge_asof logic (rare)
                    sep_at_break = np.nan
                
                
                # Closing Burst Calculation (Sep @ Break - Sep @ Break+1s)
                burst_time = break_time + pd.Timedelta(seconds=1.0)
                sep_hits_burst = best_merged[best_merged['ts'] >= burst_time]
                
                closing_burst = 0
                if not sep_hits_burst.empty:
                    # Get the first point >= 1s later
                    sep_after_1s = sep_hits_burst['separation'].iloc[0]
                    # Positive closing burst = reduced separation (good for D, bad for O). 
                    # For WR profile, we might want "Separation Sustained"
                    closing_burst = sep_at_break - sep_after_1s
                    
                
                speed_maint = wr_rep.loc[break_idx, 's'] / max_speed if max_speed > 0 else 0
                
                # Context Feature 1: Relative Alignment at Snap (Start of Rep)
                # We use the first frame of the rep where both match
                start_row = best_merged.iloc[0]
                start_dx = start_row['x_wr'] - start_row['x_db']
                start_dy = start_row['y_wr'] - start_row['y_db']
                
                # Context Feature 2: Route Depth (Y distance from start to break)
                # Assuming Y is downfield direction. If not, abs() handles it.
                # Actually, in standard tracking X is usually sideline-to-sideline (53.3) and Y is downfield.
                # We'll assume relative change from start is the depth.
                break_row = best_merged[best_merged['ts'] == break_time]
                if not break_row.empty:
                    route_depth = abs(break_row['y_wr'].iloc[0] - start_row['y_wr'])
                else:
                    route_depth = 0 # Fallback
                
                speed_maint = wr_rep.loc[break_idx, 's'] / max_speed if max_speed > 0 else 0
                break_angle = wr_rep.loc[break_idx, 'dir_diff_smooth']
                
                results.append({
                    'WR': wr_name,
                    'DB': best_db,
                    'Rep_ID': f"{wr_name}_{rep_id}",
                    'Avg_Sep': min_avg_dist,
                    'Sep_at_Break': sep_at_break,
                    'Closing_Burst': closing_burst,
                    'Speed_Maint': speed_maint,
                    'Break_Angle': break_angle,
                    'Speed_Maint': speed_maint,
                    'Break_Angle': break_angle,
                    'Start_dx': start_dx,
                    'Start_dy': start_dy,
                    'Route_Depth': route_depth,
                    'Break_Time': break_time,
                    'Max_Speed': max_speed
                })

# Save results
res_df = pd.DataFrame(results)
print(f"Processed {len(res_df)} reps.")
res_df.to_csv(output_path, index=False)
print(f"Saved results to {output_path}")

# Print Top Performers
print("\nTop 5 Separators (Avg Sep at Break):")
print(res_df.groupby('WR')['Sep_at_Break'].mean().sort_values(ascending=False).head())
