import pyarrow.parquet as pq
import os
import pandas as pd

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\practice_data"
file_name = "2022_West_Practice_2.snappy.parquet"
path = os.path.join(data_dir, file_name)

print(f"Checking Cross Over drills in {file_name}...")

try:
    # Read columns for Cross Over
    table = pq.read_table(path, filters=[('drill_type', '==', 'Cross Over')])
    df = table.to_pandas()
    
    if not df.empty:
        print(f"Found {len(df)} rows.")
        print("Entity Types:")
        print(df['entity_type'].value_counts())
        
        # Check IDs for 'player' entity type
        players_df = df[df['entity_type'] == 'player'] # Assuming 'player' is the value
        if not players_df.empty:
            print(f"Found {len(players_df)} player rows.")
            ids = players_df['gsis_id'].unique()
            print(f"Unique Player IDs: {len(ids)}")
            print(f"Sample IDs: {ids[:10]}")
            
            # Check if 158332 is in there
            if 158332 in ids:
                print("ID 158332 FOUND in Cross Over!")
            else:
                print("ID 158332 NOT found in Cross Over.")
        else:
            print("No 'player' entity type found. Checking unique entity types...")
            print(df['entity_type'].unique())
            
    else:
        print("No Cross Over rows found.")
        
except Exception as e:
    print(f"Error: {e}")
