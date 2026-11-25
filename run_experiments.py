import argparse

from experiments.runner import ExperimentConfig, run_experiments


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Griductive benchmark experiments (Member 3)."
    )
    parser.add_argument(
        "--suite",
        default="puzzles/benchmark",
        help="Path to benchmark directory or single puzzle JSON",
    )
    parser.add_argument(
        "--output",
        default="outputs/experiments",
        help="Directory for results.csv, manifest.json, and summary.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-solve/analyze timeout budget in seconds",
    )
    parser.add_argument(
        "--case-timeout",
        type=float,
        default=None,
        help="Whole-case deadline in seconds (defaults to max(timeout*5, 30))",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of repeated runs per case",
    )
    parser.add_argument(
        "--config",
        default="dpll_baseline",
        help="Solver configuration name",
    )
    parser.add_argument(
        "--no-subprocess",
        action="store_true",
        help="Run cases in-process instead of isolated child processes",
    )
    args = parser.parse_args()

    config = ExperimentConfig(
        suite=args.suite,
        output=args.output,
        timeout_s=args.timeout,
        repeats=args.repeats,
        configuration=args.config,
        case_timeout_s=args.case_timeout,
        use_subprocess=not args.no_subprocess,
    )
    run_experiments(config)


if __name__ == "__main__":
    main()