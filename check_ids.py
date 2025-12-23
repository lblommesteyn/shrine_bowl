import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")
parquet_path = os.path.join(practice_dir, "2022_West_Practice_2.snappy.parquet")

print("--- CSV IDs ---")
df_csv = pd.read_csv(csv_path)
print(f"CSV ID column: 'college_gsis_id'")
print(df_csv['college_gsis_id'].head())
print(f"Total players in CSV: {len(df_csv)}")

print("\n--- Parquet IDs ---")
# Read a small sample of gsis_id from parquet
table = pq.read_table(parquet_path, columns=['gsis_id'])
# Get unique non-null IDs
ids = pd.Series(table.column('gsis_id').to_pylist()).dropna().unique()
print(f"Parquet ID column: 'gsis_id'")
print(ids[:10])
print(f"Total unique IDs in Parquet: {len(ids)}")

# Check overlap
common = set(df_csv['college_gsis_id']).intersection(set(ids))
print(f"\nCommon IDs: {len(common)}")
