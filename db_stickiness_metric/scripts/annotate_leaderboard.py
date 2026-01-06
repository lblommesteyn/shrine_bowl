"""
Annotate db_player_leaderboard.csv with the player names we can resolve.
"""

import pandas as pd
import pyarrow.parquet as pq

LEADERBOARD_PATH = 'outputs/db_player_leaderboard.csv'
PARQUET_PATHS = [
    '../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet',
    '../data/Shrine Bowl Data/practice_data/2022_West_Practice_2.snappy.parquet'
]
COLLEGE_STATS_PATH = '../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'


def resolve_gsis(zebra_ids):
    samples = []
    for path in PARQUET_PATHS:
        table = pq.read_table(
            path,
            columns=['zebra_id', 'gsis_id'],
            filters=[('zebra_id', 'in', zebra_ids)]
        )
        samples.append(table.to_pandas())

    full = pd.concat(samples, ignore_index=True)
    full = full.drop_duplicates(['zebra_id', 'gsis_id'])
    full['gsis_id'] = full['gsis_id'].astype('Int64')

    mapping = {}
    for zebra in zebra_ids:
        subset = full[full['zebra_id'] == zebra]['gsis_id'].dropna()
        mapping[zebra] = str(subset.iloc[0]) if not subset.empty else None

    return mapping


def load_name_lookup():
    stats = pd.read_csv(COLLEGE_STATS_PATH, dtype=str)
    stats['college_gsis_id'] = stats['college_gsis_id'].str.strip()
    lookup = stats[['college_gsis_id', 'player_name']].drop_duplicates('college_gsis_id')
    lookup = lookup.set_index('college_gsis_id')['player_name']
    return lookup.to_dict()


def annotate_leaderboard():
    leaderboard = pd.read_csv(LEADERBOARD_PATH, dtype={'db_name': str})
    zebra_ids = leaderboard['db_name'].unique().tolist()
    gsis_map = resolve_gsis(zebra_ids)
    name_map = load_name_lookup()

    def lookup_name(zebra):
        gsis = gsis_map.get(zebra)
        if gsis and gsis in name_map:
            return name_map[gsis]
        return ''

    leaderboard['player_name'] = leaderboard['db_name'].map(lookup_name)
    cols = leaderboard.columns.tolist()
    if 'player_name' in cols:
        cols.remove('player_name')
    cols.insert(2, 'player_name')  # insert after db_name
    leaderboard = leaderboard[cols]
    leaderboard.to_csv(LEADERBOARD_PATH, index=False)
    print(f'Annotated {len(leaderboard)} rows with player names (missing names left blank).')


if __name__ == '__main__':
    annotate_leaderboard()
