import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")

# 1. Load CSV and identify matched WR/DB IDs
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)

target_positions = ['WR', 'CB', 'S', 'DB', 'DS', 'FS', 'SS', 'DC']
target_players = df_csv[df_csv['position'].isin(target_positions)]
target_ids = set(target_players['college_gsis_id'].dropna().astype(int))

print(f"Target IDs (WR/DB): {len(target_ids)}")

# 2. Scan Parquet using batches
drill_counts = {}

for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Reading {file}...")
        try:
            parquet_file = pq.ParquetFile(path)
            
            # Iterate in batches
            for batch in parquet_file.iter_batches(batch_size=100000, columns=['drill_type', 'gsis_id']):
                df_batch = batch.to_pandas()
                
                # Clean IDs
                df_batch['gsis_id'] = pd.to_numeric(df_batch['gsis_id'], errors='coerce')
                
                # Filter
                matched = df_batch[df_batch['gsis_id'].isin(target_ids)]
                
                if not matched.empty:
                    drills = matched['drill_type'].value_counts()
                    for drill, count in drills.items():
                        drill_counts[drill] = drill_counts.get(drill, 0) + count
                        
        except Exception as e:
            print(f"Error reading {file}: {e}")

print("\nTop Drills for WR/DB IDs:")
for drill, count in sorted(drill_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{drill}: {count}")
