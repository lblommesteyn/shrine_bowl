import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")
output_file = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\skill_1on1_matched.csv"

# 1. Load CSV and get IDs
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)
csv_ids = set(df_csv['college_gsis_id'].dropna().astype(int))

# 2. Extract Data
all_data = []

print("Scanning Parquet files...")
for file in os.listdir(practice_dir):
    if file.endswith(".parquet"):
        path = os.path.join(practice_dir, file)
        print(f"Processing {file}...")
        
        try:
            parquet_file = pq.ParquetFile(path)
            
            # Stream batch to save memory
            for batch in parquet_file.iter_batches(batch_size=100000):
                df = batch.to_pandas()
                
                # Filter for "Skill 1 on 1"
                # Use str.contains to be safe about exact naming
                mask_drill = df['drill_type'].astype(str).str.contains("Skill 1 on 1", case=False, na=False)
                df_drill = df[mask_drill]
                
                if not df_drill.empty:
                    # Clean gsis_id
                    df_drill['gsis_id'] = pd.to_numeric(df_drill['gsis_id'], errors='coerce')
                    
                    # Filter for matched IDs
                    df_matched = df_drill[df_drill['gsis_id'].isin(csv_ids)].copy()
                    
                    if not df_matched.empty:
                        all_data.append(df_matched)
                        
        except Exception as e:
            print(f"Error reading {file}: {e}")

# 3. Save
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    # Join with player info
    final_df = final_df.merge(df_csv[['college_gsis_id', 'player_name', 'position', 'team']], 
                              left_on='gsis_id', right_on='college_gsis_id', how='left')
    
    print(f"Total matched rows: {len(final_df)}")
    print("Positions found:")
    print(final_df['position'].value_counts())
    
    final_df.to_csv(output_file, index=False)
    print(f"Saved to {output_file}")
else:
    print("No matched data found.")
