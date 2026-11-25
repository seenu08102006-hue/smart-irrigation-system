"""
Smart Irrigation Data Analysis System - Flask backend.

The app analyses ONLY the dataset the user uploads. There is no sample data, no built-in model and no simulated values:
every statistic, graph, SVM metric and prediction comes from the uploaded file.

Run (development):  python backend/app.py
"""
import json
import os
import threading
import traceback
import uuid

from flask import (Flask, Response, jsonify, render_template, request,
                   send_from_directory)
from flask_cors import CORS

import config
import database
import dataset_service
import reports
import water_energy

app = Flask(__name__, static_folder=config.STATIC_DIR, static_url_path="/static",
            template_folder=config.TEMPLATE_DIR)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024   # bigger uploads are rejected (HTTP 413)
CORS(app, resources={r"/api/*": {"origins": "*"}})

NO_DATA_MESSAGE = "Please upload a real-life CSV or Excel dataset to begin analysis."
PROGRESS = {}                    # dataset id -> live progress of the running analysis
PROGRESS_LOCK = threading.Lock()


def err(message, code=400, **extra):
    return jsonify(error=message, **extra), code


def load_dataset(ds_id):
    row = database.query("SELECT * FROM datasets WHERE id = ?", (ds_id,), one=True)
    if row:
        row["mapping"] = json.loads(row["mapping"]) if row["mapping"] else None
        row["results"] = json.loads(row["results"]) if row["results"] else None
        row["system_params"] = json.loads(row["system_params"]) if row.get("system_params") else None
    return row


def get_done_dataset(ds_id):
    ds = load_dataset(ds_id)
    return ds if ds and ds["status"] == "done" and ds["results"] and ds["model_file"] else None


# ------------------------------------------------------------------ upload + validation
@app.post("/api/datasets")
def upload_dataset():
    """Step 1: receive a .csv/.xlsx file, validate it and return file information + preview."""
    f = request.files.get("file")
    if not f or not f.filename:
        return err("Please choose a CSV or Excel file.")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        return err("Only .csv and .xlsx files are supported. Other file types are rejected.")
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.UPLOAD_DIR, stored)
    f.save(path)
    try:
        df = dataset_service.read_table(path)
        info = dataset_service.file_info(df, os.path.getsize(path), f.filename)
        mapping = dataset_service.detect_mapping(df)
    except dataset_service.DatasetError as exc:
        os.remove(path)
        return err(str(exc))
    missing = dataset_service.missing_required(mapping)
    ds_id = database.execute(
        "INSERT INTO datasets (name, stored_name, size_bytes, n_rows, n_cols, mapping) VALUES (?,?,?,?,?,?)",
        (f.filename, stored, info["size_bytes"], info["rows"], info["columns"], json.dumps(mapping)))
    return jsonify(id=ds_id, info=dataset_service.jsonable(info), mapping=mapping, columns=list(df.columns),
                   missing_required=missing,
                   valid=not missing), 201


def _analysis_worker(ds_id, path, mapping, threshold):
    model_file = f"{ds_id}.joblib"
    os.makedirs(config.USER_MODEL_DIR, exist_ok=True)

    def progress(percent, step, steps):
        with PROGRESS_LOCK:
            cur = PROGRESS.get(ds_id, {})
            PROGRESS[ds_id] = {"percent": percent if percent is not None else cur.get("percent", 0),
                               "step": step, "steps": [dict(s) for s in steps]}

    try:
        results = dataset_service.run_analysis(path, mapping, threshold,
                                               os.path.join(config.USER_MODEL_DIR, model_file), progress)
        database.execute("UPDATE datasets SET status='done', error=NULL, results=?, model_file=?, mapping=? WHERE id=?",
                         (json.dumps(results), model_file, json.dumps(results["mapping"]), ds_id))
    except dataset_service.DatasetError as exc:
        database.execute("UPDATE datasets SET status='error', error=? WHERE id=?", (str(exc), ds_id))
    except Exception as exc:                                    # never leave a dataset stuck in "analyzing"
        traceback.print_exc()
        database.execute("UPDATE datasets SET status='error', error=? WHERE id=?",
                         (f"Unexpected problem while analysing the file: {exc}", ds_id))
    finally:
        with PROGRESS_LOCK:
            PROGRESS.pop(ds_id, None)


