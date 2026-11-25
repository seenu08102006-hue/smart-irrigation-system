"""
dataset_service.py - everything that happens to an uploaded dataset ("Start Analysis").

    read_table()      read .csv / .xlsx
    file_info()       rows, columns, missing cells, duplicates, size, preview
    detect_mapping()  guess which column is temperature, humidity, soil moisture, rainfall, crop, date, target
    run_analysis()    cleaning -> EDA -> chart data -> SVM training -> findings
    predict_with_model()  manual prediction with the SVM trained on the upload

Everything is computed from the uploaded file only: no sample data, no default model, no simulated or invented values.

The analysis reports progress through a callback so the web page can show a live progress bar.
"""
import io
import math
import os
import re
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

FEATURE_KEYS = ["temperature", "humidity", "soil_moisture", "rainfall"]
REQUIRED = ["date", "temperature", "humidity", "soil_moisture", "rainfall"]
REQUIRED_NAMES = {"date": "Date", "temperature": "Temperature", "humidity": "Humidity", "soil_moisture": "Soil Moisture", "rainfall": "Rainfall"}
LABELS = {"temperature": "Temperature", "humidity": "Humidity", "soil_moisture": "Soil Moisture", "rainfall": "Rainfall"}
UNITS = {"temperature": "°C", "humidity": "%", "soil_moisture": "%", "rainfall": "mm"}

SYNONYMS = {
    "date": ["date", "datetime", "timestamp", "time", "day", "recorded"],
    "temperature": ["temperature", "temp", "airtemp", "tavg", "tmean", "t2m"],
    "humidity": ["humidity", "relativehumidity", "hum", "rh"],
    "soil_moisture": ["soilmoisture", "soilmoist", "moisture", "soilwater", "soil"],
    "rainfall": ["rainfall", "rain", "precipitation", "precip", "prcp"],
    "crop": ["croptype", "crop", "plant", "cultivar"],
    "target": ["irrigationneeded", "irrigationrequired", "irrigation", "irrigate", "pumpstatus", "pump",
               "needirrigation", "label", "target", "class", "output"],
}
# physical limits used to flag impossible sensor readings (wide enough for cold or hot climates)
HARD_LIMITS = {"temperature": (-40, 65), "humidity": (0, 100), "soil_moisture": (0, 100), "rainfall": (0, 600)}
YES_WORDS = {"1", "yes", "y", "true", "t", "on", "needed", "required", "irrigate", "irrigation", "need"}


class DatasetError(ValueError):
    """A problem with the uploaded data that the user can understand and fix."""


def jsonable(o):
    """Recursively convert numpy / pandas / NaN values into plain JSON-safe Python."""
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (math.isnan(o) or math.isinf(o)) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    if o is pd.NaT:
        return None
    return o


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


# ---------------------------------------------------------------------------- reading
def read_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".xlsx":
            df = pd.read_excel(path, engine="openpyxl")
        else:
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    df = pd.read_csv(path, encoding=enc, sep=None, engine="python")   # sep=None sniffs , ; tab
                    break
                except UnicodeDecodeError:
                    continue
    except pd.errors.EmptyDataError:
        raise DatasetError("The file is empty.")
    except Exception as exc:
        raise DatasetError(f"The file is corrupted or is not a valid {ext[1:].upper()} table ({str(exc)[:120]}).")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise DatasetError("The file is empty: it contains no data rows.")
    if df.shape[0] < 30:
        raise DatasetError(f"The dataset has only {df.shape[0]} rows. At least 30 rows are needed for a meaningful analysis.")
    return df


def file_info(df: pd.DataFrame, size_bytes: int, filename: str) -> dict:
    cells = df.shape[0] * df.shape[1]
    missing = int(df.isna().sum().sum())
    return {
        "filename": filename, "rows": int(df.shape[0]), "columns": int(df.shape[1]),
        "missing_cells": missing, "missing_percent": round(100 * missing / max(cells, 1), 2),
        "duplicates": int(df.duplicated().sum()), "size_bytes": int(size_bytes), "size_human": human_size(size_bytes),
        "column_info": [{"name": c, "dtype": str(df[c].dtype), "missing": int(df[c].isna().sum()),
                         "unique": int(df[c].nunique())} for c in df.columns],
        "preview": jsonable(df.head(10).astype(object).where(df.head(10).notna(), None).to_dict("records")),
    }


