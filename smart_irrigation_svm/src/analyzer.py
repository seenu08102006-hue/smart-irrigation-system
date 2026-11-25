"""
analyzer.py
===========
Analyse ANY uploaded CSV and train an SVM on it.

Given a CSV file and the name of the column to predict (the "target"), analyze_csv():
  1. profiles and cleans the data (duplicates, missing values, ID-like / constant columns)
  2. draws EDA graphs (missing values, class balance, histograms, correlation heat-map)
  3. trains an RBF-SVM with GridSearchCV inside a scaling + encoding Pipeline
  4. draws SVM graphs: confusion matrix, ROC curve, decision regions, C-gamma heat-map,
     kernel comparison, learning curve, metric bars
  5. saves the trained pipeline (Joblib) and returns everything as a dictionary for the web page.

Works for binary and multi-class targets (ROC curve is drawn for binary targets only).
"""
import os
import threading
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import f_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, learning_curve, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")
_plot_lock = threading.Lock()          # Matplotlib is not thread-safe; Flask may use threads

MAX_ROWS = 6000                        # larger files are sampled so the SVM stays fast
MAX_CATEGORIES = 20                    # text columns with more distinct values are treated as IDs and dropped
PALETTE = ["#16a34a", "#0ea5e9", "#f97316", "#8b5cf6", "#ef4444", "#eab308", "#14b8a6", "#64748b"]


class AnalysisError(ValueError):
    """Problem with the uploaded data that the user can fix (shown in the web page)."""


def profile_columns(df: pd.DataFrame) -> list:
    """Short description of each column for the 'choose target' page."""
    rows = []
    for c in df.columns:
        rows.append({"name": c, "dtype": str(df[c].dtype), "unique": int(df[c].nunique()),
                     "missing": int(df[c].isna().sum()), "example": str(df[c].dropna().iloc[0]) if df[c].notna().any() else ""})
    return rows


def guess_target(df: pd.DataFrame) -> str:
    """Pick the most likely target: a column with 2-10 distinct values, preferring the last column."""
    for c in reversed(df.columns):
        if 2 <= df[c].nunique() <= 10:
            return c
    return df.columns[-1]


def _save(fig, folder, name):
    fig.tight_layout()
    fig.savefig(os.path.join(folder, name), dpi=120)
    plt.close(fig)
    return name


def analyze_csv(csv_path: str, target: str, fig_dir: str, model_path: str) -> dict:
    os.makedirs(fig_dir, exist_ok=True)
    try:
        raw = pd.read_csv(csv_path)
    except Exception as exc:
        raise AnalysisError(f"Could not read the file as CSV: {exc}")
    raw.columns = [str(c).strip() for c in raw.columns]
    if target not in raw.columns:
        raise AnalysisError(f"Target column '{target}' not found.")
    if raw.shape[0] < 30:
        raise AnalysisError("Need at least 30 rows to train and test a model.")

    figures, notes = [], []
    with _plot_lock:
        return _run(raw, target, fig_dir, model_path, figures, notes)


