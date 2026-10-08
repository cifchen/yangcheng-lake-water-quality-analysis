"""Regenerate data-derived figures for the final manuscript.

Figures 1 (audit protocol) and 2 (study-area schematic) are author-drawn and are not generated
here. This script produces:
- Fig. 3 monthly archived class composition;
- Fig. 4 monthly tie-aware binding and TP/CODMn means;
- Fig. 5 monthly equal-credit (Shapley) attribution with forced-order ranges;
- Fig. 6 rule-benchmarked temporal validation and pH-labeling change;
- Online Resource Fig. S1 held-out confusion matrices.

Usage
-----
    python src/make_figures.py --csv data/yangcheng_lake_center_station_3187.csv
"""

from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from reproduce_analysis import LABELS, LABEL_TEXT, RETAINED, SEED, build_forest, load_archive, primary_split, reconstruct
from audit_diagnostics import attribution_by_month, rule_agreement_by_year, temporal_validation

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CLASS_ORDER = [2, 3, 4, 5, 6]
DPI = 600


def save(fig, path: str) -> None:
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def figure3(df: pd.DataFrame, outdir: str) -> None:
    share = (pd.crosstab(df["month"], df["obs"], normalize="index")
             .reindex(index=range(1, 13), columns=CLASS_ORDER, fill_value=0) * 100)
    mean_score = df.groupby("month")["obs"].mean().reindex(range(1, 13))

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bottom = np.zeros(12)
    for code in CLASS_ORDER:
        vals = share[code].to_numpy()
        ax.bar(MONTHS, vals, bottom=bottom, label=LABEL_TEXT[code], edgecolor="white", linewidth=0.4)
        bottom += vals
    ax.set_ylabel("Monthly class composition (%)")
    ax.set_ylim(0, 100)
    ax.set_xlabel("Month")

    twin = ax.twinx()
    twin.plot(MONTHS, mean_score.to_numpy(), marker="o", linewidth=1.5, label="Mean ordinal class score")
    twin.set_ylabel("Mean class score (2 = Class II; 6 = Below Class V)")
    twin.set_ylim(2.5, 5.4)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = twin.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, ncol=3, fontsize=8, loc="upper center",
              bbox_to_anchor=(0.5, -0.18), frameon=False)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "figure3_monthly_class_composition.png"))


def figure4(df: pd.DataFrame, outdir: str) -> None:
    tp_cod = frozenset(["TP", "CODMn"])
    cats = ["Total phosphorus", "Permanganate index", "Dissolved oxygen", "TP-CODMn tie", "Other tie"]
    rows = []
    for m in range(1, 13):
        g = df[df["month"] == m]; n = len(g)
        rows.append([
            100 * sum(b == frozenset(["TP"]) for b in g["binders"]) / n,
            100 * sum(b == frozenset(["CODMn"]) for b in g["binders"]) / n,
            100 * sum(b == frozenset(["DO"]) for b in g["binders"]) / n,
            100 * sum(b == tp_cod for b in g["binders"]) / n,
            100 * sum((len(b) >= 2) and (b != tp_cod) for b in g["binders"]) / n,
        ])
    shares = np.asarray(rows)

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.2, 6.2), sharex=True,
                                     gridspec_kw={"height_ratios": [1.15, 1]})
    base = np.zeros(12)
    for i, label in enumerate(cats):
        top.bar(MONTHS, shares[:, i], bottom=base, label=label, edgecolor="white", linewidth=0.4)
        base += shares[:, i]
    top.set_ylabel("Binding / co-binding share (%)")
    top.set_ylim(0, 100)
    top.legend(ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.20), frameon=False)

    monthly = df.groupby("month")[["总磷", "高锰酸盐指数"]].mean().reindex(range(1, 13))
    bottom.plot(MONTHS, monthly["总磷"], marker="o", label="Total phosphorus")
    bottom.set_ylabel("Total phosphorus (mg L$^{-1}$)")
    bottom.set_xlabel("Month")
    twin = bottom.twinx()
    twin.plot(MONTHS, monthly["高锰酸盐指数"], marker="s", linestyle="--", label="Permanganate index")
    twin.set_ylabel("Permanganate index (mg L$^{-1}$)")
    h1, l1 = bottom.get_legend_handles_labels(); h2, l2 = twin.get_legend_handles_labels()
    bottom.legend(h1 + h2, l1 + l2, ncol=2, fontsize=8, loc="upper center",
                  bbox_to_anchor=(0.5, -0.22), frameon=False)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "figure4_monthly_binding_status.png"))


