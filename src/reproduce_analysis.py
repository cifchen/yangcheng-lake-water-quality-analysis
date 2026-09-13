"""
Reproduce the analysis reported in:

    Meng, X.; Tang, K.; Zheng, Y. Seasonal Shifts in Binding and Co-Binding Indicators of
    Regulatory Water-Quality Classification: Separating Rule Recovery from Ecological
    Inference at a National Monitoring Station in Yangcheng Lake, China.

Usage
-----
    pip install -r requirements.txt
    python src/reproduce_analysis.py --csv data/yangcheng_lake_center_station.csv

The script prints every quantity cited in the manuscript and writes the analysis set,
the tie-aware monthly table (Table 5) and the ablation table (Table 8) to ./outputs/.

Deterministic results (quality control, Tables 2-5, the four-indicator reconstruction and
the tie structure) reproduce exactly. Random-forest figures may differ by a few tenths of a
percentage point across scikit-learn versions; the version used for the reported numbers is
recorded in requirements.txt.
"""

import argparse
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

INDICATORS = ["水温", "pH", "溶解氧", "电导率", "浊度", "高锰酸盐指数",
              "氨氮", "总磷", "总氮", "叶绿素α", "藻密度"]
RETAINED = ["总磷", "高锰酸盐指数", "pH"]
NON_RULE = ["水温", "电导率", "浊度", "叶绿素α", "藻密度", "总氮"]
BEST = dict(n_estimators=300, max_depth=None, min_samples_split=5, min_samples_leaf=1)
SEED = 42

# GB 3838-2002 limits for Classes I-V. Dissolved oxygen is "higher is better";
# total phosphorus uses the lake and reservoir column.
LIMITS_UP = {"高锰酸盐指数": [2, 4, 6, 10, 15],
             "氨氮": [0.15, 0.5, 1.0, 1.5, 2.0],
             "总磷": [0.01, 0.025, 0.05, 0.1, 0.2],
             "总氮": [0.2, 0.5, 1.0, 1.5, 2.0]}
