"""
generate_dataset.py
===================
Creates a SYNTHETIC irrigation dataset (no suitable public dataset has exactly these columns).

How the label is produced (so the data is explainable, not random):
  * every crop has a soil-moisture threshold;
  * hot weather raises the water need, humid air and rain lower it;
  * Gaussian noise imitates sensor error and day-to-day variation.
  irrigation_needed = 1 when the combined "water-stress score" is positive.

The raw file is deliberately a little "dirty" (missing values, duplicates, impossible readings)
so that the data-cleaning step has real work to do.

Run:  python src/generate_dataset.py
"""
import os

import numpy as np
import pandas as pd

import config


def generate(n_samples: int = 5000, seed: int = config.RANDOM_STATE) -> pd.DataFrame:
    rng = np.random.default_rng(seed)               # reproducible random-number generator

    crop = rng.choice(list(config.CROPS), size=n_samples)
    temperature = np.clip(rng.normal(29, 7, n_samples), 5, 50)
    # humidity tends to be lower on hotter days -> add a negative link to temperature
    humidity = np.clip(rng.normal(62, 15, n_samples) - 0.6 * (temperature - 29), 10, 100)
    soil_moisture = np.clip(rng.normal(42, 16, n_samples), 3, 95)
    rainy_day = rng.random(n_samples) < 0.30        # about 30 % of days have rain
    rainfall = np.where(rainy_day, rng.gamma(2.0, 7.0, n_samples), 0.0)
    rainfall = np.clip(rainfall, 0, 150)

    threshold = np.array([config.CROPS[c]["threshold"] for c in crop], dtype=float)

    # water-stress score: > 0 means the crop is short of water
    # The relationships are intentionally NON-linear, as they are in real fields:
    #   * evaporation accelerates as it gets hotter (quadratic, sign-preserving term)
    #   * the drying effect of low humidity is stronger on hot days (temperature x humidity interaction)
    #   * rain helps with diminishing returns: the soil saturates (1 - exp(-rain/15))
    heat = 0.004 * (temperature - 25) * np.abs(temperature - 25)
    score = (0.12 * (threshold - soil_moisture)     # drier soil than the crop likes
             + heat
             - 0.025 * (humidity - 60) * (temperature / 30)
             - 1.6 * (1 - np.exp(-rainfall / 15))
             + rng.normal(0, 0.55, n_samples))      # sensor / field noise
    irrigation = (score > 0).astype(int)

    df = pd.DataFrame({
        "temperature": temperature.round(1),
        "humidity": humidity.round(1),
        "soil_moisture": soil_moisture.round(1),
        "rainfall": rainfall.round(1),
        "crop_type": crop,
        "irrigation_needed": irrigation,
    })

    # ---- make the raw file realistically messy ----
    for col in config.NUMERIC_FEATURES:             # ~2 % missing values per sensor
        idx = rng.choice(n_samples, size=int(0.02 * n_samples), replace=False)
        df.loc[idx, col] = np.nan
    spikes = rng.choice(n_samples, size=20, replace=False)
    df.loc[spikes, "temperature"] = 99.0            # impossible sensor spikes
    df.loc[rng.choice(n_samples, size=15, replace=False), "soil_moisture"] = -5.0
    df = pd.concat([df, df.sample(50, random_state=seed)], ignore_index=True)   # 50 duplicate rows
    return df


if __name__ == "__main__":
    os.makedirs(config.DATA_DIR, exist_ok=True)
    data = generate()
    data.to_csv(config.RAW_CSV, index=False)
    print(f"Raw dataset saved -> {config.RAW_CSV}   shape = {data.shape}")
