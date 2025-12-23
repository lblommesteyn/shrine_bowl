import pandas as pd
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")

try:
    df_csv = pd.read_csv(csv_path, nrows=1)
    cols = df_csv.columns.tolist()
    print("All Columns:", cols)
    
    # Check for keywords
    keywords = ['jersey', 'num', 'no', 'id']
    potential = [c for c in cols if any(k in c.lower() for k in keywords)]
    print("Potential ID/Jersey Columns:", potential)
    
except Exception as e:
    print(f"Error: {e}")
