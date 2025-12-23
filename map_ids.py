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
print("Unique Teams in CSV:", df_csv['team'].unique())

# 2. Get Jersey Number for a sample ID in Parquet
print(f"\nReading {parquet_path}...")
try:
    # Filter for a specific ID we saw earlier: 280246
    # We need to read jersey_number and gsis_id
    table = pq.read_table(parquet_path, columns=['gsis_id', 'jersey_number'], filters=[('gsis_id', '==', 280246)])
    df_parquet = table.to_pandas()
    
    if not df_parquet.empty:
        jersey_num = df_parquet['jersey_number'].iloc[0]
        print(f"ID 280246 has Jersey Number: {jersey_num}")
        
        # 3. Find match in CSV
        # Assuming 'West' team because filename is 2022_West...
        # Check if 'West' is a team name in CSV
        potential_matches = df_csv[
            (df_csv['jersey_number'] == jersey_num) & 
            (df_csv['team'].str.contains('West', case=False, na=False))
        ]
        
        if not potential_matches.empty:
            print("Potential Matches in CSV:")
            print(potential_matches[['college_gsis_id', 'player_name', 'position', 'team', 'jersey_number']])
        else:
            print("No matches found in CSV for West team.")
            # Try all teams
            all_matches = df_csv[df_csv['jersey_number'] == jersey_num]
            print("Matches across all teams:")
            print(all_matches[['college_gsis_id', 'player_name', 'position', 'team', 'jersey_number']])
            
    else:
        print("ID 280246 not found in this file (maybe it was in another file or I misread the previous output).")
        # Let's just get ANY ID and jersey number
        table = pq.read_table(parquet_path, columns=['gsis_id', 'jersey_number'])
        df_sample = table.to_pandas().drop_duplicates().head(5)
        print("Sample IDs and Jersey Numbers from Parquet:")
        print(df_sample)

except Exception as e:
    print(f"Error: {e}")
