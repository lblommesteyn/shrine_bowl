import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\practice_data"
# Find first parquet
file = [f for f in os.listdir(data_dir) if f.endswith('.parquet')][0]
path = os.path.join(data_dir, file)

print(f"Inspecting: {file}")
pf = pq.ParquetFile(path)
print("Columns:")
print(pf.schema.names)
