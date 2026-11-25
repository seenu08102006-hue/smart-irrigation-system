"""
train_models.py
===============
Trains and compares four classifiers on the cleaned irrigation data:
    SVM (RBF)  |  Decision Tree  |  Random Forest  |  Logistic Regression

For a FAIR comparison every model
  * gets the same preprocessing (scaling + one-hot) inside a Pipeline,
  * is tuned with the same 5-fold GridSearchCV (score = F1),
  * is evaluated on the same untouched 20 % test set.

Outputs: models/*.joblib, reports/metrics.json, reports/model_comparison.csv, figures in static/figures.

Run:  python src/train_models.py
"""
import json
import os
import time
import warnings

# newer scikit-learn prints a deprecation warning for SVC(probability=True); it still works
os.environ["PYTHONWARNINGS"] = "ignore::FutureWarning"
warnings.filterwarnings("ignore", category=FutureWarning)

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

import config
from preprocess import make_preprocessor

COLORS = {"SVM": "#16a34a", "Decision Tree": "#f97316", "Random Forest": "#0ea5e9", "Logistic Regression": "#8b5cf6"}
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})


def candidates():
    """name -> (classifier, hyper-parameter grid)."""
    rs = config.RANDOM_STATE
    return {
        "SVM": (SVC(kernel="rbf", probability=True, random_state=rs),
                {"clf__C": [0.5, 1, 5, 10, 50], "clf__gamma": ["scale", 0.02, 0.05, 0.1, 0.3]}),
        "Decision Tree": (DecisionTreeClassifier(random_state=rs),
                          {"clf__max_depth": [3, 5, 8, 12, None], "clf__min_samples_leaf": [1, 5, 20]}),
        "Random Forest": (RandomForestClassifier(random_state=rs, n_jobs=-1),
                          {"clf__n_estimators": [100, 200], "clf__max_depth": [6, 12, None]}),
        "Logistic Regression": (LogisticRegression(max_iter=2000),
                                {"clf__C": [0.01, 0.1, 1, 10, 100]}),
    }


def save_fig(fig, name):
    os.makedirs(config.FIG_DIR, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(config.FIG_DIR, name))
    plt.close(fig)
    print("  figure ->", name)


