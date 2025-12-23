import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")
parquet_path = os.path.join(practice_dir, "2022_West_Practice_2.snappy.parquet")

# 1. Load CSV
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)

# Check Bennett Williams
bennett = df_csv[df_csv['college_gsis_id'] == 280026]
print("\nBennett Williams in CSV:")
print(bennett[['college_gsis_id', 'player_name', 'position', 'team']])

# Check 280k range positions
ids_280k = df_csv[(df_csv['college_gsis_id'] >= 280000) & (df_csv['college_gsis_id'] < 290000)]
print(f"\nPlayers with 280k IDs in CSV: {len(ids_280k)}")
print("Positions of 280k players:")
print(ids_280k['position'].value_counts())

# 2. Check Parquet for Bennett Williams
print(f"\nChecking Parquet for ID 280026...")
try:
    # Read gsis_id column
    table = pq.read_table(parquet_path, columns=['gsis_id'])
    # Convert to numeric list
    parquet_ids = pd.to_numeric(table.column('gsis_id').to_pandas(), errors='coerce').dropna().unique()
    
    if 280026 in parquet_ids:
        print("FOUND: Bennett Williams (280026) is in Parquet!")
    else:
        print("NOT FOUND: Bennett Williams (280026) is NOT in Parquet.")
        
    # Check intersection of all 280k CSV IDs with Parquet
    csv_ids_set = set(ids_280k['college_gsis_id'])
    parquet_ids_set = set(parquet_ids)
    common = csv_ids_set.intersection(parquet_ids_set)
    print(f"\nCommon IDs between CSV (280k range) and Parquet: {len(common)}")
    if common:
        print(f"Sample Common IDs: {list(common)[:5]}")
        
except Exception as e:
    print(f"Error: {e}")
