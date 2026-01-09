import pyarrow.parquet as pq
import pandas as pd

# Load zebra_id to gsis_id mapping
table = pq.read_table(
    '../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet',
    columns=['zebra_id', 'gsis_id'],
    filters=[('session_id', '=', 4)]
)
df = table.to_pandas()
df = df.drop_duplicates(subset=['zebra_id'])

# Separate with and without gsis_id
with_gsis = df[df['gsis_id'].notna()].copy()
without_gsis = df[df['gsis_id'].isna()].copy()

print("=" * 80)
print("ZEBRA_ID TO GSIS_ID MAPPING ANALYSIS")
print("=" * 80)
print(f"\nTotal unique zebra_ids: {len(df)}")
print(f"With gsis_id: {len(with_gsis)}")
print(f"Without gsis_id: {len(without_gsis)}")

print("\n" + "-" * 80)
print("Sample mappings (with gsis_id):")
print("-" * 80)
print(with_gsis.head(15).to_string(index=False))

print("\n" + "-" * 80)
print("Zebra_ids without gsis_id:")
print("-" * 80)
print(without_gsis['zebra_id'].tolist())

# Check if there's a pattern
print("\n" + "-" * 80)
print("Checking for numerical pattern:")
print("-" * 80)
with_gsis['zebra_int'] = with_gsis['zebra_id']
with_gsis['gsis_int'] = pd.to_numeric(with_gsis['gsis_id'], errors='coerce')
with_gsis = with_gsis[with_gsis['gsis_int'].notna()]

if len(with_gsis) > 0:
    with_gsis['diff'] = with_gsis['zebra_int'] - with_gsis['gsis_int']
    print("\nDifference (zebra_id - gsis_id):")
    print(with_gsis[['zebra_id', 'gsis_id', 'diff']].head(15).to_string(index=False))
    print(f"\nUnique differences: {with_gsis['diff'].nunique()}")
    if with_gsis['diff'].nunique() == 1:
        print(f"CONSTANT OFFSET FOUND: {with_gsis['diff'].iloc[0]}")
