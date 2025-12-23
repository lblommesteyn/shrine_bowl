import pyarrow.parquet as pq
import os
import pandas as pd

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\practice_data"
file_name = "2022_West_Practice_2.snappy.parquet"
path = os.path.join(data_dir, file_name)

target_id = 158332 # Austin Lee from CSV

print(f"Checking for ID {target_id} in {file_name}...")

try:
    # Read gsis_id column
    table = pq.read_table(path, columns=['gsis_id'])
    ids = table.column('gsis_id').to_pylist()
    
    if target_id in ids:
        print(f"FOUND: ID {target_id} exists in Parquet!")
    else:
        print(f"NOT FOUND: ID {target_id} does NOT exist in Parquet.")
        print(f"Sample IDs in Parquet: {ids[:10]}")
        
except Exception as e:
    print(f"Error: {e}")
