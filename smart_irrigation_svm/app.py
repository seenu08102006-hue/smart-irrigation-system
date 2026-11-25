"""
app.py - Flask web application for Smart Irrigation using SVM
Run:  python app.py      then open  http://127.0.0.1:5000
"""
import json
import os
import re
import shutil
import sys
import uuid

import pandas as pd
from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   send_file, url_for)

# let Python find the files inside src/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
import config                                   # noqa: E402
from predict import predict_irrigation, validate   # noqa: E402
import analyzer                                     # noqa: E402

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")   # needed for flash() messages
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024                              # reject uploads over 10 MB

WORKSPACE = os.path.join(config.ROOT, "workspace")              # uploaded data + trained models, one folder per upload
GENERATED = os.path.join(config.ROOT, "static", "generated")    # graphs drawn for an upload
RID_RE = re.compile(r"^[0-9a-f]{32}$")                           # upload ids are random hex (blocks path tricks)


def run_folder(rid):
    if not RID_RE.match(rid):
        abort(404)
    folder = os.path.join(WORKSPACE, rid)
    if not os.path.isdir(folder):
        abort(404)
    return folder


def read_float(name):
    """Read a form/JSON field as float; return None when it is empty or not a number."""
    value = request.values.get(name) if not request.is_json else (request.get_json(silent=True) or {}).get(name)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@app.route("/", methods=["GET", "POST"])
def home():
    """Home page: shows the form (GET) and the prediction (POST)."""
    result, errors = None, []
    form = {"temperature": "", "humidity": "", "soil_moisture": "", "rainfall": "", "crop": "Maize"}
    if request.method == "POST":
        t, h, s, r = (read_float(k) for k in ("temperature", "humidity", "soil_moisture", "rainfall"))
        crop = request.form.get("crop", "Maize")
        form = {"temperature": request.form.get("temperature", ""), "humidity": request.form.get("humidity", ""),
                "soil_moisture": request.form.get("soil_moisture", ""), "rainfall": request.form.get("rainfall", ""),
                "crop": crop}
        errors = validate(t, h, s, r)
        if crop not in config.CROPS:
            errors.append("Please choose a valid crop.")
        if not errors:
            result = predict_irrigation(t, h, s, r, crop)
    return render_template("index.html", result=result, errors=errors, form=form, crops=list(config.CROPS))


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """JSON API: POST {temperature, humidity, soil_moisture, rainfall, crop}."""
    data = request.get_json(silent=True) or {}
    t, h, s, r = (read_float(k) for k in ("temperature", "humidity", "soil_moisture", "rainfall"))
    crop = data.get("crop", "Maize")
    errors = validate(t, h, s, r)
    if crop not in config.CROPS:
        errors.append("Unknown crop.")
    if errors:
        return jsonify(errors=errors), 400
    return jsonify(predict_irrigation(t, h, s, r, crop))


@app.route("/results")
def results():
    """Model comparison page (reads the metrics saved by train_models.py)."""
    with open(config.METRICS_JSON) as f:
        metrics = json.load(f)
    return render_template("results.html", metrics=metrics)


# ---------------------------------------------------------------- upload & analyse any dataset
@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Step 1: upload a CSV (or use the built-in sample irrigation data)."""
    if request.method == "POST":
        rid = uuid.uuid4().hex
        folder = os.path.join(WORKSPACE, rid)
        os.makedirs(folder)
        target_csv = os.path.join(folder, "data.csv")
        if request.form.get("use_sample"):
            shutil.copy(config.CLEAN_CSV, target_csv)
        else:
            f = request.files.get("file")
            if not f or not f.filename:
                shutil.rmtree(folder)
                flash("Please choose a CSV file first.", "danger")
                return redirect(url_for("upload"))
            if not f.filename.lower().endswith(".csv"):
                shutil.rmtree(folder)
                flash("Only .csv files are supported (in Excel use Save As -> CSV).", "danger")
                return redirect(url_for("upload"))
            f.save(target_csv)
        try:
            pd.read_csv(target_csv, nrows=5)
        except Exception:
            shutil.rmtree(folder)
            flash("That file could not be read as a CSV table.", "danger")
            return redirect(url_for("upload"))
        return redirect(url_for("configure", rid=rid))
    return render_template("upload.html")


@app.route("/configure/<rid>", methods=["GET", "POST"])
def configure(rid):
    """Step 2: look at the data and choose the column the SVM must predict."""
    folder = run_folder(rid)
    df = pd.read_csv(os.path.join(folder, "data.csv"))
    if request.method == "POST":
        target = request.form.get("target", "")
        try:
            result = analyzer.analyze_csv(os.path.join(folder, "data.csv"), target,
                                          os.path.join(GENERATED, rid), os.path.join(folder, "model.joblib"))
        except analyzer.AnalysisError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("configure", rid=rid))
        with open(os.path.join(folder, "results.json"), "w") as fh:
            json.dump(result, fh)
        return redirect(url_for("analysis", rid=rid))
    return render_template("configure.html", rid=rid, shape=df.shape, columns=analyzer.profile_columns(df),
                           preview=df.head(8).to_html(classes="table table-sm table-striped small", index=False, border=0),
                           guess=analyzer.guess_target(df))


@app.route("/analysis/<rid>")
def analysis(rid):
    """Step 3: show EDA + SVM graphs for the uploaded data."""
    folder = run_folder(rid)
    path = os.path.join(folder, "results.json")
    if not os.path.exists(path):
        return redirect(url_for("configure", rid=rid))
    with open(path) as fh:
        result = json.load(fh)
    return render_template("analysis.html", rid=rid, r=result)


@app.route("/download/model/<rid>")
def download_model(rid):
    folder = run_folder(rid)
    return send_file(os.path.join(folder, "model.joblib"), as_attachment=True, download_name="svm_model_uploaded_data.joblib")


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)