def figure5(df: pd.DataFrame, outdir: str) -> None:
    a = attribution_by_month(df).set_index("month").reindex(range(1, 13))
    x = np.arange(12)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))

    ax.fill_between(x, a["forced_min_TP"], a["forced_max_TP"], alpha=0.18, label="TP: range over 24 priority orders")
    ax.plot(x, a["equal_TP"], marker="o", linewidth=1.7, label="Total phosphorus: equal credit")
    ax.fill_between(x, a["forced_min_CODMn"], a["forced_max_CODMn"], alpha=0.18,
                    label="CODMn: range over 24 priority orders")
    ax.plot(x, a["equal_CODMn"], marker="s", linestyle="--", linewidth=1.7,
            label="Permanganate index: equal credit")

    ax.set_xticks(x, MONTHS)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of records attributed (%)")
    ax.set_xlabel("Month")
    ax.legend(ncol=2, fontsize=8, frameon=False)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "figure5_equal_credit_shapley.png"))


def figure6(df: pd.DataFrame, outdir: str) -> None:
    rule = rule_agreement_by_year(df).set_index("year").reindex(range(2021, 2026))
    temp = temporal_validation(df)
    # Expanding-window series for Fig. 6: 2023 train 2021-22, 2024 train 2021-23,
    # 2025 use the 2021-24 expanding-window row.
    model_by_year = {
        2023: float(temp[(temp["year"] == 2023)].iloc[0]["model_accuracy"]),
        2024: float(temp[(temp["year"] == 2024)].iloc[0]["model_accuracy"]),
        2025: float(temp[(temp["year"] == 2025) & (temp["train_years"] == "2021-2024_expanding")].iloc[0]["model_accuracy"]),
    }

    years = np.arange(2021, 2026)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    ax = axes[0]
    ax.plot(years, 100 * rule["r4_agreement"], marker="o", label="Four-indicator rule (R4)")
    ax.plot(years, 100 * rule["r5_agreement"], marker="o", linestyle="--", label="R4 + pH constraint (R5)")
    mx = [np.nan, np.nan, 100 * model_by_year[2023], 100 * model_by_year[2024], 100 * model_by_year[2025]]
    ax.plot(years, mx, marker="o", linestyle=":", label="Random forest, prior years")
    ax.set_ylabel("Agreement / accuracy (%)")
    ax.set_xticks(years)
    ax.set_ylim(65, 100)
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("a")

    ax = axes[1]
    exc = rule["pH_excursions_observed"].to_numpy()
    below = rule["pH_excursions_archived_belowV"].to_numpy()
    pct = np.divide(100 * below, exc, out=np.zeros_like(below, dtype=float), where=exc != 0)
    bars = ax.bar(years, pct)
    for bar, b, e in zip(bars, below, exc):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5, f"{int(b)}/{int(e)}",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Observed pH excursions archived as Below Class V (%)")
    ax.set_xticks(years)
    ax.set_title("b")

    fig.tight_layout()
    save(fig, os.path.join(outdir, "figure6_rule_benchmarked_temporal_validation.png"))


def figure_s1(df: pd.DataFrame, outdir: str) -> None:
    split = primary_split(df)
    model = build_forest(SEED)
    model.fit(df.loc[split.train_idx, RETAINED], df.loc[split.train_idx, "obs"])
    pred = model.predict(df.loc[split.test_idx, RETAINED])
    y = df.loc[split.test_idx, "obs"].to_numpy()
    counts = confusion_matrix(y, pred, labels=LABELS)
    norm = counts / counts.sum(axis=1, keepdims=True)
    ticks = [LABEL_TEXT[x] for x in LABELS]

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4))
    for ax, matrix, is_norm in [(axes[0], counts, False), (axes[1], norm, True)]:
        im = ax.imshow(matrix)
        ax.set_xticks(range(5), ticks, rotation=45, ha="right")
        ax.set_yticks(range(5), ticks)
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("Observed class")
        for i in range(5):
            for j in range(5):
                txt = f"{matrix[i,j]:.1%}" if is_norm else str(int(matrix[i,j]))
                ax.text(j, i, txt, ha="center", va="center", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "figureS1_confusion_matrices.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    _, df = load_archive(args.csv)
    df = reconstruct(df)
    figure3(df, args.outdir)
    figure4(df, args.outdir)
    figure5(df, args.outdir)
    figure6(df, args.outdir)
    figure_s1(df, args.outdir)


if __name__ == "__main__":
    main()
