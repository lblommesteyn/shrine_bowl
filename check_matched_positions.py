import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")

# 1. Load CSV
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)
csv_ids = set(df_csv['college_gsis_id'].dropna().astype(int))

# 2. Get all Parquet IDs (re-run scan quickly or trusting previous count)
# We'll just scan one file to check those intersections again or all if needed.
# Let's effectively replicate the "Full ID check" but specifically looking at WHICH positions match.

parquet_ids = set()
for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Reading {file}...")
        try:
            table = pq.read_table(path, columns=['gsis_id'])
            p_ids = pd.to_numeric(table.column('gsis_id').to_pandas(), errors='coerce').dropna().astype(int)
            parquet_ids.update(p_ids)
        except Exception as e:
            print(f"Error reading {file}: {e}")

common = csv_ids.intersection(parquet_ids)
print(f"Common IDs: {len(common)}")

if common:
    # Filter CSV for these IDs
    matched_players = df_csv[df_csv['college_gsis_id'].isin(common)]
    print("\nMatched Players Positions:")
    print(matched_players['position'].value_counts())
    
    print("\nMatched Players Names:")
    print(matched_players[['player_name', 'position', 'college_gsis_id']])
