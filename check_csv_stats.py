import pandas as pd
df = pd.read_csv(r'C:\Users\16476\OneDrive\Desktop\ss_sbc\data\Shrine Bowl Data\shrine_bowl_players_college_stats.csv', nrows=1)
for col in df.columns:
    print(col)
