import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")
output_file = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\crossover_wr_db.csv"

# 1. Load Player Metadata
print("Loading player metadata...")
players = pd.read_csv(csv_path)
# Filter for WR and DB (CB, S, DB)
# Let's check unique positions first to be sure
print("Positions found:", players['position'].unique())
target_positions = ['WR', 'CB', 'S', 'DB', 'DS', 'FS', 'SS'] # Add others if needed
relevant_players = players[players['position'].isin(target_positions)]
relevant_ids = set(relevant_players['college_gsis_id'])
print(f"Found {len(relevant_players)} relevant players (WR/DB/S).")

# 2. Extract Tracking Data
all_data = []

print("Scanning Parquet files...")
for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Processing {file}...")
        
        try:
            # Read drill_type and gsis_id to filter rows
            # We use a filter in read_table for efficiency
            # Filter: drill_type == 'Cross Over'
            
            table = pq.read_table(path, filters=[('drill_type', '==', 'Cross Over')])
            df = table.to_pandas()
            
            if not df.empty:
                print(f"  Found {len(df)} Cross Over rows.")
                
                # Filter by relevant IDs
                # Note: Parquet 'gsis_id' might be float or int, CSV is likely int. Ensure type match.
                # Let's convert to numeric, coercing errors
                df['gsis_id'] = pd.to_numeric(df['gsis_id'], errors='coerce')
                
                # Filter
                df_filtered = df[df['gsis_id'].isin(relevant_ids)].copy()
                print(f"  Retained {len(df_filtered)} rows after position filter.")
                
                if not df_filtered.empty:
                    all_data.append(df_filtered)
                    
        except Exception as e:
            print(f"Error reading {file}: {e}")

# 3. Combine and Save
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Join with player metadata to get names and positions
    final_df = final_df.merge(relevant_players[['college_gsis_id', 'player_name', 'position']], 
                              left_on='gsis_id', right_on='college_gsis_id', how='left')
    
    print(f"Total rows extracted: {len(final_df)}")
    final_df.to_csv(output_file, index=False)
    print(f"Saved to {output_file}")
else:
    print("No data found.")
