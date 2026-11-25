"""
eda.py
======
Exploratory Data Analysis (EDA) + data visualisation.
Reads the RAW csv, cleans it, saves the clean csv and draws the figures used in the report.

Run:  python src/eda.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")                      # draw to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from preprocess import clean_data

GREEN, BLUE, ORANGE = "#16a34a", "#0ea5e9", "#f97316"
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titleweight": "bold"})


def save(fig, name):
    os.makedirs(config.FIG_DIR, exist_ok=True)
    path = os.path.join(config.FIG_DIR, name)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print("  figure ->", name)


def main():
    raw = pd.read_csv(config.RAW_CSV)
    print("Raw shape:", raw.shape)
    print(raw.describe(include="all").T.to_string())

    # ---- Fig: missing values before cleaning ----
    miss = raw[config.NUMERIC_FEATURES].isna().sum()
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(miss.index, miss.values, color=ORANGE)
    ax.set_title("Missing values per column (raw data)")
    ax.set_ylabel("count")
    for i, v in enumerate(miss.values):
        ax.text(i, v + 1, str(v), ha="center")
    save(fig, "01_missing_values.png")

    # ---- clean ----
    df, report = clean_data(raw)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    df.to_csv(config.CLEAN_CSV, index=False)

    # ---- Fig: class balance ----
    counts = df[config.TARGET].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.bar(["No (0)", "Yes (1)"], counts.values, color=[GREEN, BLUE])
    ax.set_title("Class distribution of Irrigation Needed")
    ax.set_ylabel("samples")
    for i, v in enumerate(counts.values):
        ax.text(i, v + 20, f"{v} ({100 * v / len(df):.1f}%)", ha="center")
    save(fig, "02_class_balance.png")

    # ---- Fig: histograms per class ----
    fig, axes = plt.subplots(2, 2, figsize=(9, 6))
    for ax, col in zip(axes.ravel(), config.NUMERIC_FEATURES):
        for label, colour, name in [(0, GREEN, "No irrigation"), (1, BLUE, "Irrigation")]:
            ax.hist(df.loc[df[config.TARGET] == label, col], bins=30, alpha=.65, color=colour, label=name)
        ax.set_title(col.replace("_", " ").title())
        ax.legend()
    save(fig, "03_feature_histograms.png")

    # ---- Fig: box plots ----
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.8))
    for ax, col in zip(axes, config.NUMERIC_FEATURES):
        data = [df.loc[df[config.TARGET] == k, col] for k in (0, 1)]
        bp = ax.boxplot(data, patch_artist=True, tick_labels=["No", "Yes"])
        for patch, c in zip(bp["boxes"], (GREEN, BLUE)):
            patch.set_facecolor(c)
        ax.set_title(col.replace("_", " ").title())
    save(fig, "04_boxplots.png")

    # ---- Fig: correlation heatmap ----
    corr = df[config.NUMERIC_FEATURES + [config.TARGET]].corr()
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(corr)), corr.columns)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, shrink=.8)
    ax.set_title("Correlation matrix")
    save(fig, "05_correlation_heatmap.png")

    # ---- Fig: soil moisture vs temperature scatter ----
    sample = df.sample(1200, random_state=config.RANDOM_STATE)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for label, colour, name in [(0, GREEN, "No irrigation"), (1, BLUE, "Irrigation needed")]:
        s = sample[sample[config.TARGET] == label]
        ax.scatter(s["soil_moisture"], s["temperature"], s=14, alpha=.6, c=colour, label=name)
    ax.set_xlabel("Soil moisture (%)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("Soil moisture vs temperature")
    ax.legend()
    save(fig, "06_scatter_soil_temp.png")

    # ---- Fig: irrigation rate by crop ----
    rate = df.groupby("crop_type")[config.TARGET].mean().sort_values() * 100
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.barh(rate.index, rate.values, color=GREEN)
    ax.set_xlabel("Days needing irrigation (%)")
    ax.set_title("Irrigation need by crop")
    for i, v in enumerate(rate.values):
        ax.text(v + .5, i, f"{v:.1f}%", va="center")
    save(fig, "07_crop_irrigation_rate.png")

    # ---- Fig: rainfall effect ----
    df["rain_band"] = pd.cut(df["rainfall"], [-0.1, 0, 10, 30, 300], labels=["0 mm", "0-10", "10-30", ">30"])
    r = df.groupby("rain_band", observed=True)[config.TARGET].mean() * 100
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.bar(r.index.astype(str), r.values, color=BLUE)
    ax.set_ylabel("Days needing irrigation (%)")
    ax.set_title("Effect of rainfall on irrigation need")
    save(fig, "08_rainfall_effect.png")

    stats = df[config.NUMERIC_FEATURES].describe().round(2).to_dict()
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    with open(os.path.join(config.REPORT_DIR, "eda_summary.json"), "w") as f:
        json.dump({"cleaning": report, "describe": stats,
                   "class_counts": {int(k): int(v) for k, v in counts.items()},
                   "correlation_with_target": corr[config.TARGET].round(3).to_dict()}, f, indent=2)
    print("EDA finished. Clean data ->", config.CLEAN_CSV)


if __name__ == "__main__":
    main()
