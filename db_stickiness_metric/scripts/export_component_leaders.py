"""
Export the top-3 named defenders for each component (phase/reaction/recovery).
"""

import pandas as pd

LEADERBOARD_PATH = 'outputs/db_player_leaderboard.csv'
OUTPUT_PATH = 'outputs/component_leaders_named_defensive.csv'


def export_component_leaders():
    leaderboard = pd.read_csv(LEADERBOARD_PATH, dtype={'db_name': str})
    if 'player_name' not in leaderboard.columns:
        raise ValueError('player_name column missing from leaderboard; run annotate_leaderboard.py first.')

    leaderboard['player_name_clean'] = leaderboard['player_name'].fillna('').astype(str).str.strip()
    filtered = leaderboard[
        (leaderboard['player_name_clean'] != '') &
        (leaderboard['n_reps'] >= 5)
    ].copy()

    components = {
        'avg_phase': 'phase',
        'avg_reaction': 'trigger',
        'avg_recovery': 'close'
    }

    rows = []
    for comp_col, label in components.items():
        top3 = filtered.nlargest(3, comp_col)
        for rank, (_, row) in enumerate(top3.iterrows(), start=1):
            rows.append({
                'component': label,
                'component_rank': rank,
                'player_name': row['player_name_clean'],
                'position': row.get('position', ''),
                'db_name': row['db_name'],
                'value': row[comp_col]
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f'Wrote component leaders to {OUTPUT_PATH}')


if __name__ == '__main__':
    export_component_leaders()
