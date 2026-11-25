"""
svd_module.py - Singular Value Decomposition as a feature-reduction layer in front of the SVM.

Only numbers from the uploaded dataset are used. Steps:

    1. feature matrix X   (rows = records, columns = the numeric features found in the file)
    2. standardise        Xs = (X - mean) / std            (every sensor gets the same weight)
    3. decompose          Xs = U * Sigma * V^T             (scipy.linalg.svd, economy size)
         U      : record coordinates in the new (component) space
         Sigma  : singular values = importance of each component; variance_i = sigma_i^2 / sum(sigma^2)
         V^T    : loadings = contribution of every original feature to every component
    4. reduce             keep the first k components that preserve at least `threshold` of the variance (default 95 %)
                          scores = Xs @ V[:, :k]   (= U[:, :k] * Sigma[:k])

`SvdReducer` is a scikit-learn transformer so that the same decomposition is fitted on the TRAINING rows only inside the SVM
pipeline (no information leaks from the test rows).
"""
import numpy as np
from scipy import linalg
from sklearn.base import BaseEstimator, TransformerMixin

THRESHOLD = 0.95


def choose_k(explained, threshold=THRESHOLD):
    """Smallest number of components whose cumulative explained variance reaches the threshold."""
    cum = np.cumsum(explained)
    return int(min(len(cum), np.searchsorted(cum, threshold - 1e-12) + 1))


class SvdReducer(BaseEstimator, TransformerMixin):
    """Standardise -> SVD -> project onto the first k right singular vectors."""

    def __init__(self, n_components=2):
        self.n_components = n_components

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.mean_ = X.mean(axis=0)
        self.std_ = X.std(axis=0)
        self.std_[self.std_ == 0] = 1.0
        _, s, vt = linalg.svd((X - self.mean_) / self.std_, full_matrices=False)
        self.singular_values_ = s
        self.components_ = vt[: self.n_components]
        return self

    def transform(self, X):
        return ((np.asarray(X, dtype=float) - self.mean_) / self.std_) @ self.components_.T


def analyse(X, names, threshold=THRESHOLD, target=None, max_points=400):
    """Full descriptive SVD of the cleaned feature matrix, as JSON-ready numbers for the dashboard."""
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    mean, std = X.mean(axis=0), X.std(axis=0)
    std[std == 0] = 1.0
    Xs = (X - mean) / std
    U, s, vt = linalg.svd(Xs, full_matrices=False)
    var = s ** 2
    explained = var / var.sum()
    cum = np.cumsum(explained)
    k = choose_k(explained, threshold)
    full_err = float(np.linalg.norm(Xs - (U * s) @ vt) / np.linalg.norm(Xs))           # ~1e-15: U Sigma V^T reproduces X exactly
    Xk = (U[:, :k] * s[:k]) @ vt[:k]
    red_err = float(np.linalg.norm(Xs - Xk) / np.linalg.norm(Xs))
    # contribution of every original feature to the kept components (share of its squared loadings, weighted by variance)
    contrib = (vt[:k] ** 2 * explained[:k, None]).sum(axis=0)
    contrib = contrib / contrib.sum()
    idx = np.unique(np.linspace(0, n - 1, min(n, max_points)).astype(int))
    scores = U[:, :min(2, p)] * s[:min(2, p)]
    out = {
        "features": list(names), "n_samples": int(n), "n_features": int(p), "n_components": k, "threshold": threshold,
        "singular_values": s.round(5).tolist(), "explained_variance_ratio": explained.round(6).tolist(),
        "cumulative_variance": cum.round(6).tolist(), "variance_preserved": float(cum[k - 1]),
        "loadings": vt[:k].round(4).tolist(), "all_loadings": vt.round(4).tolist(),
        "feature_contribution": contrib.round(4).tolist(),
        "reconstruction_error_full": full_err, "reconstruction_error_reduced": red_err,
        "condition_number": float(s[0] / s[-1]) if s[-1] > 1e-12 else None,
        "shapes": {"U": [int(n), int(p)], "Sigma": [int(p), int(p)], "Vt": [int(p), int(p)]},
        "pc_scatter": {"x": scores[idx, 0].round(3).tolist(), "y": (scores[idx, 1] if p > 1 else scores[idx, 0]).round(3).tolist(),
                       "c": (np.asarray(target)[idx].astype(int).tolist() if target is not None else None)},
        "reduced": bool(k < p),
    }
    return out
