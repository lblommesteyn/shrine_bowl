import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

file_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\concurrent_sample.csv"
print("Loading data...")
df = pd.read_csv(file_path)

print("Unique Players:", df['player_name'].unique())
print("Unique Positions:", df['position'].unique())

plt.figure(figsize=(12, 8))
sns.scatterplot(data=df, x='x', y='y', hue='position', style='player_name', s=20)
plt.title("Sample Trajectories (10s window)")
plt.xlabel("X (yards)")
plt.ylabel("Y (yards)")
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.axis('equal')
plt.tight_layout()

output_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\sample_plot.png"
plt.savefig(output_path)
print(f"Saved plot to {output_path}")
