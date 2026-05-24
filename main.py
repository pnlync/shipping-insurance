from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

PIPELINE_STEPS = [
    ("exposure", "Build exposure-level table", "src/build_exposure_table.py"),
    ("eda", "Run exposure-level EDA", "src/eda_exposure_table.py"),
    ("claims", "Build synthetic returns and claims", "src/build_synthetic_claims.py"),
    ("baseline", "Build baseline pricing", "src/build_baseline_pricing.py"),
    ("glm", "Build GLM pricing", "src/build_glm_pricing.py"),
    ("credibility", "Build seller credibility pricing", "src/build_seller_credibility.py"),
    ("backtesting", "Build loss ratio backtesting outputs", "src/build_loss_ratio_backtesting.py"),
    ("stress", "Build stress testing outputs", "src/build_stress_testing.py"),
    ("challenger", "Build XGBoost challenger comparison outputs", "src/build_xgboost_challenger.py"),
    (
        "interpretability",
        "Build XGBoost interpretability outputs",
        "src/build_xgboost_interpretability.py",
    ),
]

PHASES = {
    "phase1": ["exposure", "eda", "claims", "baseline"],
    "phase2": ["glm"],
    "phase3": ["credibility", "backtesting", "stress"],
    "phase4": ["challenger", "interpretability"],
    "all": [step[0] for step in PIPELINE_STEPS],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the shipping insurance pricing project pipeline.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pipeline steps and phases without running anything.",
    )
    parser.add_argument(
        "--run",
        choices=[*PHASES.keys(), *[step[0] for step in PIPELINE_STEPS]],
        help="Run one pipeline step or phase.",
    )
    return parser.parse_args()


def list_steps() -> None:
    print("Pipeline steps:")
    for name, description, script in PIPELINE_STEPS:
        print(f"  {name:12s} {script:38s} {description}")

    print("\nPhases:")
    for phase, steps in PHASES.items():
        print(f"  {phase:12s} {', '.join(steps)}")


def step_lookup() -> dict[str, tuple[str, str, str]]:
    return {name: (name, description, script) for name, description, script in PIPELINE_STEPS}


def run_step(name: str) -> None:
    _, description, script = step_lookup()[name]
    print(f"\n==> {name}: {description}", flush=True)
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / script)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main() -> None:
    args = parse_args()

    if args.list or not args.run:
        list_steps()
        if not args.run:
            print("\nUse --run <step_or_phase> to execute the pipeline.")
        return

    steps = PHASES.get(args.run, [args.run])
    for step in steps:
        run_step(step)


if __name__ == "__main__":
    main()
