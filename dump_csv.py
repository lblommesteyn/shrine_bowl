import pandas as pd
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
output_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\csv_dump.txt"

try:
    df_csv = pd.read_csv(csv_path, nrows=1)
    with open(output_path, "w") as f:
        f.write("Columns:\n")
        for col in df_csv.columns:
            f.write(f"{col}\n")
        
        f.write("\nFirst Row:\n")
        row = df_csv.iloc[0].to_dict()
        for k, v in row.items():
            f.write(f"{k}: {v}\n")
            
    print(f"Dumped to {output_path}")
    
except Exception as e:
    print(f"Error: {e}")
