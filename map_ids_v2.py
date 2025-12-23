import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")
parquet_path = os.path.join(practice_dir, "2022_West_Practice_2.snappy.parquet")

# 1. Load CSV and check teams
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)
print("Unique Teams in CSV:", sorted(df_csv['team'].unique()))

# 2. Get Jersey Number for a sample ID in Parquet
print(f"\nReading {parquet_path}...")
try:
    # Filter for a specific ID we saw earlier: 280246 (as string)
    # Note: If it's a float string like "280246.0", we might need to be careful.
    # But let's try "280246" first.
    
    # We'll read a chunk and filter in pandas to avoid pyarrow filter issues if types are messy
    table = pq.read_table(parquet_path, columns=['gsis_id', 'jersey_number'])
    df_parquet = table.to_pandas()
    
    # Clean gsis_id
    # It might be "280246.0" or "280246"
    df_parquet['gsis_id_clean'] = pd.to_numeric(df_parquet['gsis_id'], errors='coerce').astype('Int64')
    
    target_id = 280246
    match = df_parquet[df_parquet['gsis_id_clean'] == target_id]
    
    if not match.empty:
        jersey_num = match['jersey_number'].iloc[0]
        print(f"ID {target_id} has Jersey Number: {jersey_num}")
        
        # 3. Find match in CSV
        # Check if 'West' is a team name in CSV
        # Looking at filenames: 2022_West... and 2024_West...
        # The team name in CSV might be 'West' or 'East' or something else.
        
        potential_matches = df_csv[
            (df_csv['jersey_number'] == jersey_num) & 
            (df_csv['team'].str.contains('West', case=False, na=False))
        ]
        
        if not potential_matches.empty:
            print("Potential Matches in CSV (West):")
            print(potential_matches[['college_gsis_id', 'player_name', 'position', 'team', 'jersey_number']])
        else:
            print("No matches found in CSV for West team.")
            all_matches = df_csv[df_csv['jersey_number'] == jersey_num]
            print("Matches across all teams:")
            print(all_matches[['college_gsis_id', 'player_name', 'position', 'team', 'jersey_number']])
            
    else:
        print(f"ID {target_id} not found in this file.")
        print("Sample IDs from Parquet:")
        print(df_parquet['gsis_id'].head())

except Exception as e:
    print(f"Error: {e}")
