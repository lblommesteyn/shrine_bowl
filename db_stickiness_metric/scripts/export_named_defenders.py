"""
Export a CSV of leaderboard rows that have mapped player names (defensive DBs only).
"""

import os

import pandas as pd
import pyarrow.parquet as pq

LEADERBOARD_PATH = 'outputs/db_player_leaderboard.csv'
OUTPUT_PATH = 'outputs/db_player_leaderboard_named_defensive.csv'
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


def load_player_lookup():
    stats = pd.read_csv(COLLEGE_STATS_PATH, dtype=str)
    stats['college_gsis_id'] = stats['college_gsis_id'].str.strip()
    lookup = stats[['college_gsis_id', 'player_name', 'position']].drop_duplicates('college_gsis_id')
    lookup = lookup.set_index('college_gsis_id')
    return lookup.to_dict(orient='index')


def export_named_defenders():
    if not os.path.exists(LEADERBOARD_PATH):
        raise FileNotFoundError(f'{LEADERBOARD_PATH} not found')

    leaderboard = pd.read_csv(LEADERBOARD_PATH, dtype={'db_name': str})
    zebra_ids = leaderboard['db_name'].tolist()
    gsis_map = resolve_gsis(zebra_ids)
    player_lookup = load_player_lookup()

    leaderboard['gsis_id'] = leaderboard['db_name'].map(lambda zid: gsis_map.get(zid))

    def lookup_field(zid, field):
        gsis = gsis_map.get(zid)
        if gsis and gsis in player_lookup:
            return player_lookup[gsis].get(field, '')
        return ''

    leaderboard['player_name'] = leaderboard['db_name'].map(lambda zid: lookup_field(zid, 'player_name'))
    leaderboard['college_position'] = leaderboard['db_name'].map(lambda zid: lookup_field(zid, 'position'))

    named = leaderboard[leaderboard['player_name'].astype(bool)].copy()
    named.sort_values('stickiness_bayesian', ascending=False, inplace=True)
    named.reset_index(drop=True, inplace=True)
    named['def_rank'] = (named.index + 1).astype(int)

    columns = [
        'def_rank',
        'rank',
        'db_name',
        'player_name',
        'college_position',
        'n_reps',
        'stickiness_bayesian',
        'avg_phase',
        'avg_reaction',
        'avg_recovery'
    ]
    named = named[columns]
    named.to_csv(OUTPUT_PATH, index=False)
    print(f'Wrote {len(named)} rows to {OUTPUT_PATH} (defensive players with names)')


if __name__ == '__main__':
    export_named_defenders()
