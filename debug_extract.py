import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")

# 1. Load Player Metadata
print("Loading player metadata...")
players = pd.read_csv(csv_path)
target_positions = ['WR', 'CB', 'S', 'DB', 'DS', 'FS', 'SS']
relevant_players = players[players['position'].isin(target_positions)]
relevant_ids = set(relevant_players['college_gsis_id'])
print(f"Sample relevant IDs: {list(relevant_ids)[:5]}")

# 2. Extract Tracking Data Sample
for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Processing {file}...")
        
        try:
            table = pq.read_table(path, filters=[('drill_type', '==', 'Cross Over')])
            df = table.to_pandas()
            
            if not df.empty:
                print(f"  Found {len(df)} Cross Over rows.")
                print(f"  Sample gsis_id from Parquet (raw): {df['gsis_id'].head().tolist()}")
                
                # Convert to numeric
                df['gsis_id'] = pd.to_numeric(df['gsis_id'], errors='coerce')
                print(f"  Sample gsis_id from Parquet (numeric): {df['gsis_id'].head().tolist()}")
                
                # Check intersection
                parquet_ids = set(df['gsis_id'].dropna().unique())
                common = parquet_ids.intersection(relevant_ids)
                print(f"  Common IDs found: {len(common)}")
                if common:
                    print(f"  Sample common IDs: {list(common)[:5]}")
                
                break # Just check one file
        except Exception as e:
            print(f"Error reading {file}: {e}")
