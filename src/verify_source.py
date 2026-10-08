"""Verify a local MoonAPI CSV against the file used in the manuscript.

The source data are not redistributed. This utility checks whether a locally obtained copy is
byte-identical to the analyzed file and reports basic structural metadata.

Usage
-----
    python src/verify_source.py --csv data/yangcheng_lake_center_station_3187.csv
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

import pandas as pd

EXPECTED_SHA256 = "3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642"
EXPECTED_MD5 = "1162cf2a503404b8d615f1f19b0a809b"
EXPECTED_SIZE = 1_656_680
EXPECTED_RECORDS = 8516
EXPECTED_START = pd.Timestamp("2020-12-17")
EXPECTED_END = pd.Timestamp("2026-01-05 23:59:59.999999")


def digest(path: str, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--non-strict", action="store_true",
                        help="report mismatches but return exit code 0")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: file not found: {args.csv}", file=sys.stderr)
        sys.exit(2)

    sha = digest(args.csv, "sha256")
    md5 = digest(args.csv, "md5")
    size = os.path.getsize(args.csv)

    # Row 2 contains units and is skipped by the analysis scripts.
    df = pd.read_csv(args.csv, skiprows=[1], dtype=str, keep_default_na=False)
    n = len(df)
    if "监测时间" not in df.columns:
        print("ERROR: 监测时间 column not found", file=sys.stderr)
        sys.exit(2)
    t = pd.to_datetime(df["监测时间"], errors="coerce")

    checks = {
        "SHA-256": sha == EXPECTED_SHA256,
        "MD5": md5 == EXPECTED_MD5,
        "file size": size == EXPECTED_SIZE,
        "record count": n == EXPECTED_RECORDS,
        "timestamp parse": t.notna().all(),
        "date range": t.notna().all() and t.min() >= EXPECTED_START and t.max() <= EXPECTED_END,
    }

    print(f"SHA-256 : {sha} {'PASS' if checks['SHA-256'] else 'MISMATCH'}")
    print(f"MD5     : {md5} {'PASS' if checks['MD5'] else 'MISMATCH'}")
    print(f"Size    : {size:,} bytes {'PASS' if checks['file size'] else 'MISMATCH'}")
    print(f"Records : {n} {'PASS' if checks['record count'] else 'MISMATCH'}")
    if t.notna().any():
        print(f"Dates   : {t.min()} to {t.max()}")

    all_ok = all(checks.values())
    print("RESULT  : " + ("byte-identical / structurally consistent with analyzed file" if all_ok
                           else "not identical to the analyzed file; inspect differences before use"))
    if not all_ok and not args.non_strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
