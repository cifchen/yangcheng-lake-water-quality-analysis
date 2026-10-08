"""Re-run the 180-combination random-forest grid search reported in the manuscript.

Usage
-----
    python src/tune_random_forest.py --csv data/yangcheng_lake_center_station_3187.csv
"""

from __future__ import annotations

import argparse
import os

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold

from reproduce_analysis import RETAINED, SEED, load_archive, primary_split, reconstruct


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="data/yangcheng_lake_center_station_3187.csv")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    _, df = load_archive(args.csv)
    df = reconstruct(df)
    split = primary_split(df)

    X = df.loc[split.train_idx, RETAINED]
    y = df.loc[split.train_idx, "obs"]

    grid = {
        "n_estimators": [50, 100, 200, 300],
        "max_depth": [5, 10, 15, 20, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    }
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    search = GridSearchCV(
        RandomForestClassifier(random_state=SEED, n_jobs=-1),
        param_grid=grid, scoring="accuracy", cv=cv, n_jobs=-1,
        return_train_score=True, refit=True,
    )
    search.fit(X, y)

    results = pd.DataFrame(search.cv_results_).sort_values("rank_test_score")
    results.to_csv(os.path.join(args.outdir, "grid_search_results.csv"), index=False)

    print("Grid combinations :", len(results))
    print("CV fits           :", len(results) * 5)
    print("Best parameters   :", search.best_params_)
    print(f"Best mean accuracy: {search.best_score_ * 100:.3f}%")
    print("wrote", os.path.join(args.outdir, "grid_search_results.csv"))


if __name__ == "__main__":
    main()