@app.post("/api/datasets/<int:ds_id>/analyze")
def analyze_dataset(ds_id):
    """Step 2: validate the columns, then run the analysis in a background thread (poll /status)."""
    ds = load_dataset(ds_id)
    if not ds:
        return err("Dataset not found.", 404)
    if ds["status"] == "analyzing":
        return err("Analysis is already running.", 409)
    body = request.get_json(silent=True) or {}
    mapping = body.get("mapping") or ds["mapping"]
    missing = dataset_service.missing_required(mapping)
    if missing:                                                 # refuse before any analysis starts
        msg = ("Required column(s) missing: " + ", ".join(missing) +
               ". The dataset must contain Date, Temperature, Humidity, Soil Moisture and Rainfall.")
        database.execute("UPDATE datasets SET status='error', error=? WHERE id=?", (msg, ds_id))
        return err(msg, 422, missing_required=missing)
    threshold = body.get("derive_threshold")
    try:
        threshold = float(threshold) if threshold not in (None, "") else None
    except (TypeError, ValueError):
        return err("derive_threshold must be a number.")
    database.execute("UPDATE datasets SET status='analyzing', error=NULL, mapping=? WHERE id=?",
                     (json.dumps(mapping), ds_id))
    with PROGRESS_LOCK:
        PROGRESS[ds_id] = {"percent": 1, "step": "Starting", "steps": []}
    threading.Thread(target=_analysis_worker, daemon=True,
                     args=(ds_id, os.path.join(config.UPLOAD_DIR, ds["stored_name"]), mapping, threshold)).start()
    return jsonify(status="analyzing"), 202


@app.get("/api/datasets/<int:ds_id>/status")
def dataset_status(ds_id):
    ds = database.query("SELECT status, error FROM datasets WHERE id = ?", (ds_id,), one=True)
    if not ds:
        return err("Dataset not found.", 404)
    with PROGRESS_LOCK:
        live = PROGRESS.get(ds_id)
    if ds["status"] == "analyzing" and live:
        return jsonify(status="analyzing", **live)
    return jsonify(status=ds["status"], error=ds["error"], percent=100 if ds["status"] == "done" else 0, steps=[])


@app.get("/api/datasets/<int:ds_id>")
def get_dataset(ds_id):
    ds = load_dataset(ds_id)
    if not ds:
        return err("Dataset not found.", 404)
    ds.pop("stored_name", None)
    return jsonify(ds)


@app.get("/api/datasets")
def list_datasets():
    rows = database.query("SELECT id, name, uploaded_at, size_bytes, n_rows, n_cols, status, error, results "
                          "FROM datasets ORDER BY id DESC")
    for r in rows:
        res = json.loads(r.pop("results")) if r["results"] else None
        r["accuracy"] = res["model"]["metrics"]["accuracy"] if res else None
        r["f1"] = res["model"]["metrics"]["f1"] if res else None
        r["predictions"] = database.query("SELECT COUNT(*) AS n FROM predictions WHERE dataset_id = ?",
                                          (r["id"],), one=True)["n"]
    return jsonify(datasets=rows, message=None if rows else NO_DATA_MESSAGE)


@app.delete("/api/datasets/<int:ds_id>")
def delete_dataset(ds_id):
    ds = load_dataset(ds_id)
    if not ds:
        return err("Dataset not found.", 404)
    for path in (os.path.join(config.UPLOAD_DIR, ds["stored_name"]),
                 os.path.join(config.USER_MODEL_DIR, ds["model_file"] or "")):
        if os.path.isfile(path):
            os.remove(path)
    database.execute("DELETE FROM predictions WHERE dataset_id = ?", (ds_id,))
    database.execute("DELETE FROM datasets WHERE id = ?", (ds_id,))
    return jsonify(message="Deleted")


# ------------------------------------------------------------------ prediction (model trained on the upload)
LABELS = {"temperature": "Temperature", "humidity": "Humidity", "soil_moisture": "Soil moisture", "rainfall": "Rainfall"}


@app.get("/api/datasets/<int:ds_id>/model")
def model_info(ds_id):
    """What the prediction form needs: the model's features, crops and the value ranges seen in the uploaded data."""
    ds = get_done_dataset(ds_id)
    if not ds:
        return err(NO_DATA_MESSAGE, 404)
    r = ds["results"]
    return jsonify(dataset={"id": ds["id"], "name": ds["name"]}, crops=r["crops"], features=r["features"],
                   observed=r["ranges"], metrics=r["model"]["metrics"], labels=r["labels"], units=r["units"],
                   system_params=ds["system_params"], extras=r.get("extras", {}))


