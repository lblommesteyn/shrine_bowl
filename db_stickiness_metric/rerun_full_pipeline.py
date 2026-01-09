"""
Re-run Full Pipeline
====================

Re-run all 4 scripts after fixing position filtering and minimum reps.

Changes:
1. Filter out QBs/OL/DL from extraction (keep only WR/TE/CB/S/DB positions)
2. Add minimum 5 reps filter for leaderboard
3. Prefer players with matched names in visualizations
"""

import subprocess
import sys
import os

print('=' * 80)
print('RE-RUNNING FULL DB STICKINESS PIPELINE')
print('=' * 80)

# Change to scripts directory
os.chdir('scripts')

scripts = [
    ('extract_skill_1v1_reps.py', 'Extracting WR-DB reps (with position filtering)'),
    ('compute_db_stickiness.py', 'Computing stickiness scores'),
    ('validate_translation.py', 'Validating metric'),
    ('generate_deck_figures.py', 'Generating deck figures')
]

for script, description in scripts:
    print('\n' + '=' * 80)
    print(f'RUNNING: {script}')
    print(f'Description: {description}')
    print('=' * 80)

    result = subprocess.run([sys.executable, script], capture_output=False)

    if result.returncode != 0:
        print(f'\nERROR: {script} failed with return code {result.returncode}')
        print('Stopping pipeline.')
        sys.exit(1)

    print(f'\n✓ {script} completed successfully')

print('\n' + '=' * 80)
print('PIPELINE COMPLETE')
print('=' * 80)
print('\nAll outputs saved to ../outputs/')
print('All figures saved to ../outputs/deck_figures/')
