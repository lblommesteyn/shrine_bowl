import pandas as pd

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"
df = pd.read_csv(file_path)

print("Distribution of Avg Separation:")
print(df['Avg_Sep'].describe())

print("\nDistribution of Sep at Break:")
print(df['Sep_at_Break'].describe())

# Filter for realistic pairs (Avg Sep < 10 yards)
valid_reps = df[df['Avg_Sep'] < 10.0]
print(f"\nValid Reps (Avg Sep < 10yds): {len(valid_reps)}")

if not valid_reps.empty:
    print("\nTop Separators (Valid Reps):")
    print(valid_reps[['WR', 'DB', 'Sep_at_Break', 'Speed_Maint']].sort_values('Sep_at_Break', ascending=False))
else:
    print("No valid reps found.")
