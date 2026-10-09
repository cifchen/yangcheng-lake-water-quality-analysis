"""D1-D4 audit diagnostics for the audit-before-automation manuscript.

Implements:
D1  Audit-set decomposition and year-specific R4/R5 agreement.
D2  Rule-benchmarked skill score (SSR) and exact McNemar tests.
D3  Order-invariant equal-credit (Shapley) attribution and all 24 forced priority orders.
D4  Rare-class reliability and rule-benchmarked temporal validation / label-drift diagnostics.

Usage
-----
    python src/audit_diagnostics.py --csv data/yangcheng_lake_center_station_3187.csv
"""

from __future__ import annotations

import argparse
import itertools
import os
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import accuracy_score

from reproduce_analysis import (
    BEST, BINDER_NAMES, FORCED_ORDER, INDICATORS, LABELS, NON_RULE, RETAINED, SEED,
    TIME_COL, TP_LIMITS, build_forest, load_archive, primary_split, reconstruct,
)


def exact_mcnemar(correct_a: np.ndarray, correct_b: np.ndarray) -> tuple[int, int, float]:
    """Exact two-sided McNemar test.

    Returns (A_only_correct, B_only_correct, p_value).
    """
    a_only = int(np.sum(correct_a & ~correct_b))
    b_only = int(np.sum(~correct_a & correct_b))
    n = a_only + b_only
    p = 1.0 if n == 0 else float(binomtest(min(a_only, b_only), n=n, p=0.5, alternative="two-sided").pvalue)
    return a_only, b_only, p


def skill_score(model_errors: int, rule_errors: int) -> float:
    if rule_errors == 0:
        return np.nan
    return 1.0 - model_errors / rule_errors


def _numeric_decimals(value: float) -> float:
    """Decimals actually carried by a published value (trailing zeros ignored)."""
    if pd.isna(value) or value == 0:
        return np.nan
    for d in range(7):
        if abs(round(float(value), d) - float(value)) < 1e-9:
            return d
    return 7


def coarse_tp_months(df: pd.DataFrame) -> pd.Series:
    """Calendar months in which TP was published at 0.01 mg/L resolution.

    The CSV pads every value to five decimals, so the resolution cannot be read from the
    string of a single record. A month counts as coarse when no TP value in that month
    carries more than two decimals.
    """
    month = df[TIME_COL].dt.to_period("M")
    dps = df["source_总磷"].apply(_numeric_decimals)
    return dps.groupby(month.values).max() <= 2


def tp_limit_in_rounding_interval(value: float) -> bool:
    """A class limit lies in [value - 0.005, value + 0.005) for a value published at 0.01 mg/L."""
    if pd.isna(value):
        return False
    x = float(value)
    return bool(np.any((x - 0.005 <= TP_LIMITS) & (TP_LIMITS < x + 0.005)))


def tp_near_limit(value: float, frac: float = 0.05) -> bool:
    if pd.isna(value):
        return False
    for limit in TP_LIMITS:
        if abs(float(value) - limit) <= frac * limit + 1e-12:
            return True
    return False


def decompose_audit_set(df: pd.DataFrame) -> pd.DataFrame:
    """Sequentially assign mechanisms A-E exactly as specified in manuscript Section 2.5."""
    audit = df.loc[df["r4"] != df["obs"]].copy()
    audit["distance"] = (audit["obs"] - audit["r4"]).abs().astype(int)
    audit["tier"] = np.where(audit["distance"] == 1, "one_class", ">=2_classes")
    audit["direction"] = np.where(audit["obs"] > audit["r4"], "archived_worse", "archived_better")
    audit["mechanism"] = "E_unexplained"

    # A: observed pH excursion, archived Below V, reconstructed above Below V.
    a = audit["pH_excursion_observed"] & (audit["obs"] == 6) & (audit["r4"] < 6)
    audit.loc[a, "mechanism"] = "A_pH_excursion"

    # B: source archive had an invalid/missing fixed R4 indicator. Sequential: only unassigned.
    missing_rule = np.zeros(len(audit), dtype=bool)
    for col in ["溶解氧", "高锰酸盐指数", "氨氮", "总磷"]:
        missing_rule |= (~audit[f"observed_{col}"].to_numpy())
    b = (audit["mechanism"] == "E_unexplained").to_numpy() & missing_rule
    audit.loc[b, "mechanism"] = "B_invalid_rule_indicator"

    # C: 0.01 mg/L TP publication resolution whose rounding interval straddles a class limit.
    coarse = coarse_tp_months(df)
    in_coarse_month = audit[TIME_COL].dt.to_period("M").map(coarse).fillna(False).astype(bool).to_numpy()
    c_candidate = in_coarse_month & audit["source_总磷"].apply(tp_limit_in_rounding_interval).to_numpy()
    c = (audit["mechanism"] == "E_unexplained").to_numpy() & c_candidate
    audit.loc[c, "mechanism"] = "C_reporting_precision"

    # D: observed TP within 5% of any class limit.
    d_candidate = audit["source_总磷"].apply(tp_near_limit).to_numpy()
    d = (audit["mechanism"] == "E_unexplained").to_numpy() & d_candidate
    audit.loc[d, "mechanism"] = "D_near_limit_TP"

    return audit


