import pandas as pd
try:
    df = pd.read_csv("wroe_results.csv")
    print("Top 10 WROE Leaders:")
    print(df.head(10))
except Exception as e:
    print(e)