LIMITS_DO = [7.5, 6, 5, 3, 2]
CLASS_MAP = {"Ⅰ": "II", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V", "劣Ⅴ": "BelowV"}
ORDINAL = {"II": 2, "III": 3, "IV": 4, "V": 5, "BelowV": 6}
LABELS = ["II", "III", "IV", "V", "BelowV"]


def grade_down(value):
    """Grade an indicator for which higher values are better (dissolved oxygen)."""
    for cls, limit in zip([1, 2, 3, 4, 5], LIMITS_DO):
        if value >= limit:
            return cls
    return 6


def grade_up(value, limits):
    """Grade an indicator for which lower values are better."""
    for cls, limit in zip([1, 2, 3, 4, 5], limits):
        if value <= limit:
            return cls
    return 6


def wilson(successes, n, z=1.96):
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return 100 * (centre - half), 100 * (centre + half)


def load(csv_path):
    """Section 2.2-2.3: load, drop unlabelled records, interpolate, median-fill edges."""
    raw = pd.read_csv(csv_path, skiprows=[1])
    raw["监测时间"] = pd.to_datetime(raw["监测时间"])
    raw = raw.sort_values("监测时间").reset_index(drop=True)
    print(f"retrieved records                 : {len(raw)}")

    print("\n--- Table 2: invalid or missing entries ---")
    for col in INDICATORS + ["水质"]:
        series = raw[col].astype("object")
        invalid = series.isna().sum() + (series.astype(str).str.strip() == "UNKNOWN").sum()
        print(f"  {col:8s} {invalid:5d}  {invalid / len(raw) * 100:5.2f}%  valid {len(raw) - invalid}")

    df = raw[raw["水质"] != "UNKNOWN"].copy().reset_index(drop=True)
    for col in INDICATORS:
        df[col] = df[col].interpolate(method="linear", limit_direction="both")
        df[col] = df[col].fillna(df[col].median())
    df["month"] = df["监测时间"].dt.month
    df["year"] = df["监测时间"].dt.year
    df["cls"] = df["水质"].map(CLASS_MAP)
    df["obs"] = df["cls"].map(ORDINAL)
    print(f"\nanalysis set                      : {len(df)}")
    return df


def reconstruct(df):
    """Section 2.4: four-indicator worst-of reconstruction and tie-aware attribution."""
    grades = pd.DataFrame({
        "NH3-N": df["氨氮"].apply(lambda v: grade_up(v, LIMITS_UP["氨氮"])),
        "DO": df["溶解氧"].apply(grade_down),
        "CODMn": df["高锰酸盐指数"].apply(lambda v: grade_up(v, LIMITS_UP["高锰酸盐指数"])),
        "TP": df["总磷"].apply(lambda v: grade_up(v, LIMITS_UP["总磷"])),
    })
    worst = grades.max(axis=1)
    names = np.array(grades.columns)
    binder_sets = [frozenset(names[row == w]) for row, w in zip(grades.values, worst)]

    df = df.copy()
    df["recon"] = worst.clip(lower=2)          # Classes I and II merged
    df["n_tied"] = (grades.values == worst.values[:, None]).sum(axis=1)
    df["binders"] = binder_sets
    df["binder_forced"] = [next(n for n in names if n in b) for b in binder_sets]
    df["g_TN"] = df["总氮"].apply(lambda v: grade_up(v, LIMITS_UP["总氮"]))
    df["recon_with_TN"] = np.maximum(df["recon"], df["g_TN"]).clip(lower=2)
    return df


def report_reconstruction(df):
    print("\n--- Section 3.4: threshold reconstruction ---")
    exact = (df["recon"] == df["obs"]).mean() * 100
    within = ((df["recon"] - df["obs"]).abs() <= 1).mean() * 100
    print(f"  exact agreement                 : {exact:.2f}%")
    print(f"  within one class                : {within:.2f}%")

    bad_ph = (df["pH"] < 6) | (df["pH"] > 9)
    with_ph = np.where(bad_ph, np.maximum(df["recon"], 6), df["recon"])
    print(f"  with pH 6-9 constraint          : {(with_ph == df['obs']).mean() * 100:.2f}%")
    print(f"  forcing total nitrogen in       : {(df['recon_with_TN'] == df['obs']).mean() * 100:.2f}%")

    core = df["监测时间"]
    core = (core >= "2021-01-01") & (core < "2026-01-01")
    sub = df[core]
    print(f"  2021-2025 core (n = {core.sum()})    : "
          f"{(sub['recon'] == sub['obs']).mean() * 100:.2f}% exact, "
          f"{(sub['recon_with_TN'] == sub['obs']).mean() * 100:.2f}% with total nitrogen forced in")


def report_binding(df, outdir):
    print("\n--- Section 3.5: tie-aware binding attribution ---")
    n = len(df)
    tied = df["n_tied"] >= 2
    print(f"  ties                            : {tied.sum()} ({tied.mean() * 100:.1f}%)  "
          f"[2-way {(df['n_tied'] == 2).sum()}, 3-way {(df['n_tied'] == 3).sum()}, "
          f"4-way {(df['n_tied'] == 4).sum()}]")
    tp_cod = frozenset(["TP", "CODMn"])
    n_tpcod = sum(b == tp_cod for b in df["binders"])
    print(f"  TP-CODMn tie                    : {n_tpcod} ({n_tpcod / n * 100:.1f}%)")
    for name in ["TP", "CODMn", "DO", "NH3-N"]:
        c = sum(b == frozenset([name]) for b in df["binders"])
        print(f"  unique {name:6s}                   : {c} ({c / n * 100:.1f}%)")

    rows = []
    for month in range(1, 13):
        g = df[df["month"] == month]
        m = len(g)
        rows.append({
            "month": month,
            "unique_TP": round(sum(b == frozenset(["TP"]) for b in g["binders"]) / m * 100, 1),
            "unique_CODMn": round(sum(b == frozenset(["CODMn"]) for b in g["binders"]) / m * 100, 1),
            "unique_DO": round(sum(b == frozenset(["DO"]) for b in g["binders"]) / m * 100, 1),
            "TP_CODMn_tie": round(sum(b == tp_cod for b in g["binders"]) / m * 100, 1),
            "other_tie": round(sum((k >= 2) and (b != tp_cod)
                                   for b, k in zip(g["binders"], g["n_tied"])) / m * 100, 1),
        })
    table5 = pd.DataFrame(rows)
    print("\n--- Table 5 ---")
    print(table5.to_string(index=False))
    table5.to_csv(os.path.join(outdir, "table5_tie_aware_binding_by_month.csv"), index=False)

    severe = df[df["cls"] == "BelowV"]
    print(f"\n  Below Class V (n = {len(severe)}): "
          f"{(severe['n_tied'] >= 2).mean() * 100:.1f}% tied, "
          f"{sum(b == tp_cod for b in severe['binders']) / len(severe) * 100:.1f}% TP-CODMn, "
          f"{sum(b == frozenset(['TP']) for b in severe['binders']) / len(severe) * 100:.1f}% unique TP")


def report_forest(df, outdir):
    print("\n--- Sections 3.6-3.7: random forest ---")
    X, y = df[INDICATORS], df["cls"]
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y)
    print(f"  development / held out          : {len(X_dev)} / {len(X_test)}")

    screen = RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1).fit(X_dev, y_dev)
    gini = pd.Series(screen.feature_importances_, index=INDICATORS)
    folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
    perm = np.zeros(len(INDICATORS))
    for tr, va in folds.split(X_dev, y_dev):
        model = RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1)
        model.fit(X_dev.iloc[tr], y_dev.iloc[tr])
        perm += permutation_importance(model, X_dev.iloc[va], y_dev.iloc[va], n_repeats=10,
                                       random_state=SEED, scoring="accuracy", n_jobs=-1).importances_mean
    perm = pd.Series(perm / 5, index=INDICATORS)
    table6 = pd.DataFrame({"gini": gini.round(3), "permutation": perm.round(3)})
    table6["retained"] = (table6["gini"] >= 0.05) | (table6["permutation"] >= 0.01)
    print("\n--- Table 6 ---")
    print(table6.sort_values("gini", ascending=False).to_string())
    table6.to_csv(os.path.join(outdir, "table6_feature_importance.csv"))

    cv = cross_val_score(RandomForestClassifier(random_state=SEED, n_jobs=-1, **BEST),
                         X_dev[RETAINED], y_dev, cv=folds, scoring="accuracy")
    print(f"\n  five-fold CV accuracy           : {cv.mean() * 100:.3f}% "
          f"(sample SD {cv.std(ddof=1) * 100:.3f} pp)")

    model = RandomForestClassifier(random_state=SEED, n_jobs=-1, **BEST).fit(X_dev[RETAINED], y_dev)
    pred = model.predict(X_test[RETAINED])
    print(f"  held-out accuracy               : {accuracy_score(y_test, pred) * 100:.2f}%")
    print(f"  weighted / macro F1             : {f1_score(y_test, pred, average='weighted') * 100:.2f}% / "
          f"{f1_score(y_test, pred, average='macro') * 100:.2f}%")

    print("\n--- Table 7: per-class performance with Wilson 95% CIs ---")
    p, r, f, s = precision_recall_fscore_support(y_test, pred, labels=LABELS)
    for i, label in enumerate(LABELS):
        lo, hi = wilson(round(r[i] * s[i]), s[i])
        print(f"  {label:7s} n={s[i]:4d}  P={p[i] * 100:5.1f}  R={r[i] * 100:5.1f}  "
              f"F1={f[i] * 100:5.1f}  CI=[{lo:.1f}, {hi:.1f}]")

    print("\n--- Table 8: ablation on the held-out set ---")
    sets = {"all 11 indicators": INDICATORS, "retained (TP, CODMn, pH)": RETAINED,
            "total phosphorus only": ["总磷"], "retained without TP": ["高锰酸盐指数", "pH"],
            "non-rule indicators": NON_RULE}
    rows = [{"feature_set": "deterministic reconstruction",
             "accuracy": round((df.loc[X_test.index, "recon"] == df.loc[X_test.index, "obs"]).mean(), 4)}]
    for name, cols in sets.items():
        m = RandomForestClassifier(random_state=SEED, n_jobs=-1, **BEST).fit(X_dev[cols], y_dev)
        rows.append({"feature_set": name, "accuracy": round(accuracy_score(y_test, m.predict(X_test[cols])), 4)})
    table8 = pd.DataFrame(rows)
    print(table8.to_string(index=False))
    table8.to_csv(os.path.join(outdir, "table8_ablation.csv"), index=False)

    print("\n--- forward temporal validation ---")
    train = df[df["year"].isin([2021, 2022, 2023])]
    fwd = RandomForestClassifier(random_state=SEED, n_jobs=-1, **BEST).fit(train[RETAINED], train["cls"])
    for year in (2024, 2025):
        test = df[df["year"] == year]
        print(f"  {year} (n = {len(test)})              : "
              f"{accuracy_score(test['cls'], fwd.predict(test[RETAINED])) * 100:.2f}%")

    print("\n--- Section 2.7: 50 repeated stratified splits ---")
    metrics = {"accuracy": [], "weighted F1": [], "macro F1": [],
               "recall II": [], "recall V": [], "recall BelowV": []}
    for seed in range(50):
        a, b, ya, yb = train_test_split(df[RETAINED], y, test_size=0.2, random_state=seed, stratify=y)
        m = RandomForestClassifier(random_state=seed, n_jobs=-1, **BEST).fit(a, ya)
        q = m.predict(b)
        metrics["accuracy"].append(accuracy_score(yb, q))
        metrics["weighted F1"].append(f1_score(yb, q, average="weighted"))
        metrics["macro F1"].append(f1_score(yb, q, average="macro"))
        _, rec, _, _ = precision_recall_fscore_support(yb, q, labels=LABELS, zero_division=0)
        metrics["recall II"].append(rec[0])
        metrics["recall V"].append(rec[3])
        metrics["recall BelowV"].append(rec[4])
    for name, values in metrics.items():
        v = np.array(values)
        print(f"  {name:14s} mean {v.mean():.4f}  "
              f"[{np.percentile(v, 2.5):.4f}, {np.percentile(v, 97.5):.4f}]")


