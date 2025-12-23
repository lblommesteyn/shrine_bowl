import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\practice_data"

for file in os.listdir(data_dir):
    if file.endswith(".parquet"):
        path = os.path.join(data_dir, file)
        print(f"File: {file}")
        try:
            # Read only the drill_type column
            df = pd.read_parquet(path, columns=['drill_type'])
            unique_drills = df['drill_type'].unique()
            print("Unique Drill Types:")
            for drill in unique_drills:
                print(drill)
            break # Just check one file for now
        except Exception as e:
            print(f"Error reading Parquet: {e}")
