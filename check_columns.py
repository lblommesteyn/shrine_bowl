import pandas as pd

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\team_1_matched.csv"
try:
    df = pd.read_csv(file_path, nrows=5)
    cols = df.columns.tolist()
    print("Columns:", cols)
    
    # Check for keywords
    keywords = ['event', 'outcome', 'pass', 'catch', 'int', 'result']
    found = [c for c in cols if any(k in c.lower() for k in keywords)]
    print("Potential Event Columns:", found)
except Exception as e:
    print(e)
