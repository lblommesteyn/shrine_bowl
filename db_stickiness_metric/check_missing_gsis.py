import pandas as pd

df = pd.read_csv('../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv')

missing_gsis = [336893, 316873, 328257, 301317, 310211, 330293, 326095, 405914, 361758, 347975, 339980]

print('Checking if these gsis_ids exist in college stats:')
print('=' * 80)
for gid in missing_gsis:
    match = df[df['college_gsis_id'] == gid]
    if len(match) > 0:
        print(f'{gid}: FOUND - {match.iloc[0]["player_name"]} ({match.iloc[0]["position"]})')
    else:
        print(f'{gid}: NOT FOUND in college stats')

print('\n' + '=' * 80)
print('Summary:')
print(f'Total missing: {len(missing_gsis)}')
print(f'Found: {sum(1 for gid in missing_gsis if len(df[df["college_gsis_id"] == gid]) > 0)}')
print(f'Not found: {sum(1 for gid in missing_gsis if len(df[df["college_gsis_id"] == gid]) == 0)}')
