"""
pde_model.py - soil-moisture dynamics solved with a finite-difference PDE, calibrated on the uploaded dataset.

Model (1-D vertical diffusion-reaction in the root zone, depth z normalised to 0 (surface) .. 1 (bottom)):

        d(theta)/dt = D * d2(theta)/dz2

  surface  z = 0 :  flux in  = alpha * Rainfall + beta * Irrigation
                    flux out = k_e * max(T, 0) * (1 - Humidity/100) / 100 * theta(0)      (evaporation, grows with temperature,
                                                                                            shrinks with humidity)
  bottom   z = 1 :  flux out = k_d * theta(1)                                           (drainage)

  theta = volumetric soil moisture (%). The soil-moisture reading of the dataset is treated as the root-zone mean of theta.

Numerical method: finite volumes in space (NZ cells), implicit (backward) Euler in time, tridiagonal system solved with the
Thomas algorithm (vectorised over many days at once with NumPy).

The parameters D, alpha, k_e, k_d (and beta when the file contains an irrigation column) are NOT assumed: they are fitted with
scipy.optimize.least_squares so that the PDE reproduces the uploaded soil-moisture series one day ahead. Temperature, humidity,
rainfall and soil moisture all come from the uploaded file; no data is generated.
"""
import numpy as np
from scipy.optimize import least_squares

NZ = 24          # grid cells over the depth
SUB = 4          # implicit time sub-steps per day
HORIZON = 7      # forecast days

NAMES = ["D", "alpha", "k_e", "k_d", "beta"]
LOWER = np.array([1e-3, 0.0, 0.0, 0.0, 0.0])
UPPER = np.array([5.0, 5.0, 20.0, 2.0, 50.0])
START = np.array([0.3, 0.3, 1.0, 0.05, 5.0])


class PdeError(ValueError):
    """The uploaded series is not suitable for the PDE model (user-readable)."""


def _thomas(a, b, c, d):
    """Solve tridiagonal systems row by row. a: sub-, b: main, c: super-diagonal, d: right-hand side; all (M, n)."""
    n = b.shape[1]
    cp = np.empty_like(b)
    dp = np.empty_like(b)
    cp[:, 0] = c[:, 0] / b[:, 0]
    dp[:, 0] = d[:, 0] / b[:, 0]
    for i in range(1, n):
        den = b[:, i] - a[:, i] * cp[:, i - 1]
        cp[:, i] = c[:, i] / den
        dp[:, i] = (d[:, i] - a[:, i] * dp[:, i - 1]) / den
    x = np.empty_like(b)
    x[:, -1] = dp[:, -1]
    for i in range(n - 2, -1, -1):
        x[:, i] = dp[:, i] - cp[:, i] * x[:, i + 1]
    return x


def step(theta, T, H, R, I, p, dt=1.0):
    """Advance moisture profiles `theta` (M, NZ) by `dt` days with the weather T, H, R and irrigation flag I (each (M,))."""
    theta = np.array(theta, dtype=float, copy=True)
    M, nz = theta.shape
    dz = 1.0 / nz
    h = dt / SUB
    r = p["D"] * h / dz ** 2
    evap_c = p["k_e"] * np.maximum(T, 0.0) * np.clip(1.0 - H / 100.0, 0.0, 1.0) / 100.0      # (M,)
    inflow = p["alpha"] * R + p.get("beta", 0.0) * I                                          # (M,) mean-% per day
    a = np.full((M, nz), -r)
    c = np.full((M, nz), -r)
    b = np.full((M, nz), 1.0 + 2.0 * r)
    b[:, 0] = 1.0 + r + h * evap_c / dz
    b[:, -1] = 1.0 + r + h * p["k_d"] / dz
    a[:, 0] = 0.0
    c[:, -1] = 0.0
    for _ in range(SUB):
        rhs = theta.copy()
        rhs[:, 0] += h * inflow / dz
        theta = np.clip(_thomas(a, b, c, rhs), 0.0, 100.0)
    return theta


def one_step_mean(soil, T, H, R, I, p):
    """Soil moisture one day ahead, starting from a uniform profile equal to today's reading (arrays of equal length)."""
    th = np.repeat(np.asarray(soil, float)[:, None], NZ, axis=1)
    return step(th, np.asarray(T, float), np.asarray(H, float), np.asarray(R, float), np.asarray(I, float), p).mean(axis=1)


# ----------------------------------------------------------------------------------------- data preparation
def daily_series(df, has_irrigation, replicated_weather):
    """One row per calendar day from the cleaned records (mean of T, H, soil; rain summed, or averaged when several crops
    share the same weather)."""
    d = df.copy()
    d["day"] = d["date"].dt.floor("D")
    g = d.groupby("day")
    out = g[["temperature", "humidity", "soil_moisture"]].mean()
    out["rainfall"] = g["rainfall"].mean() if replicated_weather else g["rainfall"].sum()
    out["irrigation"] = g["target"].max().astype(float) if has_irrigation else 0.0
    return out.reset_index().sort_values("day").reset_index(drop=True)


def _pairs(daily):
    """Indices i where day i+1 is exactly one calendar day after day i."""
    gap = daily["day"].diff().dt.days.to_numpy()
    idx = np.where(gap[1:] == 1)[0]
    return idx                                   # pair (idx, idx+1)


