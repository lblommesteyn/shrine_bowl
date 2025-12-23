import pandas as pd

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\skill_1on1_matched.csv"
print("Loading data...")
try:
    df = pd.read_csv(file_path)
    print(f"Total rows: {len(df)}")
    print("Unique Positions:", df['position'].unique())
    print("\nUnique WRs:", df[df['position'] == 'WR']['player_name'].unique())
    print("\nUnique DBs:", df[df['position'].isin(['DC', 'DS', 'CB', 'S', 'DB', 'FS', 'SS'])]['player_name'].unique())
except Exception as e:
    print(e)
