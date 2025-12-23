import pandas as pd
import pyarrow.parquet as pq
import os

base_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"
data_dir = os.path.join(base_dir, "data", "Shrine Bowl Data", "practice_data")
stats_path = os.path.join(base_dir, "data", "Shrine Bowl Data", "shrine_bowl_players_college_stats.csv")

derived_files = [
    "team_1_matched.csv",
    "skill_1on1_matched.csv",
    "full_analysis_results.csv"
]

print("--- RAW DATA ---")
# College Stats
try:
    df_stats = pd.read_csv(stats_path)
    print(f"File: shrine_bowl_players_college_stats.csv | Rows: {len(df_stats)} | Cols: {len(df_stats.columns)}")
    print(f"   Columns: {', '.join(df_stats.columns[:5])}...")
except Exception as e:
    print(f"Error reading stats: {e}")

# Parquet Files
parquet_files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
total_rows = 0
for f in parquet_files:
    path = os.path.join(data_dir, f)
    try:
        meta = pq.read_metadata(path)
        rows = meta.num_rows
        total_rows += rows
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"File: {f} | Rows: {rows:,} | Size: {size_mb:.1f} MB")
    except Exception as e:
        print(f"Error reading {f}: {e}")

print(f"\nTotal Tracking Rows: {total_rows:,}")

print("\n--- DERIVED DATA ---")
for f in derived_files:
    path = os.path.join(base_dir, f)
    if os.path.exists(path):
        try:
            # fast row count for huge files
            with open(path, 'rb') as f_obj:
                rows = sum(1 for _ in f_obj) - 1 # minus header
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"File: {f} | Rows: {rows:,} | Size: {size_mb:.1f} MB")
        except Exception as e:
             print(f"Error reading {f}: {e}")
    else:
        print(f"File: {f} | Not Found")