@app.post("/api/datasets/<int:ds_id>/predict")
def predict(ds_id):
    ds = get_done_dataset(ds_id)
    if not ds:
        return err(NO_DATA_MESSAGE, 404)
    r = ds["results"]
    data = request.get_json(silent=True) or {}
    values = {}
    for key in r["features"]:
        try:
            val = float(data.get(key))
        except (TypeError, ValueError):
            return err(f"{LABELS[key]} must be a number.")
        if not (-100 <= val <= 10000) or val != val:
            return err(f"{LABELS[key]} is not a sensible value.")
        values[key] = val
    crop = data.get("crop_type")
    if r["crops"] and crop not in r["crops"]:
        return err("Please choose one of the crops that appear in your dataset.")
    extras = {}
    given = data.get("extras") or {}
    for key, info in r.get("extras", {}).items():              # other numeric sensors found in the dataset (optional in the form)
        if given.get(key) in (None, ""):
            continue
        try:
            extras[key] = float(given[key])
        except (TypeError, ValueError):
            return err(f"{info['label']} must be a number.")
    res = dataset_service.predict_with_model(os.path.join(config.USER_MODEL_DIR, ds["model_file"]),
                                             values["temperature"], values["humidity"], values["soil_moisture"],
                                             values["rainfall"], crop, extras)
    need = None                                                  # water / electricity only with the user's own pump data
    if ds["system_params"]:
        need = water_energy.requirement(res["deficit_pct"], ds["system_params"])
        res.update({k: round(v, 2) for k, v in need.items()})
    pid = database.execute(
        """INSERT INTO predictions (dataset_id, temperature, humidity, soil_moisture, rainfall, crop_type, prediction,
                                    irrigation_required, pump_status, confidence, pde_next, water_litres, electricity_kwh)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ds_id, values["temperature"], values["humidity"], values["soil_moisture"], values["rainfall"],
         crop or "", res["prediction"], int(res["irrigation_required"]), res["pump_status"], res["confidence"],
         res["pde_next_moisture"], need["water_litres"] if need else None, need["electricity_kwh"] if need else None))
    row = database.query("SELECT created_at FROM predictions WHERE id = ?", (pid,), one=True)
    return jsonify(id=pid, created_at=row["created_at"], inputs=values, crop_type=crop, model_name=ds["name"],
                   has_system_params=bool(ds["system_params"]), **res), 201


@app.get("/api/datasets/<int:ds_id>/predictions")
def list_predictions(ds_id):
    rows = database.query("SELECT * FROM predictions WHERE dataset_id = ? ORDER BY id DESC LIMIT 200", (ds_id,))
    return jsonify(predictions=rows)


# ------------------------------------------------------------------ SVD feature reduction
@app.get("/api/datasets/<int:ds_id>/svd")
def get_svd(ds_id):
    """The SVD analysis of the uploaded dataset: singular values, explained variance, loadings and the SVM comparison."""
    ds = get_done_dataset(ds_id)
    if not ds:
        return err(NO_DATA_MESSAGE, 404)
    return jsonify(dataset={"id": ds["id"], "name": ds["name"]}, svd=ds["results"]["svd"])


# ------------------------------------------------------------------ pump / field parameters, water and electricity
@app.post("/api/datasets/<int:ds_id>/system")
def save_system(ds_id):
    """The user's own field and pump data (needed for litres and kWh; a weather dataset cannot contain them)."""
    ds = get_done_dataset(ds_id)
    if not ds:
        return err(NO_DATA_MESSAGE, 404)
    try:
        params = water_energy.parse(request.get_json(silent=True) or {})
    except ValueError as exc:
        return err(str(exc))
    database.execute("UPDATE datasets SET system_params=? WHERE id=?", (json.dumps(params), ds_id))
    return jsonify(params=params, usage=water_energy.usage(ds["results"]["daily_plan"], params))


@app.get("/api/datasets/<int:ds_id>/usage")
def get_usage(ds_id):
    ds = get_done_dataset(ds_id)
    if not ds:
        return err(NO_DATA_MESSAGE, 404)
    params = ds["system_params"]
    return jsonify(params=params, usage=water_energy.usage(ds["results"]["daily_plan"], params) if params else None,
                   levels=ds["results"]["levels"], fields={**water_energy.REQUIRED, **water_energy.OPTIONAL})


# ------------------------------------------------------------------ reports
REPORTS = {
    "pdf": ("application/pdf", "pdf", reports.build_pdf),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx", reports.build_xlsx),
    "csv": ("text/csv", "csv", reports.build_csv),
}


@app.get("/api/datasets/<int:ds_id>/report/<fmt>")
def dataset_report(ds_id, fmt):
    if fmt not in REPORTS:
        return err("Unknown report format.", 404)
    ds = get_done_dataset(ds_id)
    if not ds:
        return err("Analysis for this dataset is not finished yet.", 409)
    preds = database.query("SELECT * FROM predictions WHERE dataset_id = ? ORDER BY id DESC LIMIT 200", (ds_id,))
    mime, ext, build = REPORTS[fmt]
    stem = os.path.splitext(ds["name"])[0].replace(" ", "_")[:40]
    res = dict(ds["results"])
    res["usage"] = water_energy.usage(res["daily_plan"], ds["system_params"]) if ds["system_params"] else None
    res["system_params"] = ds["system_params"]
    return Response(build(res, preds), mimetype=mime,
                    headers={"Content-Disposition": f"attachment; filename=irrigation_report_{stem}.{ext}"})


@app.errorhandler(413)
def too_large(e):
    return err(f"File too large. The limit is {config.MAX_UPLOAD_MB} MB.", 413)


# -------------------------------------------------- serve the React frontend
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return err("Endpoint not found.", 404)
    return serve_spa(request.path.lstrip("/"))


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    """Serve the built React app (backend/static). Falls back to a help page."""
    if path.startswith("api/"):
        return err("Endpoint not found.", 404)
    index = os.path.join(config.STATIC_DIR, "index.html")
    if not os.path.exists(index):
        return render_template("index.html"), 200
    full = os.path.join(config.STATIC_DIR, path)
    if path and os.path.isfile(full):
        return send_from_directory(config.STATIC_DIR, path)
    return send_from_directory(config.STATIC_DIR, "index.html")


database.init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
