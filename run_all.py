"""Convenience launcher for the validated Yangcheng Lake scripts.

This file does not change the analysis code. It only invokes the existing scripts in order.
The grid search is optional because it is considerably slower.

Usage:
    python run_all.py
    python run_all.py --with-tuning
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def run(script: str) -> None:
    cmd = [sys.executable, script]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-tuning", action="store_true")
    args = parser.parse_args()

    run("src/verify_source.py")
    run("src/reproduce_analysis.py")
    run("src/audit_diagnostics.py")
    run("src/make_figures.py")
    if args.with_tuning:
        run("src/tune_random_forest.py")


if __name__ == "__main__":
    main()
