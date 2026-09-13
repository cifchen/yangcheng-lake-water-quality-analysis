"""
Regenerate the data-derived figures of the manuscript (Figures 3, 4 and 5).

    python src/make_figures.py --csv data/yangcheng_lake_center_station_3187.csv

Figures 1 and 2 of the paper are a study-area schematic and a workflow diagram; they are
drawn rather than computed and are therefore not produced here.

Outputs (600 dpi PNG, written to ./outputs/):
    figure3_monthly_class_composition.png
    figure4_monthly_binding_status.png
    figure5_confusion_matrices.png
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split

from reproduce_analysis import (BEST, LABELS, RETAINED, SEED, load, reconstruct)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CLASS_ORDER = ["II", "III", "IV", "V", "BelowV"]
CLASS_LABEL = {"II": "Class II", "III": "Class III", "IV": "Class IV",
               "V": "Class V", "BelowV": "Below Class V"}
CLASS_COLOR = {"II": "#2c7fb8", "III": "#7fcdbb", "IV": "#fec44f",
               "V": "#fc8d59", "BelowV": "#b2182b"}
DPI = 600


def figure3(df, outdir):
    """Monthly class composition (stacked bars) with mean ordinal class score."""
    share = (pd.crosstab(df["month"], df["cls"], normalize="index")
             .reindex(columns=CLASS_ORDER, fill_value=0) * 100)
    mean_score = df.groupby("month")["obs"].mean()

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bottom = np.zeros(12)
    for cls in CLASS_ORDER:
        values = share[cls].reindex(range(1, 13)).values
        ax.bar(MONTHS, values, bottom=bottom, label=CLASS_LABEL[cls],
               color=CLASS_COLOR[cls], edgecolor="white", linewidth=0.4)
        bottom += values
    ax.set_ylabel("Share of records (%)")
    ax.set_ylim(0, 100)
    ax.set_xlabel("Month")

    twin = ax.twinx()
    twin.plot(MONTHS, mean_score.reindex(range(1, 13)).values,
              color="black", marker="o", markersize=4, linewidth=1.4,
              label="Mean class score")
    twin.set_ylabel("Mean ordinal class score (2 = Class II, 6 = Below Class V)")
    twin.set_ylim(2, 6)

    handles, labels = ax.get_legend_handles_labels()
    h2, l2 = twin.get_legend_handles_labels()
    ax.legend(handles + h2, labels + l2, ncol=3, fontsize=8,
              loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False)
    fig.tight_layout()
    path = os.path.join(outdir, "figure3_monthly_class_composition.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def figure4(df, outdir):
    """Monthly tie-aware binding status, with monthly mean TP and permanganate index."""
    tp_cod = frozenset(["TP", "CODMn"])
    categories = ["Unique TP", "Unique CODMn", "Unique DO", "TP-CODMn tie", "Other tie"]
    colors = ["#2166ac", "#d6604d", "#4daf4a", "#f4a582", "#999999"]

    rows = []
    for month in range(1, 13):
        g = df[df["month"] == month]
        n = len(g)
        rows.append([
            sum(b == frozenset(["TP"]) for b in g["binders"]) / n * 100,
            sum(b == frozenset(["CODMn"]) for b in g["binders"]) / n * 100,
            sum(b == frozenset(["DO"]) for b in g["binders"]) / n * 100,
            sum(b == tp_cod for b in g["binders"]) / n * 100,
            sum((k >= 2) and (b != tp_cod) for b, k in zip(g["binders"], g["n_tied"])) / n * 100,
        ])
    shares = np.array(rows)

    fig, (top, bottom_ax) = plt.subplots(
        2, 1, figsize=(7.2, 6.2), sharex=True, gridspec_kw={"height_ratios": [2, 1]})

    base = np.zeros(12)
    for i, (label, colour) in enumerate(zip(categories, colors)):
        top.bar(MONTHS, shares[:, i], bottom=base, label=label,
                color=colour, edgecolor="white", linewidth=0.4)
        base += shares[:, i]
    top.set_ylabel("Share of records within month (%)")
    top.set_ylim(0, 100)
    top.legend(ncol=5, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, 1.13),
               frameon=False, columnspacing=1.2, handlelength=1.4)

    monthly = df.groupby("month")[["总磷", "高锰酸盐指数"]].mean().reindex(range(1, 13))
    bottom_ax.plot(MONTHS, monthly["总磷"].values, marker="o", markersize=4,
                   color="#2166ac", label="Total phosphorus")
    bottom_ax.set_ylabel("TP (mg L$^{-1}$)", color="#2166ac")
    bottom_ax.tick_params(axis="y", labelcolor="#2166ac")

    twin = bottom_ax.twinx()
    twin.plot(MONTHS, monthly["高锰酸盐指数"].values, marker="s", markersize=4,
              color="#d6604d", label="Permanganate index")
    twin.set_ylabel("COD$_{Mn}$ (mg L$^{-1}$)", color="#d6604d")
    twin.tick_params(axis="y", labelcolor="#d6604d")
    bottom_ax.set_xlabel("Month")

    fig.tight_layout()
    path = os.path.join(outdir, "figure4_monthly_binding_status.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def figure5(df, outdir):
    """Confusion matrices for the held-out test set: counts and row-normalized."""
    X, y = df[RETAINED], df["cls"]
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y)
    model = RandomForestClassifier(random_state=SEED, n_jobs=-1, **BEST).fit(X_dev, y_dev)
    pred = model.predict(X_test)

    counts = confusion_matrix(y_test, pred, labels=LABELS)
    norm = counts / counts.sum(axis=1, keepdims=True)
    ticks = [CLASS_LABEL[c] for c in LABELS]

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    for ax, matrix, title, fmt in (
            (axes[0], counts, "Counts", "{:d}"),
            (axes[1], norm, "Row-normalized", "{:.2f}")):
        image = ax.imshow(matrix, cmap="Blues")
        ax.set_xticks(range(len(LABELS)), ticks, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(LABELS)), ticks, fontsize=8)
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("Archived class")
        ax.set_title(title, fontsize=10)
        # keep annotations legible on both dark and light cells
        threshold = matrix.max() * 0.55
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = matrix[i, j]
                ax.text(j, i, fmt.format(value), ha="center", va="center", fontsize=8,
                        color="white" if value > threshold else "black")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    fig.tight_layout()
    path = os.path.join(outdir, "figure5_confusion_matrices.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = reconstruct(load(args.csv))
    figure3(df, args.outdir)
    figure4(df, args.outdir)
    figure5(df, args.outdir)


if __name__ == "__main__":
    main()