# ---------------------------------------------------------------------------- column detection
def _norm(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def detect_mapping(df: pd.DataFrame) -> dict:
    """Guess the role of each column from its name (exact match first, then 'contains')."""
    mapping, used = {}, set()
    cols = {c: _norm(c) for c in df.columns}
    for role in ["target", "date", "temperature", "humidity", "soil_moisture", "rainfall", "crop"]:
        found = None
        for syn in SYNONYMS[role]:                              # 1. exact
            for c, n in cols.items():
                if c not in used and n == syn:
                    found = c; break
            if found: break
        if not found:
            for syn in SYNONYMS[role]:                          # 2. contains (skip very short synonyms)
                if len(syn) < 4:
                    continue
                for c, n in cols.items():
                    if c not in used and syn in n:
                        found = c; break
                if found: break
        if found:
            used.add(found)
        mapping[role] = found
    # a "date" column must really parse as dates; otherwise un-assign it
    if mapping.get("date"):
        parsed = pd.to_datetime(df[mapping["date"]], errors="coerce")
        if parsed.notna().mean() < 0.8:
            mapping["date"] = None
    if not mapping.get("date"):                                 # look for any column that parses as dates
        for c in df.columns:
            if c in used or df[c].dtype.kind in "fi":
                continue
            if pd.to_datetime(df[c], errors="coerce").notna().mean() > 0.9:
                mapping["date"] = c
                break
    return mapping


def missing_required(mapping: dict) -> list:
    """Names of the required columns (Date, Temperature, Humidity, Soil Moisture, Rainfall) that were not found."""
    return [REQUIRED_NAMES[k] for k in REQUIRED if not (mapping or {}).get(k)]


def check_required(mapping: dict):
    miss = missing_required(mapping)
    if miss:
        raise DatasetError("Required column(s) missing: " + ", ".join(miss) +
                           ". The dataset must contain Date, Temperature, Humidity, Soil Moisture and Rainfall. "
                           "If the columns exist under other names, select them below and analyse again.")


# ---------------------------------------------------------------------------- analysis
class Steps:
    """Collects the visible cleaning / analysis steps and reports progress."""

    def __init__(self, cb):
        self.cb, self.items = cb, []

    def start(self, key, title, percent):
        self.items.append({"id": key, "title": title, "status": "running", "detail": "", "metrics": {}})
        self.cb(percent, title, self.items)

    def done(self, detail, metrics=None, status="done", percent=None):
        s = self.items[-1]
        s.update(status=status, detail=detail, metrics=metrics or {})
        self.cb(percent, s["title"], self.items)


def _positive_mask(series: pd.Series):
    """Turn a yes/no style column into 0/1. Returns (y, description)."""
    vals = series.dropna().astype(str).str.strip().str.lower()
    uniq = sorted(vals.unique())
    if len(uniq) != 2:
        raise DatasetError(f"The target column '{series.name}' must have exactly 2 classes (e.g. Yes/No or 0/1) "
                           f"but has {len(uniq)}: {', '.join(uniq[:6])}{'...' if len(uniq) > 6 else ''}")
    pos = next((u for u in uniq if u in YES_WORDS), None)
    if pos is None:
        pos = uniq[-1]
    y = series.astype(str).str.strip().str.lower().eq(pos).astype(int)
    neg = [u for u in uniq if u != pos][0]
    return y, f"'{pos}' = irrigation needed (1), '{neg}' = not needed (0)"


def run_analysis(path: str, mapping: dict, derive_threshold, model_path: str, progress_cb=None) -> dict:
    cb = progress_cb or (lambda *a: None)
    st = Steps(cb)
    raw = read_table(path)
    info = file_info(raw, os.path.getsize(path), os.path.basename(path))
    mapping = {k: (v if v in raw.columns else None) for k, v in (mapping or detect_mapping(raw)).items()}
    check_required(mapping)
    present = list(FEATURE_KEYS)

    # ---- 1. load -----------------------------------------------------------------
    st.start("load", "Reading dataset", 3)
    st.done(f"Loaded {info['rows']:,} rows x {info['columns']} columns from {info['filename']} ({info['size_human']}).",
            {"rows": info["rows"], "columns": info["columns"]}, percent=6)

    # ---- 2. columns / types ---------------------------------------------------------
    st.start("types", "Detecting columns and converting data types", 8)
    df = pd.DataFrame(index=raw.index)
    converted = []
    for key in FEATURE_KEYS:
        col = mapping.get(key)
        if col:
            before = raw[col].dtype
            df[key] = pd.to_numeric(raw[col].astype(str).str.replace(",", ".", regex=False).str.extract(r"(-?\d+\.?\d*)")[0]
                                    if raw[col].dtype == object else raw[col], errors="coerce")
            if before == object:
                converted.append(f"{col} (text -> number)")
    scaled = []
    for key in ("soil_moisture", "humidity"):                       # fractions 0-1 -> percent
        if key in df and df[key].notna().any() and df[key].max() <= 1.0 and df[key].min() >= 0:
            df[key] = df[key] * 100
            scaled.append(f"{mapping[key]} (0-1 -> %)")
    if mapping.get("crop"):
        df["crop"] = raw[mapping["crop"]].astype(str).str.strip().str.title().replace({"Nan": np.nan, "": np.nan})
    date_col = mapping["date"]
    df["date"] = pd.to_datetime(raw[date_col], errors="coerce")
    if df["date"].notna().mean() < 0.8:
        raise DatasetError(f"The Date column '{date_col}' could not be read as dates (only "
                           f"{100 * df['date'].notna().mean():.0f}% of the values are valid dates).")
    target_derived = False
    if mapping.get("target"):
        df["_target_raw"] = raw[mapping["target"]]
    st.done("Mapped: " + ", ".join(f"{REQUIRED_NAMES.get(k, k.title())} <- '{v}'" for k, v in mapping.items() if v)
            + (f". Converted: {'; '.join(converted)}." if converted else "")
            + (f" Rescaled: {'; '.join(scaled)}." if scaled else ""),
            {"mapped_columns": sum(1 for v in mapping.values() if v)}, percent=14)

    # ---- 3. duplicates --------------------------------------------------------------
    st.start("duplicates", "Removing duplicate records", 18)
    n0 = len(df)
    dup_mask = raw.duplicated()
    df = df[~dup_mask.values]
    removed = n0 - len(df)
    st.done(f"{removed:,} duplicate row(s) removed." if removed else "No duplicate rows found.",
            {"before": n0, "after": len(df), "removed": removed}, percent=22)

    # ---- 4. impossible readings -----------------------------------------------------
    st.start("invalid", "Detecting impossible sensor readings", 25)
    invalid_total, invalid_detail = 0, []
    for key in present:
        lo, hi = HARD_LIMITS[key]
        bad = ((df[key] < lo) | (df[key] > hi)) & df[key].notna()
        if bad.any():
            invalid_total += int(bad.sum())
            invalid_detail.append(f"{LABELS[key]}: {int(bad.sum())}")
            df.loc[bad, key] = np.nan
    st.done((f"{invalid_total} reading(s) outside physical limits were marked missing ({'; '.join(invalid_detail)})."
             if invalid_total else "All readings are within physical limits."),
            {"invalid_values": invalid_total}, percent=30)

    # ---- 5. missing values: rows are DROPPED, never filled with invented numbers ----------------
    st.start("missing", "Handling missing values", 33)
    miss_before = {k: int(df[k].isna().sum()) for k in present}
    miss_before["date"] = int(df["date"].isna().sum())
    n_before = len(df)
    df = df.dropna(subset=present + ["date"])
    dropped = n_before - len(df)
    if len(df) < 30 or len(df) < 0.5 * n_before:
        raise DatasetError(f"Too many missing values: only {len(df)} of {n_before} rows have all of Date, Temperature, Humidity, "
                           "Soil Moisture and Rainfall. Please upload a more complete dataset.")
    df = df.sort_values("date", kind="stable")
    if "crop" in df:
        df["crop"] = df["crop"].fillna("Unknown")
    st.done((f"{dropped:,} row(s) with a missing value were removed (no values are estimated or invented). "
             + ", ".join(f"{(LABELS.get(k) or 'Date')}: {v}" for k, v in miss_before.items() if v)) if dropped else
            "No missing values in the required columns.",
            {"removed_rows": dropped, **{f"missing_{k}": v for k, v in miss_before.items()}}, percent=40)

    # ---- 6. outliers: detected and reported, values are left unchanged -------------------------------
    st.start("outliers", "Detecting outliers (IQR rule)", 43)
    out_info, out_total = {}, 0
    for k in present:
        q1, q3 = df[k].quantile([.25, .75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((df[k] < lo) | (df[k] > hi)).sum()) if iqr > 0 else 0
        out_info[k] = {"count": n_out, "lower": float(lo), "upper": float(hi)}
        out_total += n_out
    st.done(f"{out_total:,} outlier value(s) detected with the IQR rule. They are real measurements, so they were kept unchanged."
            if out_total else "No outliers detected.",
            {"outliers": out_total, **{f"outliers_{k}": v["count"] for k, v in out_info.items()}}, percent=50)

    # ---- 7. target ------------------------------------------------------------------
    st.start("target", "Preparing the irrigation label (target)", 53)
    df = df.reset_index(drop=True)
    if "_target_raw" in df:
        keep = df["_target_raw"].notna()
        df = df[keep].copy()
        df["target"], target_note = _positive_mask(df["_target_raw"])
        status = "done"
    else:
        # No irrigation column: label = "the NEXT reading is dry", where dry means below the lowest third of the
        # uploaded soil-moisture values. Today's readings therefore predict the coming need (no label leakage).
        target_derived = True
        if not derive_threshold:
            derive_threshold = float(round(df["soil_moisture"].quantile(1 / 3), 1))
        nxt = df.groupby("crop")["soil_moisture"].shift(-1) if "crop" in df else df["soil_moisture"].shift(-1)
        df = df[nxt.notna()].copy()
        df["target"] = (nxt[nxt.notna()] <= derive_threshold).astype(int)
        target_note = (f"The file has no irrigation column, so the label was DERIVED from your own data: 'irrigation needed' = the next "
                       f"reading of soil moisture is at or below {derive_threshold:g}% (the lowest third of your soil-moisture values). "
                       "The SVM learns to predict that from today's readings. Upload a file with a real irrigation column for decision-based predictions.")
        status = "warning"
    df = df.drop(columns=["_target_raw"], errors="ignore").reset_index(drop=True)
    if df["target"].nunique() < 2:
        raise DatasetError("After cleaning, only one class remains in the target; an SVM needs both Yes and No examples.")
    st.done(target_note, {"yes": int(df["target"].sum()), "no": int((df["target"] == 0).sum())}, status=status, percent=56)

    # ---- 8. normalisation -----------------------------------------------------------
    st.start("normalize", "Feature scaling (normalisation)", 58)
    st.done("Features are standardised (z = (x - mean) / std) inside the SVM pipeline so the scaler is fitted on training data only; "
            "crop names are one-hot encoded.", {"method": "StandardScaler + OneHotEncoder"}, percent=60)
    cleaning_steps_before_eda = [dict(s) for s in st.items]

    # ---- 9. statistics ---------------------------------------------------------------
    st.start("eda", "Exploratory data analysis", 62)
    stats = {}
    for k in present:
        s = df[k]
        mode = s.round(1).mode()
        stats[k] = {"count": int(s.count()), "mean": s.mean(), "median": s.median(), "mode": float(mode.iloc[0]) if len(mode) else None,
                    "std": s.std(), "min": s.min(), "max": s.max(), "q1": s.quantile(.25), "q3": s.quantile(.75), "skew": s.skew()}
    corr_cols = present + ["target"]
    corr = df[corr_cols].corr().fillna(0)
    corr_labels = [LABELS.get(c, "Irrigation needed") for c in corr_cols]
    st.done("Mean, median, mode, standard deviation, minimum, maximum and the correlation matrix were calculated.",
            {"numeric_columns": len(present)}, percent=68)

    # ---- 10. chart data -----------------------------------------------------------------
    st.start("charts", "Generating graphs", 70)
    charts = build_charts(df, present, mapping, corr)
    st.done(f"{len(charts['timeseries']['series'])} time-series, histograms, box plots, scatter, bar and pie charts prepared.", percent=76)

    # ---- 11. SVM -----------------------------------------------------------------------
    st.start("svm", "Training the SVM model", 78)
    model_info = train_svm(df, present, model_path)
    m = model_info["metrics"]
    st.done(f"RBF-SVM trained on {model_info['train_rows']:,} rows (best C={model_info['best_params']['C']}, "
            f"gamma={model_info['best_params']['gamma']}). Test accuracy {m['accuracy'] * 100:.1f}%, F1 {m['f1'] * 100:.1f}%.",
            {"accuracy": m["accuracy"]}, percent=90)

    # ---- 12. findings -------------------------------------------------------------------------
    st.start("findings", "Summarising the findings", 92)
    recs = recommendations(df, present, stats, model_info, target_derived, info, derive_threshold)
    st.done(f"{len(recs)} finding(s) written from your data.", percent=97)

    crops = sorted(df["crop"].unique().tolist()) if "crop" in df else []
    ranges = {k: [float(df[k].min()), float(df[k].max())] for k in present}
    results = {
        "info": info, "mapping": mapping, "features": present, "target_derived": target_derived,
        "derive_threshold": derive_threshold, "target_note": target_note,
        "cleaning": {"steps": st.items[:len(cleaning_steps_before_eda)], "rows_before": info["rows"], "rows_after": int(len(df)),
                     "outliers": out_info, "missing_before": miss_before},
        "steps": st.items, "stats": stats, "correlation": {"labels": corr_labels, "matrix": corr.values.tolist()},
        "charts": charts, "model": model_info,
        "recommendations": recs, "crops": crops, "ranges": ranges,
        "labels": {k: LABELS[k] for k in present}, "units": {k: UNITS[k] for k in present},
    }
    cb(100, "Analysis complete", st.items)
    return jsonable(results)


# ---------------------------------------------------------------------------- charts
def _downsample(df, max_points=400):
    if len(df) <= max_points:
        return df
    idx = np.linspace(0, len(df) - 1, max_points).astype(int)
    return df.iloc[idx]


def build_charts(df, present, mapping, corr):
    # time series: daily values if a date exists, otherwise record number
    has_date = True
    if has_date:
        d = df.dropna(subset=["date"]).copy()
        d["day"] = d["date"].dt.floor("D")
        agg = {k: ("sum" if k == "rainfall" else "mean") for k in present}
        g = d.groupby("day").agg(agg).reset_index()
        if len(g) > 400:                                  # long history -> weekly
            g = d.set_index("date").resample("W").agg(agg).dropna(how="all").reset_index().rename(columns={"date": "day"})
        labels = g["day"].dt.strftime("%Y-%m-%d").tolist()
        series = {k: g[k].round(2).tolist() for k in present}
        x_title = "Date"
    else:
        g = _downsample(df.reset_index())
        labels = [f"#{int(i) + 1}" for i in g["index"]]
        series = {k: g[k].round(2).tolist() for k in present}
        x_title = "Record number"
    ts = {"labels": labels, "series": series, "x_title": x_title, "has_date": bool(has_date)}

    hist = {}
    for k in present:
        counts, edges = np.histogram(df[k], bins=20)
        hist[k] = {"counts": counts.tolist(), "edges": [round(float(e), 2) for e in edges]}

    box = {}
    for k in present:
        s = df[k]
        q1, med, q3 = s.quantile([.25, .5, .75])
        iqr = q3 - q1
        lo_w, hi_w = s[s >= q1 - 1.5 * iqr].min(), s[s <= q3 + 1.5 * iqr].max()
        box[k] = {"min": s.min(), "q1": q1, "median": med, "q3": q3, "max": s.max(), "whisker_low": lo_w, "whisker_high": hi_w,
                  "outliers": int(((s < lo_w) | (s > hi_w)).sum())}

    # scatter: soil moisture vs temperature (or the best other feature)
    other = next((k for k in ["temperature", "humidity", "rainfall"] if k in present), present[0])
    samp = df.sample(min(500, len(df)), random_state=1)
    scatter = {"x_key": "soil_moisture", "y_key": other,
               "points": [{"x": round(float(a), 2), "y": round(float(b), 2), "c": int(c)}
                          for a, b, c in zip(samp["soil_moisture"], samp[other], samp["target"])]}

    # bar chart: irrigation share per crop, or per soil-moisture band when there is no crop column
    if "crop" in df and df["crop"].nunique() > 1:
        grp = df.groupby("crop")["target"].mean().sort_values(ascending=False).head(12)
        bar = {"title": "Share of records needing irrigation, by crop (%)", "labels": grp.index.tolist(),
               "values": (grp * 100).round(1).tolist()}
    else:
        bands = pd.qcut(df["soil_moisture"], q=4, duplicates="drop")
        grp = df.groupby(bands, observed=True)["target"].mean()
        bar = {"title": "Share of records needing irrigation, by soil-moisture quartile (%)",
               "labels": [f"{iv.left:.0f}-{iv.right:.0f}%" for iv in grp.index], "values": (grp * 100).round(1).tolist()}

    pies = {"irrigation": {"title": "Irrigation needed", "labels": ["Not needed", "Needed"],
                           "values": [int((df["target"] == 0).sum()), int((df["target"] == 1).sum())]}}
    if "crop" in df and 1 < df["crop"].nunique() <= 12:
        vc = df["crop"].value_counts()
        pies["crop"] = {"title": "Records by crop", "labels": vc.index.tolist(), "values": vc.values.tolist()}
    return {"timeseries": ts, "histograms": hist, "boxplots": box, "scatter": scatter, "bar": bar, "pies": pies}


# ---------------------------------------------------------------------------- SVM
def train_svm(df, present, model_path):
    use_crop = "crop" in df and 1 < df["crop"].nunique() <= 30
    feats = present + (["crop"] if use_crop else [])
    d = df[feats + ["target"]]
    if len(d) > 6000:
        d, _ = train_test_split(d, train_size=6000, stratify=d["target"], random_state=42)
    X, y = d[feats], d["target"]
    if y.value_counts().min() < 10:
        raise DatasetError("The smaller class has fewer than 10 rows; add more examples of both Yes and No.")
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    transformers = [("num", StandardScaler(), present)]
    if use_crop:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), ["crop"]))
    prep = ColumnTransformer(transformers)
    grid = GridSearchCV(Pipeline([("prep", prep), ("svm", SVC(kernel="rbf"))]),
                        {"svm__C": [1, 10, 50], "svm__gamma": ["scale", 0.05, 0.2]},
                        cv=3, scoring="f1", n_jobs=-1).fit(Xtr, ytr)
    best = {k.replace("svm__", ""): v for k, v in grid.best_params_.items()}
    pipe = Pipeline([("prep", ColumnTransformer(transformers)),
                     ("svm", SVC(kernel="rbf", probability=True, random_state=42, **best))]).fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    score = pipe.decision_function(Xte)
    fpr, tpr, _ = roc_curve(yte, score)
    step = max(1, len(fpr) // 120)
    cm = confusion_matrix(yte, pred, labels=[0, 1])
    metrics = {"accuracy": accuracy_score(yte, pred), "precision": precision_score(yte, pred, zero_division=0),
               "recall": recall_score(yte, pred, zero_division=0), "f1": f1_score(yte, pred, zero_division=0),
               "roc_auc": roc_auc_score(yte, score)}
    joblib.dump({"pipeline": pipe, "features": feats, "present": present, "use_crop": use_crop,
                 "crops": sorted(df["crop"].unique().tolist()) if "crop" in df else []}, model_path)
    return ({"features": feats, "metrics": {k: round(float(v), 4) for k, v in metrics.items()}, "confusion": cm.tolist(),
             "roc": {"fpr": fpr[::step].round(4).tolist(), "tpr": tpr[::step].round(4).tolist()},
             "best_params": {k: (v if isinstance(v, str) else float(v)) for k, v in best.items()},
             "train_rows": int(len(Xtr)), "test_rows": int(len(Xte)), "kernel": "rbf",
             "cv_f1": round(float(grid.best_score_), 4)})


# ---------------------------------------------------------------------------- findings
def recommendations(df, present, stats, model, derived, info, thr):
    """Plain-language findings. Every number comes from the uploaded dataset and its SVM."""
    recs = []
    share = 100 * df["target"].mean()
    recs.append(f"{share:.0f}% of the usable records are labelled 'irrigation needed'. "
                + ("The classes are well balanced." if 30 <= share <= 70 else "The classes are imbalanced, so check recall and F1 as well as accuracy."))
    if derived:
        recs.append(f"The label was derived from your soil moisture (next reading at or below {thr:g}%) because the file has no irrigation column. "
                    "Upload data that contains the real irrigation decisions for decision-based predictions.")
    acc, f1 = model["metrics"]["accuracy"], model["metrics"]["f1"]
    quality = min(acc, f1)                      # F1 is the honest score when one class is rare
    recs.append(f"The SVM reached {acc * 100:.1f}% test accuracy (F1 {f1 * 100:.1f}%). "
                + ("This is a strong result for this file." if quality >= 0.9 else
                   "Performance is moderate; more rows, more informative sensors or cleaner labels would help." if quality >= 0.75 else
                   "Performance is low; the available columns may not explain the irrigation need well."))
    corr = df[present + ["target"]].corr()["target"].drop("target").fillna(0)
    top = corr.abs().sort_values(ascending=False).index[0]
    recs.append(f"{LABELS[top]} is the variable most strongly related to the irrigation label (correlation {corr[top]:+.2f}).")
    sm = stats["soil_moisture"]
    recs.append(f"Soil moisture ranged from {sm['min']:.1f}% to {sm['max']:.1f}% (mean {sm['mean']:.1f}%, median {sm['median']:.1f}%).")
    wet = 100 * float((df["rainfall"] > 0).mean())
    recs.append(f"Rain was recorded on {wet:.0f}% of the records (total {df['rainfall'].sum():,.0f} mm, "
                f"maximum {stats['rainfall']['max']:.1f} mm in one record).")
    if info["missing_percent"] > 5:
        recs.append(f"{info['missing_percent']:.1f}% of the original cells were missing. Check sensor connectivity to improve data quality.")
    return recs


# ---------------------------------------------------------------------------- prediction with an uploaded-data model
_cache = {}


def load_user_model(path):
    m = os.path.getmtime(path)
    if path not in _cache or _cache[path][0] != m:
        _cache[path] = (m, joblib.load(path))
    return _cache[path][1]


def predict_with_model(model_path, temperature, humidity, soil_moisture, rainfall, crop):
    bundle = load_user_model(model_path)
    row = {"temperature": temperature, "humidity": humidity, "soil_moisture": soil_moisture, "rainfall": rainfall}
    if bundle["use_crop"]:
        row["crop"] = crop if crop in bundle["crops"] else bundle["crops"][0]
    X = pd.DataFrame([row])[bundle["features"]]
    pipe = bundle["pipeline"]
    needs = bool(pipe.predict(X)[0])
    p_yes = float(pipe.predict_proba(X)[0][list(pipe.classes_).index(1)])
    return {"irrigation_required": needs, "prediction": "Irrigation Required" if needs else "No Irrigation Needed",
            "probability_yes": round(100 * p_yes, 1), "confidence": round(100 * max(p_yes, 1 - p_yes), 1)}
