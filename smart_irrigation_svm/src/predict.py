"""
predict.py
==========
Loads the saved SVM (Joblib) and turns four sensor readings into a full irrigation decision
(prediction + pump status + electricity used / saved).
"""
import joblib
import pandas as pd

import config
import energy

_model = None          # cache: the model is read from disk only once


def load_model():
    global _model
    if _model is None:
        _model = joblib.load(config.SVM_MODEL_PATH)
    return _model


def validate(temperature, humidity, soil_moisture, rainfall):
    """Return a list of human-readable problems (empty list = input is fine)."""
    values = {"temperature": temperature, "humidity": humidity,
              "soil_moisture": soil_moisture, "rainfall": rainfall}
    problems = []
    for name, value in values.items():
        low, high = config.VALID_RANGES[name]
        if value is None:
            problems.append(f"{name.replace('_', ' ').title()} must be a number.")
        elif not low <= value <= high:
            problems.append(f"{name.replace('_', ' ').title()} must be between {low} and {high}.")
    return problems


def predict_irrigation(temperature, humidity, soil_moisture, rainfall, crop="Maize") -> dict:
    model = load_model()
    row = pd.DataFrame([{"temperature": temperature, "humidity": humidity,
                         "soil_moisture": soil_moisture, "rainfall": rainfall, "crop_type": crop}])
    needed = bool(model.predict(row)[0])
    prob_yes = float(model.predict_proba(row)[0][1])
    result = energy.estimate(needed, temperature, soil_moisture, rainfall, crop)
    result.update({
        "irrigation_needed": needed,
        "prediction": "Irrigation Required" if needed else "Irrigation Not Required",
        "confidence": round(100 * (prob_yes if needed else 1 - prob_yes), 1),
        "crop": crop,
    })
    return result


if __name__ == "__main__":      # quick command-line test
    print(predict_irrigation(36, 40, 18, 0, "Rice"))
    print(predict_irrigation(22, 85, 75, 30, "Wheat"))
