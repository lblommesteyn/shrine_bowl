"""
Master Pipeline Runner
======================

Runs all 4 scripts in sequence with error handling and progress tracking.

Usage:
    python run_pipeline.py

Or run individual steps:
    python run_pipeline.py --step 1  # Extract reps only
    python run_pipeline.py --step 2  # Compute scores only
    python run_pipeline.py --step 3  # Validate only
    python run_pipeline.py --step 4  # Generate figures only
"""

import subprocess
import sys
import time
import argparse
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPTS = [
    {
        'name': 'Script 1: Extract Skill 1v1 Reps',
        'path': 'scripts/extract_skill_1v1_reps.py',
        'desc': 'Extracting WR-DB paired reps from session 4',
        'est_time': '2-3 minutes'
    },
    {
        'name': 'Script 2: Compute DB Stickiness',
        'path': 'scripts/compute_db_stickiness.py',
        'desc': 'Computing phase, reaction, recovery scores',
        'est_time': '3-5 minutes'
    },
    {
        'name': 'Script 3: Validate Translation',
        'path': 'scripts/validate_translation.py',
        'desc': 'Validating metric reliability',
        'est_time': '30 seconds'
    },
    {
        'name': 'Script 4: Generate Deck Figures',
        'path': 'scripts/generate_deck_figures.py',
        'desc': 'Generating visualizations for deck',
        'est_time': '1-2 minutes'
    }
]

# ============================================================================
# FUNCTIONS
# ============================================================================

def print_banner(text):
    """Print a formatted banner."""
    print('\n' + '=' * 80)
    print(text.center(80))
    print('=' * 80 + '\n')

def run_script(script_info, step_num):
    """Run a single script with timing and error handling."""
    print_banner(f"STEP {step_num}/4: {script_info['name']}")
    print(f"Description: {script_info['desc']}")
    print(f"Estimated time: {script_info['est_time']}")
    print(f"Running: python {script_info['path']}\n")

    start_time = time.time()

    try:
        # Run script
        result = subprocess.run(
            [sys.executable, script_info['path']],
            capture_output=False,
            text=True,
            check=True
        )

        elapsed = time.time() - start_time
        print(f"\n✓ Step {step_num} completed successfully in {elapsed:.1f}s")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n✗ Step {step_num} failed after {elapsed:.1f}s")
        print(f"Error: {e}")
        return False

    except FileNotFoundError:
        print(f"\n✗ Step {step_num} failed: Script not found at {script_info['path']}")
        return False

def check_outputs():
    """Check if expected output files exist."""
    expected_files = [
        'outputs/reps_skill_1v1.parquet',
        'outputs/db_rep_scores.parquet',
        'outputs/db_player_leaderboard.csv',
        'outputs/validation_metrics.json'
    ]

    print_banner("CHECKING OUTPUTS")

    all_exist = True
    for filepath in expected_files:
        if os.path.exists(filepath):
            size_kb = os.path.getsize(filepath) / 1024
            print(f"✓ {filepath} ({size_kb:.1f} KB)")
        else:
            print(f"✗ {filepath} - NOT FOUND")
            all_exist = False

    return all_exist

def check_figures():
    """Check if figures were generated."""
    figures_dir = 'figures'

    if not os.path.exists(figures_dir):
        print(f"✗ Figures directory not found")
        return False

    figures = [f for f in os.listdir(figures_dir) if f.endswith('.png')]

    if len(figures) == 0:
        print(f"✗ No figures generated")
        return False

    print(f"\n✓ Generated {len(figures)} figures:")
    for fig in sorted(figures):
        size_kb = os.path.getsize(os.path.join(figures_dir, fig)) / 1024
        print(f"  - {fig} ({size_kb:.1f} KB)")

    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Run DB Stickiness Metric Pipeline')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4],
                       help='Run only a specific step (1-4)')
    args = parser.parse_args()

    print_banner("DB STICKINESS METRIC PIPELINE")
    print("Competition: Shrine Bowl × SūmerSports Analytics")
    print("Objective: Build Man Coverage Stickiness metric for DBs")
    print("\nTotal estimated time: 7-11 minutes")

    # Determine which steps to run
    if args.step:
        steps_to_run = [args.step - 1]
        print(f"\nRunning step {args.step} only...")
    else:
        steps_to_run = range(len(SCRIPTS))
        print("\nRunning full pipeline (all 4 steps)...")

    pipeline_start = time.time()
    all_success = True

    # Run scripts
    for i in steps_to_run:
        script = SCRIPTS[i]
        success = run_script(script, i + 1)

        if not success:
            all_success = False
            print(f"\n⚠️  Pipeline stopped due to error in Step {i + 1}")
            print(f"Fix the error and re-run with: python run_pipeline.py --step {i + 1}")
            sys.exit(1)

        # Small pause between steps
        if i < len(SCRIPTS) - 1 and not args.step:
            time.sleep(1)

    pipeline_elapsed = time.time() - pipeline_start

    # Final summary
    print_banner("PIPELINE COMPLETE")
    print(f"Total time: {pipeline_elapsed:.1f}s ({pipeline_elapsed/60:.1f} minutes)")

    # Check outputs
    if not args.step:
        outputs_ok = check_outputs()
        figures_ok = check_figures()

        if outputs_ok and figures_ok:
            print("\n" + "="*80)
            print("✓ ALL CHECKS PASSED".center(80))
            print("="*80)
            print("\nNext steps:")
            print("  1. Review leaderboard: head -20 outputs/db_player_leaderboard.csv")
            print("  2. Check validation: cat outputs/validation_metrics.json")
            print("  3. View figures: ls figures/")
            print("  4. Build 10-slide deck using figures/")
            print("\nSee QUICKSTART.md for deck structure and interpretation guide.")
        else:
            print("\n⚠️  Some outputs missing - check logs above")
            sys.exit(1)
    else:
        print(f"\nStep {args.step} completed successfully.")
        if args.step < 4:
            print(f"Next: python run_pipeline.py --step {args.step + 1}")
        else:
            print("All steps complete! Check outputs/ and figures/")

if __name__ == '__main__':
    main()
