import pandas as pd
import pyarrow.parquet as pq
import os
import gc

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data"
csv_path = os.path.join(data_dir, "shrine_bowl_players_college_stats.csv")
practice_dir = os.path.join(data_dir, "practice_data")
output_file = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\skill_1on1_matched.csv"

# 1. Load CSV and get IDs
print("Loading CSV...")
df_csv = pd.read_csv(csv_path)
csv_ids = set(df_csv['college_gsis_id'].dropna().astype(int))
player_metadata = df_csv[['college_gsis_id', 'player_name', 'position', 'team']]

# 2. Extract Data Iteratively
first_chunk = True

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
                mask_drill = df['drill_type'].astype(str).str.contains("Skill 1 on 1", case=False, na=False)
                df_drill = df[mask_drill]
                
                if not df_drill.empty:
                    # Clean gsis_id
                    df_drill = df_drill.copy() # Avoid SettingWithCopyWarning
                    df_drill['gsis_id'] = pd.to_numeric(df_drill['gsis_id'], errors='coerce')
                    
                    # Filter for matched IDs
                    df_matched = df_drill[df_drill['gsis_id'].isin(csv_ids)].copy()
                    
                    if not df_matched.empty:
                        # Join with player info immediately
                        df_merged = df_matched.merge(player_metadata, 
                                                  left_on='gsis_id', right_on='college_gsis_id', how='left')
                        
                        # Append to CSV
                        if first_chunk:
                            df_merged.to_csv(output_file, index=False, mode='w')
                            first_chunk = False
                        else:
                            df_merged.to_csv(output_file, index=False, mode='a', header=False)
                        
                        # Explicitly clear memory
                        del df_merged
                        del df_matched
                
                # Clear batch memory
                del df
                del df_drill
                gc.collect()
                        
        except Exception as e:
            print(f"Error reading {file}: {e}")

print(f"Saved to {output_file}")
