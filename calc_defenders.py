import pandas as pd

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"
output_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\defender_leaderboard.csv"

print("Loading data...")
df = pd.read_csv(file_path)

if df.empty:
    print("No data.")
    exit()

# Metric: "Stickiness" = Low Avg Separation
# Filter: Min 1 rep
qualified = df.groupby('DB').size()
qualified_dbs = qualified[qualified >= 1].index

db_stats = df[df['DB'].isin(qualified_dbs)].groupby('DB').agg(
    Avg_Sep_at_Break=('Sep_at_Break', 'mean'),
    Total_Reps=('Sep_at_Break', 'count')
).reset_index()

# Sort by lowest separation (Best Stickiness)
leaderboard = db_stats.sort_values('Avg_Sep_at_Break', ascending=True)

print("\n--- Defender Stickiness Leaderboard ---")
print(leaderboard)
leaderboard.to_csv(output_path, index=False)
