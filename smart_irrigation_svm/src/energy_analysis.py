"""
energy_analysis.py
==================
Measures the electrical benefit of the smart system on the held-out TEST days.

For every test day we compare
    * conventional system : pump runs TIMER_HOURS every day (fixed energy)
    * smart system        : SVM decides, pump runs only when needed and only as long as needed
and report the average energy / water per day, plus how often each system is cheaper.

Run:  python src/energy_analysis.py      (after train_models.py)
"""
import json
import os

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config
import energy


def main():
    df = pd.read_csv(config.CLEAN_CSV)
    X = df[config.NUMERIC_FEATURES + config.CATEGORICAL_FEATURES]
    y = df[config.TARGET]
    _, X_test, _, _ = train_test_split(X, y, test_size=0.2, stratify=y, random_state=config.RANDOM_STATE)

    model = joblib.load(config.SVM_MODEL_PATH)
    pred = model.predict(X_test)

    rows = []
    for (_, r), p in zip(X_test.iterrows(), pred):
        rows.append(energy.estimate(bool(p), r.temperature, r.soil_moisture, r.rainfall, r.crop_type))
    e = pd.DataFrame(rows)

    base_kwh = config.TIMER_HOURS * config.PUMP_POWER_KW
    base_l = config.TIMER_HOURS * config.PUMP_FLOW_L_PER_H
    summary = {
        "test_days": int(len(e)),
        "timer_kwh_per_day": base_kwh,
        "smart_kwh_per_day": round(float(e.energy_used_kwh.mean()), 3),
        "saving_percent": round(100 * (1 - float(e.energy_used_kwh.mean()) / base_kwh), 1),
        "timer_litres_per_day": base_l,
        "smart_litres_per_day": round(float(e.water_litres.mean()), 1),
        "water_saving_percent": round(100 * (1 - float(e.water_litres.mean()) / base_l), 1),
        "pump_on_days_percent": round(100 * float((e.pump_status == "ON").mean()), 1),
        "days_smart_cheaper_percent": round(100 * float((e.energy_used_kwh < base_kwh).mean()), 1),
        "days_smart_costlier_percent": round(100 * float((e.energy_used_kwh > base_kwh).mean()), 1),
        "total_kwh_saved_over_test_days": round(float((base_kwh - e.energy_used_kwh).sum()), 1),
    }
    # monthly (30-day) projection for one 100 m2 plot
    summary["kwh_saved_per_30_days"] = round(30 * (base_kwh - summary["smart_kwh_per_day"]), 1)

    # ---------- figures ----------
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    ax.bar(["Timer system", "Smart (SVM)"], [base_kwh, summary["smart_kwh_per_day"]], color=["#f97316", "#16a34a"])
    for i, v in enumerate([base_kwh, summary["smart_kwh_per_day"]]):
        ax.text(i, v + .05, f"{v:.2f} kWh", ha="center")
    ax.set_ylabel("average energy per day (kWh)")
    ax.set_title(f"Pump energy: {summary['saving_percent']}% lower")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(config.FIG_DIR, "14_energy_comparison.png"), dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.hist(e.energy_used_kwh, bins=30, color="#16a34a", alpha=.8)
    ax.axvline(base_kwh, color="#f97316", ls="--", lw=2, label=f"timer = {base_kwh:.1f} kWh")
    ax.set_xlabel("smart-system energy per day (kWh)")
    ax.set_ylabel("number of test days")
    ax.set_title("Distribution of daily pump energy")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(config.FIG_DIR, "15_energy_distribution.png"), dpi=130)
    plt.close(fig)

    with open(os.path.join(config.REPORT_DIR, "energy_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
