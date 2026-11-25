"""
config.py
=========
One place for every path and constant used by the project.
Keeping them here means we never have "magic numbers" scattered around the code.
"""
import os

# ---------- folders ----------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # smart_irrigation_svm/
DATA_DIR = os.path.join(ROOT, "data")
MODEL_DIR = os.path.join(ROOT, "models")
FIG_DIR = os.path.join(ROOT, "static", "figures")      # figures live in static/ so Flask can show them
REPORT_DIR = os.path.join(ROOT, "reports")

RAW_CSV = os.path.join(DATA_DIR, "irrigation_raw.csv")
CLEAN_CSV = os.path.join(DATA_DIR, "irrigation_clean.csv")
SVM_MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.joblib")
BEST_MODEL_PATH = os.path.join(MODEL_DIR, "best_model.joblib")
METRICS_JSON = os.path.join(REPORT_DIR, "metrics.json")
COMPARISON_CSV = os.path.join(REPORT_DIR, "model_comparison.csv")

# ---------- machine-learning columns ----------
NUMERIC_FEATURES = ["temperature", "humidity", "soil_moisture", "rainfall"]
CATEGORICAL_FEATURES = ["crop_type"]
TARGET = "irrigation_needed"          # 1 = Yes, 0 = No
RANDOM_STATE = 42                     # makes every run reproducible

# Valid physical range of each sensor reading (used to remove impossible values)
VALID_RANGES = {
    "temperature": (0, 55),      # degrees Celsius
    "humidity": (0, 100),        # percent
    "soil_moisture": (0, 100),   # percent
    "rainfall": (0, 300),        # millimetres
}

# Soil-moisture level (%) under which each crop normally needs water, and its relative water demand
CROPS = {
    "Rice":      {"threshold": 55, "water_factor": 1.6},
    "Sugarcane": {"threshold": 50, "water_factor": 1.5},
    "Maize":     {"threshold": 40, "water_factor": 1.0},
    "Cotton":    {"threshold": 38, "water_factor": 1.1},
    "Wheat":     {"threshold": 35, "water_factor": 0.9},
}

# ---------- electrical optimisation (pump) constants ----------
PUMP_POWER_KW = 1.5            # electrical rating of the pump motor
PUMP_FLOW_L_PER_H = 3000.0     # water delivered per hour
LITRES_PER_PCT = 300.0         # litres needed to raise a 100 m2 root-zone by 1 % moisture
LITRES_PER_MM_RAIN = 100.0     # 1 mm of rain on 100 m2 = 100 litres
TIMER_HOURS = 2.0              # a conventional timer system runs the pump 2 h every day
