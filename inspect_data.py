import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")

print("--- CSV Schema ---")
try:
    df_csv = pd.read_csv(csv_path, nrows=1)
    for col in df_csv.columns:
        print(col)
except Exception as e:
    print(f"Error reading CSV: {e}")

print("\n--- Parquet Schema ---")
for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"File: {file}")
        try:
            parquet_file = pq.ParquetFile(path)
            for name in parquet_file.schema.names:
                print(name)
            print(f"Num rows: {parquet_file.metadata.num_rows}")
            break 
        except Exception as e:
            print(f"Error reading Parquet: {e}")