def _run(raw, target, fig_dir, model_path, figures, notes):
    # ------------------------------------------------------------------ cleaning
    report = {"rows_uploaded": int(len(raw)), "columns_uploaded": int(raw.shape[1])}
    df = raw.drop_duplicates().copy()
    report["duplicates_removed"] = report["rows_uploaded"] - len(df)
    report["missing_cells_before"] = int(df.isna().sum().sum())

    # figure 1: missing values per column (before filling)
    miss = raw.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False).head(15)
    if len(miss):
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        ax.barh(miss.index[::-1], miss.values[::-1], color="#f97316")
        ax.set_title("Missing values per column (uploaded file)")
        ax.spines[["top", "right"]].set_visible(False)
        figures.append((_save(fig, fig_dir, "eda_missing.png"), "Missing values", "Columns with empty cells before cleaning."))

    df = df.dropna(subset=[target])
    y_raw = df[target]
    if y_raw.nunique() < 2:
        raise AnalysisError("The target column has only one class - a classifier needs at least two.")
    if y_raw.dtype.kind in "fi" and y_raw.nunique() > 20:
        raise AnalysisError(f"'{target}' looks like a continuous number ({y_raw.nunique()} distinct values). "
                            "Choose a column with a few classes such as Yes/No or 0/1.")
    if y_raw.nunique() > 20:
        raise AnalysisError(f"'{target}' has {y_raw.nunique()} classes; at most 20 are supported.")

    X = df.drop(columns=[target])
    dropped = []
    for c in list(X.columns):
        s = X[c]
        if s.nunique(dropna=True) <= 1:
            dropped.append((c, "constant")); X = X.drop(columns=c); continue
        if s.dtype == object:
            as_num = pd.to_numeric(s, errors="coerce")
            if as_num.notna().mean() > 0.9:                      # numbers stored as text
                X[c] = as_num
            elif s.nunique() > MAX_CATEGORIES or s.nunique() > 0.5 * len(s):
                dropped.append((c, "too many distinct text values (looks like an ID/name)")); X = X.drop(columns=c)
        elif s.dtype.kind == "i" and s.nunique() == len(s) and s.is_monotonic_increasing:
            dropped.append((c, "looks like a row index/ID")); X = X.drop(columns=c)
    if X.shape[1] == 0:
        raise AnalysisError("No usable feature columns are left after removing IDs/constant columns.")
    for col, why in dropped:
        notes.append(f"Dropped column '{col}': {why}.")

    numeric = [c for c in X.columns if X[c].dtype.kind in "fiub"]
    categorical = [c for c in X.columns if c not in numeric]
    for c in numeric:                                             # booleans -> numbers
        X[c] = pd.to_numeric(X[c], errors="coerce")
    report["features_numeric"], report["features_categorical"] = numeric, categorical

    le = LabelEncoder()
    y = pd.Series(le.fit_transform(y_raw.astype(str)), index=y_raw.index)
    class_names = [str(c) for c in le.classes_]
    counts = y.value_counts().sort_index()
    if counts.min() < 5:
        raise AnalysisError(f"The smallest class ('{class_names[counts.idxmin()]}') has only {counts.min()} rows; need at least 5 per class.")

    if len(X) > MAX_ROWS:
        X, _, y, _ = train_test_split(X, y, train_size=MAX_ROWS, stratify=y, random_state=42)
        notes.append(f"File has more than {MAX_ROWS} rows; a stratified sample of {MAX_ROWS} rows was used so the SVM trains quickly.")
    report["rows_used"] = int(len(X))
    report["classes"] = class_names

    # figure 2: class balance
    fig, ax = plt.subplots(figsize=(5.2, 3.5))
    bars = ax.bar(class_names, counts.values, color=PALETTE[:len(class_names)])
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v}\n({100 * v / counts.sum():.0f}%)", ha="center", va="bottom", fontsize=8)
    ax.set_title(f"Class distribution of '{target}'")
    ax.set_ylabel("rows")
    ax.margins(y=.18)
    ax.spines[["top", "right"]].set_visible(False)
    figures.append((_save(fig, fig_dir, "eda_class_balance.png"), "Class balance", "How many rows belong to each class."))

    # figure 3: histograms of numeric features, split by class
    if numeric:
        show = numeric[:6]
        ncol = 3 if len(show) > 2 else len(show)
        nrow = int(np.ceil(len(show) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3 * nrow), squeeze=False)
        for ax, col in zip(axes.ravel(), show):
            for k, name in enumerate(class_names):
                vals = X.loc[y == k, col].dropna()
                ax.hist(vals, bins=25, alpha=.6, color=PALETTE[k % len(PALETTE)], label=name)
            ax.set_title(col, fontsize=10)
            ax.legend(fontsize=7)
        for ax in axes.ravel()[len(show):]:
            ax.axis("off")
        figures.append((_save(fig, fig_dir, "eda_histograms.png"), "Feature distributions", "Histogram of each numeric feature for every class."))

    # figure 4: correlation heat-map
    if len(numeric) >= 2:
        cols = numeric[:12]
        corr = X[cols].assign(**{target: y.values}).corr()
        fig, ax = plt.subplots(figsize=(6.2, 5.2))
        im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(corr)), corr.columns, fontsize=8)
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
        fig.colorbar(im, shrink=.8)
        ax.set_title("Correlation matrix")
        figures.append((_save(fig, fig_dir, "eda_correlation.png"), "Correlation heat-map", "Linear relationship between numeric features and the target."))

    # ------------------------------------------------------------------ model
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    transformers = []
    if numeric:
        transformers.append(("num", Pipeline([("fill", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric))
    if categorical:
        transformers.append(("cat", Pipeline([("fill", SimpleImputer(strategy="most_frequent")),
                                              ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical))
    prep = ColumnTransformer(transformers)

    folds = int(min(5, counts.min(), 5))
    folds = max(folds, 2)
    cv = StratifiedKFold(folds, shuffle=True, random_state=42)
    C_list, G_list = [0.1, 1, 10, 100], [0.001, 0.01, 0.1, 1]
    search = GridSearchCV(Pipeline([("prep", prep), ("svm", SVC(kernel="rbf"))]),
                          {"svm__C": C_list, "svm__gamma": G_list}, cv=cv, scoring="f1_weighted", n_jobs=-1)
    search.fit(X_tr, y_tr)
    model = search.best_estimator_
    pred = model.predict(X_te)

    binary = len(class_names) == 2
    avg = "binary" if binary else "weighted"
    metrics = {
        "accuracy": accuracy_score(y_te, pred),
        "precision": precision_score(y_te, pred, average=avg, zero_division=0),
        "recall": recall_score(y_te, pred, average=avg, zero_division=0),
        "f1": f1_score(y_te, pred, average=avg, zero_division=0),
        "cv_f1": float(search.best_score_),
    }
    if binary:
        scores = model.decision_function(X_te)
        metrics["roc_auc"] = roc_auc_score(y_te, scores)
    metrics = {k: round(float(v), 4) for k, v in metrics.items()}
    best = {k.replace("svm__", ""): (v if isinstance(v, str) else float(v)) for k, v in search.best_params_.items()}

    # --- SVM figure A: confusion matrix
    cm = confusion_matrix(y_te, pred)
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(class_names)), class_names, rotation=30, ha="right")
    ax.set_yticks(range(len(class_names)), class_names)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual"); ax.set_title("SVM confusion matrix (test set)")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=13, color="white" if cm[i, j] > cm.max() / 2 else "black")
    figures.append((_save(fig, fig_dir, "svm_confusion.png"), "SVM confusion matrix", "Correct predictions are on the diagonal."))

    # --- SVM figure B: ROC (binary only)
    if binary:
        fpr, tpr, _ = roc_curve(y_te, scores)
        fig, ax = plt.subplots(figsize=(4.8, 4.2))
        ax.plot(fpr, tpr, color="#16a34a", lw=2, label=f"SVM (AUC = {metrics['roc_auc']:.3f})")
        ax.plot([0, 1], [0, 1], "k--", lw=.8)
        ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate"); ax.set_title("SVM ROC curve"); ax.legend()
        figures.append((_save(fig, fig_dir, "svm_roc.png"), "SVM ROC curve", f"Positive class = '{class_names[1]}'. Closer to the top-left is better."))
    else:
        notes.append("ROC curve is only drawn for two-class targets.")

    # --- SVM figure C: metric bars
    labels = ["Accuracy", "Precision", "Recall", "F1"]
    vals = [metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1"]]
    fig, ax = plt.subplots(figsize=(5, 3.6))
    bars = ax.bar(labels, [v * 100 for v in vals], color=PALETTE[:4])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 100 + 1, f"{v * 100:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 112); ax.set_ylabel("score (%)"); ax.set_title("SVM performance on the test set")
    ax.spines[["top", "right"]].set_visible(False)
    figures.append((_save(fig, fig_dir, "svm_metrics.png"), "SVM performance metrics", "Averages are weighted when there are more than two classes."))

    # --- SVM figure D: C-gamma grid-search heat-map
    mean = search.cv_results_["mean_test_score"].reshape(len(C_list), len(G_list))
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    im = ax.imshow(mean, cmap="YlGn")
    ax.set_xticks(range(len(G_list)), [str(g) for g in G_list]); ax.set_yticks(range(len(C_list)), [str(c) for c in C_list])
    ax.set_xlabel("gamma"); ax.set_ylabel("C"); ax.set_title("Grid search: cross-validated F1")
    for i in range(len(C_list)):
        for j in range(len(G_list)):
            ax.text(j, i, f"{mean[i, j]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, shrink=.8)
    figures.append((_save(fig, fig_dir, "svm_grid.png"), "C and gamma tuning", f"Best combination: C = {best['C']}, gamma = {best['gamma']}."))

    # --- SVM figure E: kernel comparison
    kernel_rows = []
    for kernel in ["linear", "poly", "rbf", "sigmoid"]:
        k_pipe = Pipeline([("prep", prep), ("svm", SVC(kernel=kernel, C=best["C"] if kernel == "rbf" else 1.0,
                                                       gamma=best["gamma"] if kernel == "rbf" else "scale"))]).fit(X_tr, y_tr)
        kp = k_pipe.predict(X_te)
        kernel_rows.append({"kernel": kernel, "accuracy": round(float(accuracy_score(y_te, kp)), 4),
                            "f1": round(float(f1_score(y_te, kp, average=avg, zero_division=0)), 4)})
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    w = .38
    xs = np.arange(len(kernel_rows))
    ax.bar(xs - w / 2, [r["accuracy"] * 100 for r in kernel_rows], w, label="Accuracy", color="#16a34a")
    ax.bar(xs + w / 2, [r["f1"] * 100 for r in kernel_rows], w, label="F1", color="#0ea5e9")
    ax.set_xticks(xs, [r["kernel"] for r in kernel_rows]); ax.set_ylabel("score (%)")
    ax.set_ylim(max(0, min(min(r["accuracy"], r["f1"]) for r in kernel_rows) * 100 - 15), 102)
    ax.set_title("SVM kernel comparison"); ax.legend(fontsize=8); ax.spines[["top", "right"]].set_visible(False)
    figures.append((_save(fig, fig_dir, "svm_kernels.png"), "SVM kernel comparison", "Same data, four kernels (RBF uses the tuned C and gamma)."))

    # --- SVM figure F: learning curve
    try:
        sizes, tr_sc, va_sc = learning_curve(model, X_tr, y_tr, cv=min(3, folds), train_sizes=np.linspace(.2, 1, 5),
                                             scoring="accuracy", n_jobs=-1, random_state=42, shuffle=True)
        fig, ax = plt.subplots(figsize=(5.4, 3.8))
        for sc, lab, col in [(tr_sc, "Training", "#f97316"), (va_sc, "Validation", "#16a34a")]:
            ax.plot(sizes, sc.mean(1), "o-", color=col, label=lab)
            ax.fill_between(sizes, sc.mean(1) - sc.std(1), sc.mean(1) + sc.std(1), color=col, alpha=.15)
        ax.set_xlabel("training rows"); ax.set_ylabel("accuracy"); ax.set_title("SVM learning curve"); ax.legend()
        ax.spines[["top", "right"]].set_visible(False)
        figures.append((_save(fig, fig_dir, "svm_learning.png"), "Learning curve", "A large gap between the curves suggests over-fitting; both low suggests under-fitting."))
    except Exception:
        notes.append("Learning curve skipped (not enough data).")

    # --- SVM figure G: 2-D decision regions on the two most informative numeric features
    if len(numeric) >= 2:
        filled = X_tr[numeric].fillna(X_tr[numeric].median())
        f_scores, _ = f_classif(filled, y_tr)
        top2 = [numeric[i] for i in np.argsort(np.nan_to_num(f_scores))[::-1][:2]]
        sc2 = StandardScaler().fit(filled[top2])
        svm2 = SVC(kernel="rbf", C=best["C"], gamma=best["gamma"] if not isinstance(best["gamma"], str) else "scale").fit(sc2.transform(filled[top2]), y_tr)
        lo, hi = filled[top2].quantile(.01), filled[top2].quantile(.99)
        gx, gy = np.meshgrid(np.linspace(lo[top2[0]], hi[top2[0]], 220), np.linspace(lo[top2[1]], hi[top2[1]], 220))
        zz = svm2.predict(sc2.transform(pd.DataFrame({top2[0]: gx.ravel(), top2[1]: gy.ravel()}))).reshape(gx.shape)
        cmap = ListedColormap(PALETTE[:len(class_names)])
        fig, ax = plt.subplots(figsize=(6, 4.6))
        ax.contourf(gx, gy, zz, alpha=.22, cmap=cmap, levels=np.arange(-.5, len(class_names), 1))
        samp = filled[top2].assign(y=y_tr.values).sample(min(600, len(filled)), random_state=1)
        for k, name in enumerate(class_names):
            p = samp[samp.y == k]
            ax.scatter(p[top2[0]], p[top2[1]], s=12, color=PALETTE[k % len(PALETTE)], label=name, edgecolor="white", linewidth=.3)
        ax.set_xlim(lo[top2[0]], hi[top2[0]]); ax.set_ylim(lo[top2[1]], hi[top2[1]])
        ax.set_xlabel(top2[0]); ax.set_ylabel(top2[1]); ax.set_title("SVM decision regions (2 most informative features)")
        ax.legend(fontsize=8)
        figures.append((_save(fig, fig_dir, "svm_boundary.png"), "SVM decision regions",
                        f"2-D illustration using '{top2[0]}' and '{top2[1]}'; the real model uses all features."))
    else:
        notes.append("Decision-region plot needs at least two numeric features.")

    # ------------------------------------------------------------------ save + return
    joblib.dump({"model": model, "classes": class_names, "target": target, "features": list(X.columns)}, model_path)
    report["missing_cells_after"] = 0
    return {
        "target": target, "classes": class_names, "report": report, "metrics": metrics, "best_params": best,
        "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)), "cv_folds": folds, "kernels": kernel_rows,
        "figures": [{"file": f, "title": t, "caption": c} for f, t, c in figures], "notes": notes,
        "features": list(X.columns), "binary": binary,
    }