# ----------------------------------------------------------------------------------------- calibration
def calibrate(daily, has_irrigation):
    idx = _pairs(daily)
    if len(idx) < 20:
        raise PdeError("The PDE soil-moisture model needs at least 20 pairs of consecutive daily records; "
                       f"this file has {len(idx)}. Please upload a longer daily series.")
    s = daily["soil_moisture"].to_numpy()
    T, H, R, I = (daily[k].to_numpy() for k in ("temperature", "humidity", "rainfall", "irrigation"))
    th0 = np.repeat(s[idx][:, None], NZ, axis=1)
    target = s[idx + 1]
    use = [0, 1, 2, 3] + ([4] if has_irrigation else [])

    def full(x):
        v = START.copy()
        v[use] = x
        if not has_irrigation:
            v[4] = 0.0
        return dict(zip(NAMES, v))

    def resid(x):
        p = full(x)
        return step(th0, T[idx], H[idx], R[idx], I[idx], p).mean(axis=1) - target

    scale = max(float(np.std(target)), 1e-6)
    sol = least_squares(resid, START[use], bounds=(LOWER[use], UPPER[use]), loss="soft_l1", f_scale=scale, max_nfev=200)
    params = full(sol.x)

    pred = resid(sol.x) + target
    err = pred - target
    rmse = float(np.sqrt(np.mean(err ** 2)))
    persist = float(np.sqrt(np.mean((s[idx] - target) ** 2)))
    d_obs, d_pred = target - s[idx], pred - s[idx]
    ss = float(np.sum((d_obs - d_obs.mean()) ** 2))
    metrics = {"rmse": rmse, "mae": float(np.mean(np.abs(err))), "persistence_rmse": persist,
               "skill_vs_persistence": float(1 - rmse / persist) if persist > 0 else 0.0,
               "r2_change": float(1 - np.sum((d_obs - d_pred) ** 2) / ss) if ss > 0 else 0.0,
               "pairs": int(len(idx))}
    return params, metrics, idx, pred


# ----------------------------------------------------------------------------------------- outputs for the dashboard
def _thin(n, limit=400):
    return np.unique(np.linspace(0, n - 1, min(n, limit)).astype(int))


def simulate(daily, has_irrigation, dry_level, window=60):
    params, metrics, idx, pred = calibrate(daily, has_irrigation)
    days = daily["day"].dt.strftime("%Y-%m-%d").to_numpy()
    s = daily["soil_moisture"].to_numpy()
    T, H, R, I = (daily[k].to_numpy() for k in ("temperature", "humidity", "rainfall", "irrigation"))

    # 1. one-step fit
    keep = _thin(len(idx))
    fit = {"dates": days[idx + 1][keep].tolist(), "observed": np.round(s[idx + 1][keep], 2).tolist(),
           "pde": np.round(pred[keep], 2).tolist(), "persistence": np.round(s[idx][keep], 2).tolist()}

    # 2. distribution over time: profile carried from day to day, mean nudged to the observation each day
    w0 = max(0, len(daily) - window - 1)
    prof = np.repeat(s[w0:w0 + 1, None], NZ, axis=1)
    cols, col_days = [prof[0].copy()], [days[w0]]
    for i in range(w0, len(daily) - 1):
        if (daily["day"].iloc[i + 1] - daily["day"].iloc[i]).days != 1:
            prof = np.repeat(s[i + 1:i + 2, None], NZ, axis=1)
        else:
            prof = step(prof, T[i:i + 1], H[i:i + 1], R[i:i + 1], I[i:i + 1], params)
            prof = np.clip(prof + (s[i + 1] - prof.mean()), 0, 100)                       # keep the shape, match the reading
        cols.append(prof[0].copy())
        col_days.append(days[i + 1])
    heat = {"dates": col_days, "depth_cells": NZ, "values": np.round(np.array(cols), 1).tolist()}

    # 3. forecast: start from the last reading; future weather only from the uploaded data (mean of the last 7 days)
    recent = slice(max(0, len(daily) - 7), len(daily))
    T_f, H_f = float(T[recent].mean()), float(H[recent].mean())
    avg_rain = float(np.mean(R))
    last = daily["day"].iloc[-1]
    f_days = [(last + np.timedelta64(j, "D")).strftime("%Y-%m-%d") for j in range(1, HORIZON + 1)]
    scen = {}
    for name, rain_f in (("No rain", 0.0), ("Average rain", avg_rain)):
        prof = np.repeat(s[-1:, None], NZ, axis=1)
        means, profiles = [], {"0": prof[0].round(1).tolist()}
        for j in range(HORIZON):
            tj, hj, rj = (T[-1], H[-1], R[-1]) if j == 0 else (T_f, H_f, rain_f)
            prof = step(prof, np.array([tj]), np.array([hj]), np.array([rj]), np.array([0.0]), params)
            means.append(float(prof.mean()))
            profiles[str(j + 1)] = prof[0].round(1).tolist()
        cross = next((j + 1 for j, m in enumerate(means) if m <= dry_level), None)
        scen[name] = {"mean": np.round(means, 2).tolist(), "profiles": profiles, "dry_in_days": cross}
    n_ctx = min(len(daily), 30)
    forecast = {"horizon": HORIZON, "dates": f_days, "scenarios": scen, "dry_level": dry_level,
                "context": {"dates": days[-n_ctx:].tolist(), "observed": np.round(s[-n_ctx:], 2).tolist()},
                "assumptions": {"temperature": round(T_f, 1), "humidity": round(H_f, 1), "average_rain_mm": round(avg_rain, 2),
                                "first_day_weather": "the last uploaded day"}}
    return {"params": {k: round(float(v), 5) for k, v in params.items()}, "metrics": metrics, "fit": fit, "heatmap": heat,
            "forecast": forecast, "uses_irrigation": bool(has_irrigation), "nz": NZ, "substeps": SUB, "days_used": int(len(daily))}