def decision_boundary_figure(X_train, y_train):
    """Illustration: an SVM that only sees soil moisture and temperature, so we can draw its boundary in 2-D."""
    from sklearn.preprocessing import StandardScaler
    cols = ["soil_moisture", "temperature"]
    sc = StandardScaler().fit(X_train[cols])
    svm = SVC(kernel="rbf", C=10, gamma="scale").fit(sc.transform(X_train[cols]), y_train)
    gx, gy = np.meshgrid(np.linspace(0, 100, 250), np.linspace(5, 50, 250))
    zz = svm.predict(sc.transform(pd.DataFrame({"soil_moisture": gx.ravel(), "temperature": gy.ravel()})))
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.contourf(gx, gy, zz.reshape(gx.shape), alpha=.25, levels=[-.5, .5, 1.5], colors=["#16a34a", "#0ea5e9"])
    s = X_train.assign(y=y_train.values).sample(700, random_state=1)
    for label, c, n in [(0, "#16a34a", "No irrigation"), (1, "#0ea5e9", "Irrigation")]:
        p = s[s.y == label]
        ax.scatter(p["soil_moisture"], p["temperature"], s=10, c=c, label=n)
    ax.set_xlabel("Soil moisture (%)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("SVM (RBF) decision regions - 2-D illustration")
    ax.legend(loc="upper right")
    save_fig(fig, "10_svm_decision_boundary.png")


def main():
    df = pd.read_csv(config.CLEAN_CSV)
    X = df[config.NUMERIC_FEATURES + config.CATEGORICAL_FEATURES]
    y = df[config.TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=config.RANDOM_STATE)
    print(f"Train = {len(X_train)} rows, Test = {len(X_test)} rows")

    cv = StratifiedKFold(5, shuffle=True, random_state=config.RANDOM_STATE)
    results, fitted, matrices, roc_data = [], {}, {}, {}

    for name, (clf, grid) in candidates().items():
        pipe = Pipeline([("prep", make_preprocessor()), ("clf", clf)])
        t0 = time.time()
        search = GridSearchCV(pipe, grid, cv=cv, scoring="f1", n_jobs=-1).fit(X_train, y_train)
        train_time = time.time() - t0
        model = search.best_estimator_

        pred = model.predict(X_test)
        proba = model.predict_proba(X_test)[:, 1]
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1")
        row = {
            "Model": name,
            "Accuracy": accuracy_score(y_test, pred),
            "Precision": precision_score(y_test, pred),
            "Recall": recall_score(y_test, pred),
            "F1-score": f1_score(y_test, pred),
            "ROC-AUC": roc_auc_score(y_test, proba),
            "CV F1 (mean)": cv_scores.mean(),
            "CV F1 (std)": cv_scores.std(),
            "Train time (s)": train_time,
            "Best params": {k.replace("clf__", ""): v for k, v in search.best_params_.items()},
        }
        results.append(row)
        fitted[name] = model
        matrices[name] = confusion_matrix(y_test, pred)
        roc_data[name] = roc_curve(y_test, proba)
        print(f"{name:20s} acc={row['Accuracy']:.4f} prec={row['Precision']:.4f} "
              f"rec={row['Recall']:.4f} f1={row['F1-score']:.4f} auc={row['ROC-AUC']:.4f}  {row['Best params']}")

    table = pd.DataFrame(results)
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    table.drop(columns="Best params").round(4).to_csv(config.COMPARISON_CSV, index=False)

    # ---------- figures ----------
    fig, axes = plt.subplots(2, 2, figsize=(8, 6.6))
    for ax, name in zip(axes.ravel(), matrices):
        cm = matrices[name]
        ax.imshow(cm, cmap="Greens")
        ax.set_xticks([0, 1], ["No", "Yes"])
        ax.set_yticks([0, 1], ["No", "Yes"])
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(name, fontweight="bold")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=14,
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
    save_fig(fig, "09_confusion_matrices.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    metrics = ["Accuracy", "Precision", "Recall", "F1-score"]
    w = 0.2
    for i, r in enumerate(results):
        ax.bar(np.arange(4) + i * w, [r[m] * 100 for m in metrics], w, label=r["Model"], color=COLORS[r["Model"]])
    ax.set_xticks(np.arange(4) + 1.5 * w, metrics)
    lo = min(r[m] for r in results for m in metrics) * 100
    ax.set_ylim(max(0, lo - 8), 100)
    ax.set_ylabel("score (%)")
    ax.set_title("Model comparison on the test set")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=8, frameon=False)
    save_fig(fig, "11_model_comparison.png")

    fig, ax = plt.subplots(figsize=(5.8, 4.6))
    for name, (fpr, tpr, _) in roc_data.items():
        auc = [r["ROC-AUC"] for r in results if r["Model"] == name][0]
        ax.plot(fpr, tpr, color=COLORS[name], label=f"{name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=.8)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves")
    ax.legend(fontsize=8)
    save_fig(fig, "12_roc_curves.png")

    rf = fitted["Random Forest"]
    names = (config.NUMERIC_FEATURES + [f"crop={c}" for c in config.CROPS])
    imp = pd.Series(rf.named_steps["clf"].feature_importances_, index=names).sort_values()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(imp.index, imp.values, color="#16a34a")
    ax.set_title("Random Forest feature importance")
    save_fig(fig, "13_feature_importance.png")

    decision_boundary_figure(X_train, y_train)

    # ---------- choose + save models ----------
    best_name = table.sort_values(["F1-score", "Accuracy"], ascending=False).iloc[0]["Model"]
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    joblib.dump(fitted["SVM"], config.SVM_MODEL_PATH)             # the model used by the web app
    joblib.dump(fitted[best_name], config.BEST_MODEL_PATH)        # the numerically best model
    print(f"Best by F1-score: {best_name}.  SVM saved to {config.SVM_MODEL_PATH}")

    out = {
        "train_rows": len(X_train), "test_rows": len(X_test), "best_model_by_f1": best_name,
        "models": {r["Model"]: {k: (float(v) if isinstance(v, (np.floating, float)) else v)
                                for k, v in r.items() if k != "Model"} for r in results},
        "confusion_matrices": {n: m.tolist() for n, m in matrices.items()},
    }
    with open(config.METRICS_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("Metrics ->", config.METRICS_JSON)


if __name__ == "__main__":
    main()