def mechanism_summary(audit: pd.DataFrame) -> pd.DataFrame:
    order = [
        "A_pH_excursion", "B_invalid_rule_indicator", "C_reporting_precision",
        "D_near_limit_TP", "E_unexplained",
    ]
    rows = []
    for mech in order:
        g = audit[audit["mechanism"] == mech]
        rows.append({
            "mechanism": mech,
            "records": len(g),
            "percent_audit_set": 100 * len(g) / len(audit),
            "one_class_archived_worse": int(((g["tier"] == "one_class") & (g["direction"] == "archived_worse")).sum()),
            "one_class_archived_better": int(((g["tier"] == "one_class") & (g["direction"] == "archived_better")).sum()),
            "multi_class_archived_worse": int(((g["tier"] == ">=2_classes") & (g["direction"] == "archived_worse")).sum()),
            "multi_class_archived_better": int(((g["tier"] == ">=2_classes") & (g["direction"] == "archived_better")).sum()),
            "years": ",".join(map(str, sorted(g["year"].unique()))) if len(g) else "",
        })
    return pd.DataFrame(rows)


def rule_agreement_by_year(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in sorted(y for y in df["year"].unique() if 2021 <= y <= 2025):
        g = df[df["year"] == year]
        exc = g[g["pH_excursion_observed"]]
        rows.append({
            "year": int(year), "n": len(g),
            "r4_agreement": float((g["r4"] == g["obs"]).mean()),
            "r5_agreement": float((g["r5"] == g["obs"]).mean()),
            "pH_excursions_observed": len(exc),
            "pH_excursions_archived_belowV": int((exc["obs"] == 6).sum()),
            "pH_missing": int((~g["observed_pH"]).sum()),
        })
    return pd.DataFrame(rows)


def _fit_predict(df: pd.DataFrame, train_idx: Iterable[int], test_idx: Iterable[int], features: list[str], seed: int = SEED):
    model = build_forest(seed=seed)
    model.fit(df.loc[list(train_idx), features], df.loc[list(train_idx), "obs"])
    return model.predict(df.loc[list(test_idx), features])


def rule_benchmarked_skill(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = primary_split(df)
    test = df.loc[split.test_idx]
    y = test["obs"].to_numpy()
    r4 = test["r4"].to_numpy()
    r5 = test["r5"].to_numpy()
    r4_err = int(np.sum(r4 != y))
    r5_err = int(np.sum(r5 != y))

    specs = {
        "all_11_indicators": INDICATORS,
        "retained_TP_CODMn_pH": RETAINED,
        "TP_only": ["总磷"],
        "retained_without_TP": ["高锰酸盐指数", "pH"],
        "non_rule_indicators": NON_RULE,
    }

    rows = []
    correction_rows = []
    audit = decompose_audit_set(df)
    mechanism_lookup = audit["mechanism"].to_dict()

    for name, features in specs.items():
        pred = _fit_predict(df, split.train_idx, split.test_idx, features)
        model_correct = pred == y
        r4_correct = r4 == y
        r5_correct = r5 == y
        errors = int(np.sum(~model_correct))
        corrected4, broken4, p4 = exact_mcnemar(model_correct, r4_correct)
        corrected5, broken5, p5 = exact_mcnemar(model_correct, r5_correct)
        rows.append({
            "classifier": name,
            "accuracy": float(np.mean(model_correct)),
            "errors": errors,
            "SSR4": skill_score(errors, r4_err),
            "corrected_vs_R4": corrected4,
            "broken_vs_R4": broken4,
            "mcnemar_p_vs_R4": p4,
            "SSR5": skill_score(errors, r5_err),
            "corrected_vs_R5": corrected5,
            "broken_vs_R5": broken5,
            "mcnemar_p_vs_R5": p5,
        })

        if name in {"retained_TP_CODMn_pH", "all_11_indicators"}:
            corrected_idx = np.asarray(split.test_idx)[model_correct & ~r4_correct]
            counts = pd.Series([mechanism_lookup.get(int(i), "not_in_D1_audit") for i in corrected_idx]).value_counts()
            for mechanism, count in counts.items():
                correction_rows.append({"classifier": name, "mechanism": mechanism, "corrected_records": int(count)})

    # Add rule rows for completeness.
    rows.insert(0, {"classifier": "R4_no_model", "accuracy": 1 - r4_err / len(y), "errors": r4_err,
                    "SSR4": 0.0, "corrected_vs_R4": 0, "broken_vs_R4": 0, "mcnemar_p_vs_R4": np.nan,
                    "SSR5": np.nan, "corrected_vs_R5": np.nan, "broken_vs_R5": np.nan, "mcnemar_p_vs_R5": np.nan})
    rows.insert(1, {"classifier": "R5_no_model", "accuracy": 1 - r5_err / len(y), "errors": r5_err,
                    "SSR4": np.nan, "corrected_vs_R4": np.nan, "broken_vs_R4": np.nan, "mcnemar_p_vs_R4": np.nan,
                    "SSR5": 0.0, "corrected_vs_R5": 0, "broken_vs_R5": 0, "mcnemar_p_vs_R5": np.nan})
    return pd.DataFrame(rows), pd.DataFrame(correction_rows)


def equal_credit(df: pd.DataFrame, subset: pd.Series | None = None) -> dict[str, float]:
    g = df if subset is None else df.loc[subset]
    sums = {name: 0.0 for name in BINDER_NAMES}
    for b in g["binders"]:
        w = 1.0 / len(b)
        for name in b:
            sums[name] += w
    return {name: 100 * value / len(g) for name, value in sums.items()}


def forced_shares(df: pd.DataFrame, order: tuple[str, ...], subset: pd.Series | None = None) -> dict[str, float]:
    g = df if subset is None else df.loc[subset]
    counts = {name: 0 for name in BINDER_NAMES}
    for b in g["binders"]:
        chosen = next(name for name in order if name in b)
        counts[chosen] += 1
    return {name: 100 * c / len(g) for name, c in counts.items()}


def attribution_by_month(df: pd.DataFrame) -> pd.DataFrame:
    orders = list(itertools.permutations(BINDER_NAMES.tolist()))
    rows = []
    for month in range(1, 13):
        mask = df["month"] == month
        eq = equal_credit(df, mask)
        all_forced = [forced_shares(df, order, mask) for order in orders]
        row = {"month": month, "n": int(mask.sum())}
        for name in BINDER_NAMES:
            vals = np.array([x[name] for x in all_forced])
            row[f"equal_{name}"] = eq[name]
            row[f"forced_min_{name}"] = vals.min()
            row[f"forced_max_{name}"] = vals.max()
        rows.append(row)
    return pd.DataFrame(rows)


def attribution_summary(df: pd.DataFrame) -> pd.DataFrame:
    orders = list(itertools.permutations(BINDER_NAMES.tolist()))
    subsets = {"all_records": pd.Series(True, index=df.index), "august": df["month"] == 8}
    rows = []
    for subset_name, mask in subsets.items():
        g = df.loc[mask]
        eq = equal_credit(df, mask)
        all_forced = [forced_shares(df, order, mask) for order in orders]
        prespecified = forced_shares(df, tuple(FORCED_ORDER), mask)
        for name in ["TP", "CODMn", "DO", "NH3-N"]:
            vals = np.array([x[name] for x in all_forced])
            sole = 100 * sum(b == frozenset([name]) for b in g["binders"]) / len(g)
            involved = 100 * sum(name in b for b in g["binders"]) / len(g)
            rows.append({
                "subset": subset_name, "indicator": name, "n": len(g),
                "sole_binder": sole, "involved_in_worst_grade": involved,
                "equal_credit_shapley": eq[name], "forced_prespecified": prespecified[name],
                "forced_min_24_orders": vals.min(), "forced_max_24_orders": vals.max(),
            })
    return pd.DataFrame(rows)


def temporal_validation(df: pd.DataFrame) -> pd.DataFrame:
    rule = rule_agreement_by_year(df).set_index("year")
    rows = []

    # Main manuscript models: 2023 <- 2021-22; 2024 <- 2021-23; 2025 <- 2021-23.
    training_years = {
        2023: [2021, 2022],
        2024: [2021, 2022, 2023],
        2025: [2021, 2022, 2023],
    }
    for test_year, years in training_years.items():
        train = df[df["year"].isin(years)]
        test = df[df["year"] == test_year]
        model = build_forest()
        model.fit(train[RETAINED], train["obs"])
        pred = model.predict(test[RETAINED])
        y = test["obs"].to_numpy()
        model_err = int(np.sum(pred != y))
        r4 = test["r4"].to_numpy(); r5 = test["r5"].to_numpy()
        r4_err = int(np.sum(r4 != y)); r5_err = int(np.sum(r5 != y))
        _, _, p4 = exact_mcnemar(pred == y, r4 == y)
        _, _, p5 = exact_mcnemar(pred == y, r5 == y)
        rows.append({
            "year": test_year, "train_years": f"{min(years)}-{max(years)}", "n": len(test),
            "r4_agreement": rule.loc[test_year, "r4_agreement"],
            "r5_agreement": rule.loc[test_year, "r5_agreement"],
            "model_accuracy": 1 - model_err / len(test),
            "SSR4": skill_score(model_err, r4_err), "SSR5": skill_score(model_err, r5_err),
            "mcnemar_p_vs_R4": p4, "mcnemar_p_vs_R5": p5,
            "pH_excursions_archived_belowV": int(rule.loc[test_year, "pH_excursions_archived_belowV"]),
            "pH_excursions_observed": int(rule.loc[test_year, "pH_excursions_observed"]),
        })

    # Expanding-window 2025 model used in Fig. 6 and shown parenthetically in Table 7.
    train = df[df["year"].isin([2021, 2022, 2023, 2024])]
    test = df[df["year"] == 2025]
    model = build_forest(); model.fit(train[RETAINED], train["obs"])
    pred = model.predict(test[RETAINED]); y = test["obs"].to_numpy()
    model_err = int(np.sum(pred != y))
    r4_err = int(np.sum(test["r4"].to_numpy() != y)); r5_err = int(np.sum(test["r5"].to_numpy() != y))
    _, _, p4 = exact_mcnemar(pred == y, test["r4"].to_numpy() == y)
    _, _, p5 = exact_mcnemar(pred == y, test["r5"].to_numpy() == y)
    rows.append({
        "year": 2025, "train_years": "2021-2024_expanding", "n": len(test),
        "r4_agreement": rule.loc[2025, "r4_agreement"], "r5_agreement": rule.loc[2025, "r5_agreement"],
        "model_accuracy": 1 - model_err / len(test), "SSR4": skill_score(model_err, r4_err),
        "SSR5": skill_score(model_err, r5_err), "mcnemar_p_vs_R4": p4, "mcnemar_p_vs_R5": p5,
        "pH_excursions_archived_belowV": int(rule.loc[2025, "pH_excursions_archived_belowV"]),
        "pH_excursions_observed": int(rule.loc[2025, "pH_excursions_observed"]),
    })
    return pd.DataFrame(rows)


def error_breakdown_2025(df: pd.DataFrame) -> pd.DataFrame:
    train = df[df["year"].isin([2021, 2022, 2023])]
    test = df[df["year"] == 2025].copy()
    model = build_forest(); model.fit(train[RETAINED], train["obs"])
    test["pred"] = model.predict(test[RETAINED])
    err = test[test["pred"] != test["obs"]].copy()
    return pd.DataFrame([{
        "model_errors_2025": len(err),
        "predicted_belowV": int((err["pred"] == 6).sum()),
        "filled_pH_excursion": int(err["pH_excursion_filled"].sum()),
        "observed_pH_excursion_not_archived_belowV": int((err["pH_excursion_observed"] & (err["obs"] != 6)).sum()),
        "pH_missing_but_filled_excursion": int((~err["observed_pH"] & err["pH_excursion_filled"]).sum()),
    }])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    _, df = load_archive(args.csv)
    df = reconstruct(df)

    audit = decompose_audit_set(df)
    audit.to_csv(os.path.join(args.outdir, "audit_set_records.csv"), index=False)
    mechanism_summary(audit).to_csv(os.path.join(args.outdir, "audit_set_mechanisms.csv"), index=False)
    rule_agreement_by_year(df).to_csv(os.path.join(args.outdir, "audit_rule_agreement_by_year.csv"), index=False)

    skill, corrections = rule_benchmarked_skill(df)
    skill.to_csv(os.path.join(args.outdir, "audit_rule_benchmarked_skill.csv"), index=False)
    corrections.to_csv(os.path.join(args.outdir, "audit_model_corrections_by_mechanism.csv"), index=False)

    attribution_summary(df).to_csv(os.path.join(args.outdir, "audit_attribution_summary.csv"), index=False)
    attribution_by_month(df).to_csv(os.path.join(args.outdir, "audit_equal_credit_by_month.csv"), index=False)

    temporal_validation(df).to_csv(os.path.join(args.outdir, "audit_temporal_validation.csv"), index=False)
    error_breakdown_2025(df).to_csv(os.path.join(args.outdir, "audit_2025_error_breakdown.csv"), index=False)

    print(f"audit set                         : {len(audit)} records")
    print(mechanism_summary(audit).to_string(index=False))
    print("\nRule-benchmarked skill")
    print(skill.to_string(index=False))
    print("\nAttribution summary")
    print(attribution_summary(df).to_string(index=False))
    print("\nTemporal validation")
    print(temporal_validation(df).to_string(index=False))
    print(f"\nwrote D1-D4 audit outputs to {args.outdir}/")


if __name__ == "__main__":
    main()
