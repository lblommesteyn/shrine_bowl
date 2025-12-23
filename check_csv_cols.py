import pandas as pd
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")

try:
    df_csv = pd.read_csv(csv_path, nrows=1)
    print("CSV Columns:")
    for col in df_csv.columns:
        print(col)
except Exception as e:
    print(f"Error: {e}")
