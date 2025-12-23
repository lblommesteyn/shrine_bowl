import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")

# 1. Load CSV and identify matched WR/DB IDs
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)

# Filter for WRs/DBs and get their IDs
# Note: 'DC', 'DS' seem to be DB positions in this dataset
target_positions = ['WR', 'CB', 'S', 'DB', 'DS', 'FS', 'SS', 'DC']
target_players = df_csv[df_csv['position'].isin(target_positions)]
target_ids = set(target_players['college_gsis_id'].dropna().astype(int))

print(f"Target IDs (WR/DB): {len(target_ids)}")

# 2. Scan Parquet for these IDs and record drill types
drill_counts = {}

for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Reading {file}...")
        try:
            # We must read drill_type and gsis_id
            # Reading entire file cols might be slow, but let's try reading just these two cols
            table = pq.read_table(path, columns=['drill_type', 'gsis_id'])
            df = table.to_pandas()
            
            # Clean IDs
            df['gsis_id'] = pd.to_numeric(df['gsis_id'], errors='coerce')
            
            # Filter for our target IDs
            matched = df[df['gsis_id'].isin(target_ids)]
            
            if not matched.empty:
                print(f"  Found {len(matched)} rows for target players.")
                # Count drills
                drills = matched['drill_type'].value_counts()
                for drill, count in drills.items():
                    drill_counts[drill] = drill_counts.get(drill, 0) + count
                    
        except Exception as e:
            print(f"Error reading {file}: {e}")

print("\nTop Drills for WR/DB IDs:")
for drill, count in sorted(drill_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{drill}: {count}")
