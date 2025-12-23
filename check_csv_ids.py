import pandas as pd
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")

try:
    df_csv = pd.read_csv(csv_path)
    print("CSV Columns:", df_csv.columns.tolist())
    
    ids = df_csv['college_gsis_id']
    print(f"ID Count: {len(ids)}")
    print(f"Min ID: {ids.min()}")
    print(f"Max ID: {ids.max()}")
    print(f"Sample IDs: {ids.sample(10).tolist()}")
    
    # Check if any IDs are in 280000 range
    range_match = df_csv[(ids >= 280000) & (ids < 290000)]
    print(f"IDs in 280k range: {len(range_match)}")
    if not range_match.empty:
        print(range_match[['college_gsis_id', 'player_name']].head())
        
except Exception as e:
    print(f"Error: {e}")
