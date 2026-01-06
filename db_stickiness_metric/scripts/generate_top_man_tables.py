"""
Generate three colored PNG cards for the top man coverage defenders.

Each card mirrors a slide box:
  1. Leaderboard table with top-five named DBs (including simple avatars).
  2. Top-performer summary with a larger avatar and metric callouts.
  3. Component leaders (phase/reaction/recovery) with small face icons.
"""

import os

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
import pyarrow.parquet as pq

FIGURES_DIR = 'figures'
os.makedirs(FIGURES_DIR, exist_ok=True)

LEADERBOARD_PATH = 'outputs/db_player_leaderboard.csv'
PARQUET_PATH = '../data/Shrine Bowl Data/practice_data/2024_West_Practice_3.parquet'
COLLEGE_STATS_PATH = '../data/Shrine Bowl Data/shrine_bowl_players_college_stats.csv'
SESSION_ID = 4


def load_leaderboard():
    leaderboard = pd.read_csv(LEADERBOARD_PATH, dtype={'db_name': str})

    table = pq.read_table(
        PARQUET_PATH,
        columns=['zebra_id', 'gsis_id'],
        filters=[('session_id', '=', SESSION_ID)]
    )
    gsis_mapping = table.to_pandas()
    gsis_mapping['zebra_id'] = gsis_mapping['zebra_id'].astype(str)
    gsis_mapping['gsis_id'] = gsis_mapping['gsis_id'].astype(str)
    gsis_mapping = gsis_mapping.drop_duplicates(subset=['zebra_id']).dropna(subset=['gsis_id'])

    college_stats = pd.read_csv(COLLEGE_STATS_PATH, dtype=str)
    college_stats['college_gsis_id'] = college_stats['college_gsis_id'].astype(str)
    player_info = college_stats[['college_gsis_id', 'player_name', 'position']].drop_duplicates(subset=['college_gsis_id'])

    zebra_to_name = gsis_mapping.merge(
        player_info,
        left_on='gsis_id',
        right_on='college_gsis_id',
        how='left'
    )

    leaderboard = leaderboard.merge(
        zebra_to_name[['zebra_id', 'player_name', 'position']],
        left_on='db_name',
        right_on='zebra_id',
        how='left'
    )
    leaderboard['display_name'] = leaderboard.apply(
        lambda row: row['player_name']
        if pd.notna(row['player_name'])
        else f"Unknown DB #{row['db_name'][-4:]}",
        axis=1
    )
    leaderboard['position'] = leaderboard['position'].fillna('DB')
    return leaderboard


def build_view_data(leaderboard):
    named = leaderboard[
        leaderboard['player_name'].notna() &
        (leaderboard['n_reps'] >= 5)
    ].copy()
    named.sort_values('stickiness_bayesian', ascending=False, inplace=True)
    return named.head(5)


def create_leaderboard_card(table_data):
    fig = plt.figure(figsize=(7.4, 6), facecolor='white')
    fig.text(0.5, 0.96, 'Overall Stickiness Leaderboard', ha='center', fontsize=18, fontweight='bold')
    table_ax = fig.add_axes([0.02, 0.25, 0.96, 0.62])
    table_ax.axis('off')

    headers = ['Rank', 'Player (Pos)', 'Reps', 'Bayesian Stickiness']
    rows = []
    for idx, row in enumerate(table_data.itertuples()):
        rows.append([
            f"{idx + 1}",
            f"{row.display_name} ({row.position})",
            f"{int(row.n_reps)} reps",
            f"{row.stickiness_bayesian:.3f}",
        ])

    table = table_ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc='center',
        colLoc='center',
        loc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1, 2.15)

    for (row_idx, col_idx), cell in table.get_celld().items():
        if row_idx > 0:
            cell.set_height(cell.get_height() * 1.1)

    header_color = '#7EA5D4'
    row_colors = ['#F7F9FE', '#E8EFF9']
    for (row_idx, col_idx), cell in table.get_celld().items():
        cell.set_linewidth(1.2)
        cell.set_edgecolor('#2C3E58')
        if row_idx == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=11)
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[(row_idx - 1) % len(row_colors)])
            cell.set_text_props(color='#1F3970', fontsize=10)

    footnote = (
        "Tracking-only stickiness, Bayesian-adjusted for low sample size. "
        "Only defenders whose zebra IDs resolve to a player name are shown."
    )
    fig.text(0.5, 0.08, footnote, ha='center', fontsize=9, color='#223753')

    output_path = os.path.join(FIGURES_DIR, 'top_man_leaderboard.png')
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {output_path}")


def main():
    leaderboard = load_leaderboard()
    top_table = build_view_data(leaderboard)

    if top_table.empty:
        print("No named players with 5+ reps to render.")
        return

    create_leaderboard_card(top_table)


if __name__ == '__main__':
    main()
