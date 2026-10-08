"""Core reproduction script for:

Tang K, Meng X, Zheng Y. "Audit before automation: a rule-benchmarked protocol for
machine learning in threshold-based water-quality classification, with evidence from
Yangcheng Lake, China."

This script reproduces the core quantities used throughout the manuscript:
- source-record and analysis-set counts;
- R4/R5 regulatory-rule reconstruction;
- tie structure and monthly binding shares;
- random-forest feature screening, held-out performance, repeated-split uncertainty;
- ablation models and extreme-value sensitivity.

Audit-specific D1-D4 diagnostics (audit-set mechanisms, McNemar tests, Shapley/equal-credit
attribution and rule-benchmarked temporal validation) are implemented in
``src/audit_diagnostics.py``.

Usage
-----
    python src/reproduce_analysis.py --csv data/yangcheng_lake_center_station_3187.csv
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

# -----------------------------
# Reproducibility constants
# -----------------------------
SEED = 42

TIME_COL = "监测时间"
CLASS_COL = "水质"

INDICATORS = [
    "水温", "pH", "溶解氧", "电导率", "浊度", "高锰酸盐指数",
    "氨氮", "总磷", "总氮", "叶绿素α", "藻密度",
]
RULE_SOURCE_COLS = ["溶解氧", "高锰酸盐指数", "氨氮", "总磷"]
RETAINED = ["总磷", "高锰酸盐指数", "pH"]
NON_RULE = ["水温", "电导率", "浊度", "叶绿素α", "藻密度", "总氮"]

BEST = dict(n_estimators=300, max_depth=None, min_samples_split=5, min_samples_leaf=1)

LIMITS_UP = {
    "高锰酸盐指数": [2, 4, 6, 10, 15],
    "氨氮": [0.15, 0.5, 1.0, 1.5, 2.0],
    "总磷": [0.01, 0.025, 0.05, 0.1, 0.2],
    "总氮": [0.2, 0.5, 1.0, 1.5, 2.0],
}
LIMITS_DO = [7.5, 6, 5, 3, 2]
TP_LIMITS = np.array(LIMITS_UP["总磷"], dtype=float)

# Keep the manuscript's merged I+II outcome convention.
CLASS_CODE_RAW = {"Ⅰ": 1, "Ⅱ": 2, "Ⅲ": 3, "Ⅳ": 4, "Ⅴ": 5, "劣Ⅴ": 6}
LABELS = [2, 3, 4, 5, 6]
LABEL_TEXT = {2: "Class II", 3: "Class III", 4: "Class IV", 5: "Class V", 6: "Below Class V"}

BINDER_NAMES = np.array(["NH3-N", "DO", "CODMn", "TP"], dtype=object)
FORCED_ORDER = ["NH3-N", "DO", "CODMn", "TP"]


@dataclass(frozen=True)
class SplitData:
    train_idx: np.ndarray
    test_idx: np.ndarray


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _to_numeric(series: pd.Series) -> pd.Series:
    s = _clean_text(series).replace({"": np.nan, "--": np.nan, "UNKNOWN": np.nan})
    return pd.to_numeric(s, errors="coerce")


def decimal_places(value: str) -> int | None:
    """Return the number of decimal places in the source string, or None if not numeric."""
    s = str(value).strip()
    if s in {"", "--", "UNKNOWN", "nan", "None"}:
        return None
    try:
        float(s)
    except ValueError:
        return None
    if "e" in s.lower():
        # Scientific notation is not treated as 0.01-resolution publication.
        return None
    return len(s.split(".", 1)[1]) if "." in s else 0


def load_archive(csv_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two-row-header MoonAPI export and build the 8173-record analysis set.

    The first returned frame is the source archive after parsing/sorting. The second is the
    analysis frame after dropping UNKNOWN classes and performing the manuscript's index-based
    linear interpolation. Source values and observation flags are retained in ``source_*`` and
    ``observed_*`` columns so audit diagnostics can distinguish observed from imputed values.
    """
    raw_text = pd.read_csv(csv_path, skiprows=[1], dtype=str, keep_default_na=False)
    raw_text.columns = [str(c).strip() for c in raw_text.columns]

    required = [TIME_COL, CLASS_COL] + INDICATORS
    missing = [c for c in required if c not in raw_text.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    raw = raw_text.copy()
    raw[TIME_COL] = pd.to_datetime(raw[TIME_COL], errors="coerce")
    if raw[TIME_COL].isna().any():
        raise ValueError(f"Could not parse {raw[TIME_COL].isna().sum()} monitoring timestamps")

    for col in INDICATORS:
        raw[f"raw_{col}"] = _clean_text(raw_text[col])
        raw[f"source_{col}"] = _to_numeric(raw_text[col])
        raw[f"observed_{col}"] = raw[f"source_{col}"].notna()

    raw[CLASS_COL] = _clean_text(raw_text[CLASS_COL])
    raw["source_row"] = np.arange(1, len(raw) + 1)
    raw = raw.sort_values(TIME_COL).reset_index(drop=True)

    valid_class = raw[CLASS_COL].isin(CLASS_CODE_RAW)
    df = raw.loc[valid_class].copy().reset_index(drop=True)
    df["obs_raw"] = df[CLASS_COL].map(CLASS_CODE_RAW).astype(int)
    df["obs"] = df["obs_raw"].clip(lower=2).astype(int)
    df["year"] = df[TIME_COL].dt.year.astype(int)
    df["month"] = df[TIME_COL].dt.month.astype(int)

    # Index-based interpolation exactly as described in the manuscript. Edge gaps take the
    # nearest valid value (ffill/bfill); all original values remain in source_* columns.
    for col in INDICATORS:
        s = df[f"source_{col}"].astype(float)
        s = s.interpolate(method="linear")
        s = s.ffill().bfill()
        if s.isna().any():
            raise ValueError(f"Indicator {col} remains entirely/partly missing after interpolation")
        df[col] = s

    return raw, df


def grade_up(value: float, limits: Iterable[float]) -> int:
    for cls, limit in zip([1, 2, 3, 4, 5], limits):
        if value <= limit:
            return cls
    return 6


def grade_do(value: float) -> int:
    for cls, limit in zip([1, 2, 3, 4, 5], LIMITS_DO):
        if value >= limit:
            return cls
    return 6


def reconstruct(df: pd.DataFrame) -> pd.DataFrame:
    """Add R4, R5, TN-rule sensitivity and binding sets to an analysis frame."""
    out = df.copy()
    grades = pd.DataFrame({
        "NH3-N": out["氨氮"].apply(lambda v: grade_up(v, LIMITS_UP["氨氮"])),
        "DO": out["溶解氧"].apply(grade_do),
        "CODMn": out["高锰酸盐指数"].apply(lambda v: grade_up(v, LIMITS_UP["高锰酸盐指数"])),
        "TP": out["总磷"].apply(lambda v: grade_up(v, LIMITS_UP["总磷"])),
    }, index=out.index)

    for name in grades.columns:
        out[f"grade_{name}"] = grades[name].astype(int)

    worst_unmerged = grades.max(axis=1).astype(int)
    out["r4_unmerged"] = worst_unmerged
    out["r4"] = worst_unmerged.clip(lower=2).astype(int)

    binders = [frozenset(BINDER_NAMES[row == w]) for row, w in zip(grades.to_numpy(), worst_unmerged)]
    out["binders"] = binders
    out["n_tied"] = [len(b) for b in binders]
    out["binder_forced"] = [next(x for x in FORCED_ORDER if x in b) for b in binders]

    source_ph = out["source_pH"]
    out["pH_excursion_observed"] = out["observed_pH"] & ((source_ph < 6) | (source_ph > 9))
    out["pH_excursion_filled"] = (out["pH"] < 6) | (out["pH"] > 9)

    out["r5"] = out["r4"]
    out.loc[out["pH_excursion_observed"], "r5"] = 6
    out["r5"] = out["r5"].astype(int)

    out["grade_TN"] = out["总氮"].apply(lambda v: grade_up(v, LIMITS_UP["总氮"])).astype(int)
    out["r4_with_TN"] = np.maximum(out["r4"], out["grade_TN"]).astype(int)

    # Backward-compatible alias for earlier scripts.
    out["recon"] = out["r4"]
    return out


def primary_split(df: pd.DataFrame, seed: int = SEED) -> SplitData:
    idx = df.index.to_numpy()
    train_idx, test_idx = train_test_split(
        idx, test_size=0.20, random_state=seed, stratify=df.loc[idx, "obs"].to_numpy()
    )
    return SplitData(np.asarray(train_idx), np.asarray(test_idx))


def build_forest(seed: int = SEED) -> RandomForestClassifier:
    return RandomForestClassifier(random_state=seed, n_jobs=-1, **BEST)


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return 100 * (centre - half), 100 * (centre + half)


def missing_table(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(raw)
    for col in INDICATORS:
        invalid = int((~raw[f"observed_{col}"]).sum())
        rows.append({"variable": col, "invalid_or_missing_n": invalid,
                     "rate_percent": 100 * invalid / n, "valid_n": n - invalid})
    invalid_class = int((~raw[CLASS_COL].isin(CLASS_CODE_RAW)).sum())
    rows.append({"variable": "water-quality class", "invalid_or_missing_n": invalid_class,
                 "rate_percent": 100 * invalid_class / n, "valid_n": n - invalid_class})
    return pd.DataFrame(rows)


def binding_monthly(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tp_cod = frozenset(["TP", "CODMn"])
    for month in range(1, 13):
        g = df[df["month"] == month]
        n = len(g)
        rows.append({
            "month": month,
            "n": n,
            "unique_TP": 100 * sum(b == frozenset(["TP"]) for b in g["binders"]) / n,
            "unique_CODMn": 100 * sum(b == frozenset(["CODMn"]) for b in g["binders"]) / n,
            "unique_DO": 100 * sum(b == frozenset(["DO"]) for b in g["binders"]) / n,
            "TP_CODMn_tie": 100 * sum(b == tp_cod for b in g["binders"]) / n,
            "other_tie": 100 * sum((len(b) >= 2) and (b != tp_cod) for b in g["binders"]) / n,
        })
    return pd.DataFrame(rows)


def feature_screening(df: pd.DataFrame, train_idx: np.ndarray) -> pd.DataFrame:
    X = df.loc[train_idx, INDICATORS]
    y = df.loc[train_idx, "obs"]
    screen = RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1).fit(X, y)
    gini = pd.Series(screen.feature_importances_, index=INDICATORS)

    folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
    perm = np.zeros(len(INDICATORS), dtype=float)
    for tr, va in folds.split(X, y):
        model = RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1)
        model.fit(X.iloc[tr], y.iloc[tr])
        p = permutation_importance(
            model, X.iloc[va], y.iloc[va], n_repeats=10, random_state=SEED,
            scoring="accuracy", n_jobs=-1,
        )
        perm += p.importances_mean
    perm = pd.Series(perm / 5, index=INDICATORS)

    out = pd.DataFrame({"indicator": INDICATORS,
                        "gini_importance": gini.loc[INDICATORS].values,
                        "permutation_importance": perm.loc[INDICATORS].values})
    out["retained"] = (out["gini_importance"] >= 0.05) | (out["permutation_importance"] >= 0.01)
    return out


def primary_model_results(df: pd.DataFrame, split: SplitData) -> tuple[pd.DataFrame, np.ndarray]:
    model = build_forest()
    model.fit(df.loc[split.train_idx, RETAINED], df.loc[split.train_idx, "obs"])
    pred = model.predict(df.loc[split.test_idx, RETAINED])
    y = df.loc[split.test_idx, "obs"].to_numpy()

    precision, recall, f1, support = precision_recall_fscore_support(
        y, pred, labels=LABELS, zero_division=0
    )
    rows = []
    for i, label in enumerate(LABELS):
        successes = int(round(recall[i] * support[i]))
        lo, hi = wilson(successes, int(support[i]))
        rows.append({
            "class": LABEL_TEXT[label], "support": int(support[i]),
            "precision_percent": 100 * precision[i], "recall_percent": 100 * recall[i],
            "f1_percent": 100 * f1[i], "recall_ci_low": lo, "recall_ci_high": hi,
        })
    return pd.DataFrame(rows), pred


def repeated_split_summary(df: pd.DataFrame) -> pd.DataFrame:
    metric = {"accuracy": [], "weighted_f1": [], "macro_f1": [],
              "recall_class_II": [], "recall_class_V": [], "recall_below_V": []}
    for seed in range(50):
        split = primary_split(df, seed=seed)
        model = build_forest(seed=seed)
        model.fit(df.loc[split.train_idx, RETAINED], df.loc[split.train_idx, "obs"])
        pred = model.predict(df.loc[split.test_idx, RETAINED])
        y = df.loc[split.test_idx, "obs"].to_numpy()
        metric["accuracy"].append(accuracy_score(y, pred))
        metric["weighted_f1"].append(f1_score(y, pred, average="weighted"))
        metric["macro_f1"].append(f1_score(y, pred, average="macro"))
        _, rec, _, _ = precision_recall_fscore_support(y, pred, labels=LABELS, zero_division=0)
        metric["recall_class_II"].append(rec[0])
        metric["recall_class_V"].append(rec[3])
        metric["recall_below_V"].append(rec[4])

    rows = []
    for name, vals in metric.items():
        v = np.asarray(vals)
        rows.append({"metric": name, "mean": v.mean(), "p2_5": np.percentile(v, 2.5),
                     "p97_5": np.percentile(v, 97.5)})
    return pd.DataFrame(rows)


def ablation_table(df: pd.DataFrame, split: SplitData) -> pd.DataFrame:
    feature_sets = {
        "all_11_indicators": INDICATORS,
        "retained_TP_CODMn_pH": RETAINED,
        "TP_only": ["总磷"],
        "retained_without_TP": ["高锰酸盐指数", "pH"],
        "non_rule_indicators": NON_RULE,
    }
    y_test = df.loc[split.test_idx, "obs"].to_numpy()
    r4_acc = accuracy_score(y_test, df.loc[split.test_idx, "r4"])
    rows = [{"feature_set": "R4_no_model", "accuracy": r4_acc,
             "difference_from_R4_pp": 0.0}]
    for name, cols in feature_sets.items():
        model = build_forest()
        model.fit(df.loc[split.train_idx, cols], df.loc[split.train_idx, "obs"])
        pred = model.predict(df.loc[split.test_idx, cols])
        acc = accuracy_score(y_test, pred)
        rows.append({"feature_set": name, "accuracy": acc,
                     "difference_from_R4_pp": 100 * (acc - r4_acc)})
    return pd.DataFrame(rows)


def extreme_value_sensitivity(df: pd.DataFrame) -> dict[str, float]:
    extreme = ((df["总磷"] > 0.4) | (df["总氮"] > 5) |
               (df["高锰酸盐指数"] > 15) | (df["浊度"] > 300))
    sub = df.loc[~extreme].copy().reset_index(drop=True)
    split = primary_split(sub)
    model = build_forest()
    model.fit(sub.loc[split.train_idx, RETAINED], sub.loc[split.train_idx, "obs"])
    pred = model.predict(sub.loc[split.test_idx, RETAINED])
    y = sub.loc[split.test_idx, "obs"]
    return {
        "extreme_records": int(extreme.sum()),
        "remaining_n": len(sub),
        "r4_exact_agreement": float((sub["r4"] == sub["obs"]).mean()),
        "r4_within_one_class": float(((sub["r4"] - sub["obs"]).abs() <= 1).mean()),
        "heldout_accuracy": float(accuracy_score(y, pred)),
        "weighted_f1": float(f1_score(y, pred, average="weighted")),
    }


def save_analysis_set(df: pd.DataFrame, outdir: str) -> None:
    keep = [TIME_COL, "source_row", "year", "month"] + INDICATORS + [
        "obs", "r4", "r5", "r4_with_TN", "n_tied", "binder_forced",
        "pH_excursion_observed", "pH_excursion_filled",
    ]
    out = df[keep].copy()
    out["binders"] = ["|".join(sorted(b)) for b in df["binders"]]
    out.to_csv(os.path.join(outdir, "analysis_set.csv"), index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    raw, df = load_archive(args.csv)
    df = reconstruct(df)

    print(f"retrieved records                 : {len(raw)}")
    print(f"analysis set                      : {len(df)}")
    print(f"R4 exact agreement               : {(df['r4'] == df['obs']).mean() * 100:.2f}%")
    print(f"R5 exact agreement               : {(df['r5'] == df['obs']).mean() * 100:.2f}%")
    print(f"R4 + TN exact agreement          : {(df['r4_with_TN'] == df['obs']).mean() * 100:.2f}%")
    print(f"worst-grade ties                 : {(df['n_tied'] >= 2).sum()} ({(df['n_tied'] >= 2).mean()*100:.1f}%)")

    missing_table(raw).to_csv(os.path.join(args.outdir, "table_missing_entries.csv"), index=False)
    binding_monthly(df).to_csv(os.path.join(args.outdir, "table_monthly_binding.csv"), index=False)

    split = primary_split(df)
    screening = feature_screening(df, split.train_idx)
    screening.to_csv(os.path.join(args.outdir, "feature_importance.csv"), index=False)

    folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
    cv = cross_val_score(build_forest(), df.loc[split.train_idx, RETAINED],
                         df.loc[split.train_idx, "obs"], cv=folds, scoring="accuracy")
    print(f"five-fold CV accuracy            : {cv.mean()*100:.3f}% (sample SD {cv.std(ddof=1)*100:.3f} pp)")

    class_perf, pred = primary_model_results(df, split)
    class_perf.to_csv(os.path.join(args.outdir, "class_specific_performance.csv"), index=False)
    y_test = df.loc[split.test_idx, "obs"].to_numpy()
    print(f"held-out accuracy                : {accuracy_score(y_test, pred)*100:.3f}%")
    print(f"held-out weighted F1             : {f1_score(y_test, pred, average='weighted')*100:.2f}%")
    print(f"held-out macro F1                : {f1_score(y_test, pred, average='macro')*100:.2f}%")

    ablation_table(df, split).to_csv(os.path.join(args.outdir, "ablation_accuracy.csv"), index=False)
    repeated_split_summary(df).to_csv(os.path.join(args.outdir, "repeated_split_summary.csv"), index=False)

    sens = pd.DataFrame([extreme_value_sensitivity(df)])
    sens.to_csv(os.path.join(args.outdir, "extreme_value_sensitivity.csv"), index=False)

    save_analysis_set(df, args.outdir)
    print(f"wrote core reproduction outputs to {args.outdir}/")


if __name__ == "__main__":
    main()
