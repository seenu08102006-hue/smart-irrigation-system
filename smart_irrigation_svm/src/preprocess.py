"""
preprocess.py
=============
Data cleaning + the feature-scaling transformer used by every model.

Cleaning steps (in order):
  1. remove duplicate rows
  2. convert numeric columns to numbers (bad text becomes NaN)
  3. mark physically impossible readings as missing
  4. fill missing values with the MEDIAN of the same crop (robust to outliers)
  5. drop rows whose label or crop is missing
Scaling (StandardScaler) is NOT done here; it lives inside the model Pipeline so that the
mean/std are learned from training data only (this prevents "data leakage").
"""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config


def clean_data(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    report = {"rows_before": len(df)}
    df = df.copy()

    # 1. duplicates
    df = df.drop_duplicates()
    report["duplicates_removed"] = report["rows_before"] - len(df)

    # 2. make sure numeric columns are numeric
    for col in config.NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. impossible readings -> NaN
    for col, (low, high) in config.VALID_RANGES.items():
        df.loc[(df[col] < low) | (df[col] > high), col] = float("nan")
    report["missing_before_fill"] = int(df[config.NUMERIC_FEATURES].isna().sum().sum())

    # 5. rows without label / crop cannot be repaired
    df = df.dropna(subset=[config.TARGET, "crop_type"])

    # 4. fill remaining gaps with the crop-wise median
    for col in config.NUMERIC_FEATURES:
        df[col] = df[col].fillna(df.groupby("crop_type")[col].transform("median"))

    df[config.TARGET] = df[config.TARGET].astype(int)
    df = df.reset_index(drop=True)
    report["rows_after"] = len(df)
    report["missing_after_fill"] = int(df.isna().sum().sum())
    if verbose:
        print("[clean]", report)
    return df, report


def make_preprocessor() -> ColumnTransformer:
    """Scale the 4 sensor columns and one-hot encode the crop name."""
    return ColumnTransformer([
        ("scale", StandardScaler(), config.NUMERIC_FEATURES),
        ("crop", OneHotEncoder(categories=[list(config.CROPS)], handle_unknown="ignore"),
         config.CATEGORICAL_FEATURES),
    ])
