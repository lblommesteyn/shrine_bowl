import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\practice_data"
file_name = "2022_West_Practice_2.snappy.parquet"
path = os.path.join(data_dir, file_name)

try:
    parquet_file = pq.ParquetFile(path)
    print(f"Schema for {file_name}:")
    for name in parquet_file.schema.names:
        print(f"'{name}'")
except Exception as e:
    print(f"Error: {e}")