def report_sensitivity(df):
    """Section 2.3: exclude extreme values and confirm the conclusions hold."""
    print("\n--- sensitivity to extreme values ---")
    extreme = ((df["总磷"] > 0.4) | (df["总氮"] > 5) |
               (df["高锰酸盐指数"] > 15) | (df["浊度"] > 300))
    print(f"  distinct extreme records        : {extreme.sum()}  (remaining n = {(~extreme).sum()})")
    sub = df[~extreme]
    print(f"  exact agreement                 : {(sub['recon'] == sub['obs']).mean() * 100:.2f}%")
    print(f"  within one class                : {((sub['recon'] - sub['obs']).abs() <= 1).mean() * 100:.2f}%")
    a, b, ya, yb = train_test_split(sub[RETAINED], sub["cls"], test_size=0.2,
                                    random_state=SEED, stratify=sub["cls"])
    m = RandomForestClassifier(random_state=SEED, n_jobs=-1, **BEST).fit(a, ya)
    q = m.predict(b)
    print(f"  held-out accuracy / weighted F1 : {accuracy_score(yb, q) * 100:.2f}% / "
          f"{f1_score(yb, q, average='weighted') * 100:.2f}%")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = reconstruct(load(args.csv))
    report_reconstruction(df)
    report_binding(df, args.outdir)
    report_forest(df, args.outdir)
    report_sensitivity(df)

    keep = ["监测时间", "year", "month"] + INDICATORS + ["cls", "obs", "recon", "n_tied", "binder_forced"]
    out = df[keep].copy()
    out["binders"] = ["|".join(sorted(b)) for b in df["binders"]]
    out.to_csv(os.path.join(args.outdir, "analysis_set.csv"), index=False)
    print(f"\nwrote {args.outdir}/analysis_set.csv and the table CSVs")


if __name__ == "__main__":
    main()
