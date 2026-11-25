"""
energy.py
=========
The "Electrical Optimization" part of the project.

A conventional irrigation system switches the pump on for a fixed time every day.
Our system switches the pump on only when the SVM says irrigation is needed, and only for
as long as the crop really needs. The difference in electrical energy is the saving.

Formulas
--------
  water_needed (L)  = moisture_deficit x 300 L/% x crop_factor x heat_factor - rainfall x 100 L/mm
  pump_hours        = water_needed / pump_flow
  energy_used (kWh) = pump_hours x pump_power
  baseline (kWh)    = timer_hours x pump_power            (the fixed daily timer system)
  energy_saved      = baseline - energy_used              (never below 0)
"""
import config


def estimate(irrigation_needed: bool, temperature: float, soil_moisture: float,
             rainfall: float, crop: str = "Maize") -> dict:
    profile = config.CROPS.get(crop, config.CROPS["Maize"])
    baseline_kwh = config.TIMER_HOURS * config.PUMP_POWER_KW
    baseline_litres = config.TIMER_HOURS * config.PUMP_FLOW_L_PER_H

    litres = 0.0
    if irrigation_needed:
        target = profile["threshold"] + 15                    # water up to 15 points above the threshold
        deficit = max(0.0, target - soil_moisture)
        heat_factor = 1.0 + max(0.0, temperature - 30) * 0.02  # hotter -> more evaporation loss
        litres = deficit * config.LITRES_PER_PCT * profile["water_factor"] * heat_factor
        litres -= rainfall * config.LITRES_PER_MM_RAIN
        litres = min(max(litres, 500.0), baseline_litres * 1.5)  # at least a useful cycle, never absurd

    hours = litres / config.PUMP_FLOW_L_PER_H
    used = hours * config.PUMP_POWER_KW
    saved = max(0.0, baseline_kwh - used)
    return {
        "pump_status": "ON" if irrigation_needed else "OFF",
        "water_litres": round(litres, 1),
        "pump_minutes": round(hours * 60, 1),
        "energy_used_kwh": round(used, 3),
        "energy_baseline_kwh": round(baseline_kwh, 3),
        "energy_saved_kwh": round(saved, 3),
        "saving_percent": round(100 * saved / baseline_kwh, 1) if baseline_kwh else 0.0,
    }
