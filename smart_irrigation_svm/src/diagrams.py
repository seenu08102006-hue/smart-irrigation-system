"""
diagrams.py
===========
Draws the block diagrams used in the report and slides (system architecture, ML pipeline,
pump-control flowchart, SVM margin concept) with plain Matplotlib - no extra software needed.

Run:  python src/diagrams.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

import config

GREEN, DARK, BLUE, ORANGE, GREY = "#16a34a", "#14532d", "#0ea5e9", "#f97316", "#64748b"


def box(ax, x, y, w, h, text, color=GREEN, fs=9, tc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=color, ec="white", lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs, fontweight="bold", wrap=True)


def arrow(ax, p1, p2, text=None):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=16, color=DARK, lw=1.6))
    if text:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + .12, text, ha="center", fontsize=8, color=DARK)


def canvas(w, h, size):
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    os.makedirs(config.FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(config.FIG_DIR, name), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("  diagram ->", name)


def architecture():
    fig, ax = canvas(12, 5.2, (11, 4.8))
    box(ax, .2, 3.4, 2.2, 1.2, "Field sensors\nTemp · Humidity\nSoil moisture · Rain", ORANGE)
    box(ax, 3.2, 3.4, 2.2, 1.2, "Data cleaning\n& scaling", BLUE)
    box(ax, 6.2, 3.4, 2.2, 1.2, "SVM classifier\n(Joblib model)", GREEN)
    box(ax, 9.2, 3.4, 2.6, 1.2, "Electrical\noptimisation module", DARK)
    arrow(ax, (2.4, 4), (3.2, 4)); arrow(ax, (5.4, 4), (6.2, 4)); arrow(ax, (8.4, 4), (9.2, 4))
    box(ax, 3.2, 1.2, 2.2, 1.1, "Flask web server\n(REST + HTML)", GREEN)
    box(ax, 6.2, 1.2, 2.2, 1.1, "Bootstrap web UI\n(farmer's browser)", BLUE)
    box(ax, 9.2, 1.2, 2.6, 1.1, "Pump relay\nON / OFF", ORANGE)
    arrow(ax, (7.3, 3.4), (4.6, 2.3), "prediction"); arrow(ax, (10.5, 3.4), (4.9, 2.3))
    arrow(ax, (5.4, 1.75), (6.2, 1.75), "result"); arrow(ax, (10.5, 3.4), (10.5, 2.3), "control")
    save(fig, "20_system_architecture.png")


def pipeline():
    fig, ax = canvas(14, 2.6, (12.5, 2.6))
    steps = [("Raw\ndataset", ORANGE), ("Cleaning\n& missing values", BLUE), ("EDA &\nvisualisation", BLUE),
             ("Train/test\nsplit", GREEN), ("Scaling +\nencoding", GREEN), ("Train 4 models\n(GridSearchCV)", DARK),
             ("Evaluate &\ncompare", GREEN), ("Save with\nJoblib", ORANGE)]
    for i, (t, c) in enumerate(steps):
        box(ax, .1 + i * 1.72, .8, 1.5, 1.1, t, c, fs=8)
        if i < len(steps) - 1:
            arrow(ax, (1.6 + i * 1.72, 1.35), (1.82 + i * 1.72, 1.35))
    save(fig, "21_ml_pipeline.png")


def flowchart():
    fig, ax = canvas(10, 9, (6.4, 7.2))
    box(ax, 3.5, 8.0, 3, .7, "START", DARK)
    box(ax, 2.8, 6.7, 4.4, .8, "Read temperature, humidity,\nsoil moisture, rainfall, crop", BLUE)
    box(ax, 2.8, 5.4, 4.4, .8, "Validate & scale inputs", BLUE)
    box(ax, 2.8, 4.1, 4.4, .8, "SVM predicts class", GREEN)
    ax.add_patch(Polygon([[5, 3.7], [7.1, 2.9], [5, 2.1], [2.9, 2.9]], fc=ORANGE, ec="white"))
    ax.text(5, 2.9, "Irrigation\nneeded?", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    box(ax, .1, .6, 3.8, 1.1, "Pump ON\nlitres from deficit,\nheat and rain -> kWh", GREEN, fs=8)
    box(ax, 6.1, .6, 3.8, 1.1, "Pump OFF\n0 kWh used,\ntimer energy saved", DARK, fs=8)
    for a, b in [((5, 8), (5, 7.5)), ((5, 6.7), (5, 6.2)), ((5, 5.4), (5, 4.9)), ((5, 4.1), (5, 3.7))]:
        arrow(ax, a, b)
    arrow(ax, (2.9, 2.9), (1.9, 1.7), "YES"); arrow(ax, (7.1, 2.9), (8.1, 1.7), "NO")
    save(fig, "22_flowchart.png")


def svm_concept():
    rng = np.random.default_rng(3)
    a = rng.normal([2, 2], .55, (40, 2)); b = rng.normal([5, 5], .55, (40, 2))
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.scatter(*a.T, c=GREEN, label="Class 0: no irrigation"); ax.scatter(*b.T, c=BLUE, label="Class +1: irrigation")
    x = np.linspace(0, 7, 10)
    ax.plot(x, 7 - x, "k-", lw=2, label="hyperplane  w·x + b = 0")
    ax.plot(x, 7 - x + 1.1, "k--", lw=1); ax.plot(x, 7 - x - 1.1, "k--", lw=1)
    ax.annotate("margin", (4.3, 3.6), fontsize=10, color=ORANGE, fontweight="bold")
    ax.set_xlim(0, 7); ax.set_ylim(0, 7); ax.set_xlabel("feature 1 (e.g. soil moisture)"); ax.set_ylabel("feature 2 (e.g. temperature)")
    ax.legend(fontsize=7, loc="upper right"); ax.set_title("SVM maximum-margin idea")
    save(fig, "23_svm_concept.png")


if __name__ == "__main__":
    architecture(); pipeline(); flowchart(); svm_concept()
