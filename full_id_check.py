import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")

print("Loading CSV IDs...")
df_csv = pd.read_csv(csv_path)
csv_ids = set(df_csv['college_gsis_id'].dropna().astype(int))
print(f"CSV IDs: {len(csv_ids)}")

print("Loading Parquet IDs...")
parquet_ids = set()
for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Reading {file}...")
        try:
            table = pq.read_table(path, columns=['gsis_id'])
            # Convert to pandas series
            p_ids = table.column('gsis_id').to_pandas()
            # Convert to numeric, dropna, unique
            p_ids_numeric = pd.to_numeric(p_ids, errors='coerce').dropna().astype(int)
            parquet_ids.update(p_ids_numeric)
        except Exception as e:
            print(f"Error reading {file}: {e}")

print(f"Total Unique Parquet IDs: {len(parquet_ids)}")

common = csv_ids.intersection(parquet_ids)
print(f"Common IDs: {len(common)}")

if common:
    print(f"Sample Common IDs: {list(common)[:10]}")
else:
    print("NO COMMON IDS FOUND.")
    print(f"Sample CSV IDs: {list(csv_ids)[:5]}")
    print(f"Sample Parquet IDs: {list(parquet_ids)[:5]}")
