import pandas as pd
file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\skill_1on1_matched.csv"
try:
    df = pd.read_csv(file_path, nrows=5)
    print("Columns:")
    for c in df.columns:
        print(c)
except Exception as e:
    print(e)
