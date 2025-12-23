import pandas as pd
import pyarrow.parquet as pq
import os

data_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\practice_data"
output_file = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\crossover_sample.csv"

print("Scanning for Cross Over drills...")

# We'll just grab a sample from the first file that has them to start EDA
for file in os.listdir(data_dir):
    if file.endswith(".parquet"):
        path = os.path.join(data_dir, file)
        try:
            # Read drill_type to filter
            table = pq.read_table(path, columns=['drill_type'])
            drill_types = table.column('drill_type').to_pylist()
            
            # Find indices where drill_type is 'Cross Over'
            indices = [i for i, x in enumerate(drill_types) if x == 'Cross Over']
            
            if indices:
                print(f"Found {len(indices)} rows in {file}")
                # Read full columns for these rows
                # Pyarrow doesn't support reading by index list easily, so we might need to read chunks or use pandas with filters if memory allows.
                # Given the file size (~1GB), reading the whole thing might be tight but doable. 
                # Let's try reading with a filter pushdown.
                
                df = pd.read_parquet(path, filters=[('drill_type', '==', 'Cross Over')])
                print(f"Extracted {len(df)} rows.")
                
                # Save a sample for quick iteration
                df.head(10000).to_csv(output_file, index=False)
                print(f"Saved sample to {output_file}")
                
                # Print some basic stats
                print(df['position'].value_counts())
                print(df.columns)
                break
        except Exception as e:
            print(f"Error reading {file}: {e}")
