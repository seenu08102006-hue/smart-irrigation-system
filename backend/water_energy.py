"""
water_energy.py - water requirement and electricity consumption of the irrigation pump.

A dataset of weather and soil readings cannot contain the size of your field or the specifications of your pump, so these are
entered by the user (nothing is assumed). Together with the SVM decision and the PDE moisture deficit they give:

    water depth (mm)  = moisture deficit (% points) / 100 * root-zone depth (mm)
    water (litres)    = water depth (mm) * field area (m2)               (1 mm over 1 m2 = 1 litre)
    pump time (h)     = litres / pump flow (L/h)
    electricity (kWh) = pump time (h) * pump power (kW)

The moisture deficit is the gap between the upper operating level (75th percentile of the uploaded soil moisture) and the
PDE's expectation for the next day, on the days the SVM switches the pump ON.
"""

REQUIRED = {"area_m2": "Field area (m2)", "root_depth_mm": "Root-zone depth (mm)", "pump_kw": "Pump power (kW)", "flow_lph": "Pump flow (L/h)"}
OPTIONAL = {"baseline_hours": "Current pump hours per day (optional, for the saving)", "tariff": "Electricity price per kWh (optional)"}


def parse(data):
    """Validate the user's system parameters. Returns a clean dict or raises ValueError with a readable message."""
    out = {}
    for key, label in REQUIRED.items():
        try:
            v = float(data.get(key))
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a number.")
        if not v > 0 or v > 1e9:
            raise ValueError(f"{label} must be greater than zero.")
        out[key] = v
    for key, label in OPTIONAL.items():
        raw = data.get(key)
        if raw in (None, ""):
            out[key] = None
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a number or left empty.")
        if v < 0 or v > 1e9:
            raise ValueError(f"{label} must not be negative.")
        out[key] = v
    if out["baseline_hours"] is not None and out["baseline_hours"] > 24:
        raise ValueError("Pump hours per day cannot exceed 24.")
    return out


def requirement(deficit_pct, params):
    """Water and electricity needed to close a moisture deficit (percentage points)."""
    mm = max(0.0, deficit_pct) / 100.0 * params["root_depth_mm"]
    litres = mm * params["area_m2"]
    hours = litres / params["flow_lph"]
    return {"water_mm": mm, "water_litres": litres, "pump_hours": hours, "electricity_kwh": hours * params["pump_kw"]}


def usage(plan, params):
    """Totals and monthly sums over the uploaded period, using the SVM's daily ON/OFF plan."""
    months, tot = {}, {"water": 0.0, "kwh": 0.0, "hours": 0.0, "on_days": 0}
    base_kwh = base_l = 0.0
    for day, need, deficit in zip(plan["dates"], plan["need"], plan["deficit_pct"]):
        m = months.setdefault(day[:7], {"water": 0.0, "kwh": 0.0, "base_water": 0.0, "base_kwh": 0.0, "days": 0})
        m["days"] += 1
        if params["baseline_hours"] is not None:
            m["base_water"] += params["baseline_hours"] * params["flow_lph"]
            m["base_kwh"] += params["baseline_hours"] * params["pump_kw"]
        if need:
            r = requirement(deficit, params)
            m["water"] += r["water_litres"]
            m["kwh"] += r["electricity_kwh"]
            tot["water"] += r["water_litres"]
            tot["kwh"] += r["electricity_kwh"]
            tot["hours"] += r["pump_hours"]
            tot["on_days"] += 1
    days = len(plan["dates"])
    labels = sorted(months)
    out = {"days": days, "pump_on_days": tot["on_days"], "pump_on_percent": round(100 * tot["on_days"] / max(days, 1), 1),
           "water_litres": round(tot["water"]), "electricity_kwh": round(tot["kwh"], 2), "pump_hours": round(tot["hours"], 1),
           "cost": round(tot["kwh"] * params["tariff"], 2) if params["tariff"] is not None else None,
           "monthly": {"labels": labels, "water": [round(months[k]["water"]) for k in labels],
                       "electricity": [round(months[k]["kwh"], 2) for k in labels]},
           "baseline": None}
    if params["baseline_hours"] is not None:
        bk = sum(m["base_kwh"] for m in months.values())
        bw = sum(m["base_water"] for m in months.values())
        out["baseline"] = {"hours_per_day": params["baseline_hours"], "electricity_kwh": round(bk, 2), "water_litres": round(bw),
                           "saved_kwh": round(bk - tot["kwh"], 2), "saved_litres": round(bw - tot["water"]),
                           "saved_percent": round(100 * (bk - tot["kwh"]) / bk, 1) if bk > 0 else None,
                           "monthly_baseline_electricity": [round(months[k]["base_kwh"], 2) for k in labels],
                           "monthly_baseline_water": [round(months[k]["base_water"]) for k in labels]}
    return out
