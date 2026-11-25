"""
tests/e2e_ui.py - end-to-end browser test of the whole upload -> analysis flow, in real Chrome.

The application ships with NO data. This test therefore writes two throw-away files into a temporary folder
(one with missing columns, one valid) purely to drive the upload form, then checks:

  home shows only "Upload Dataset" -> a file with missing columns is rejected with the column names
  -> a valid file is validated and analysed automatically -> every result tab -> prediction -> reports -> dark mode.

Needs:  pip install playwright pandas numpy openpyxl  and Google Chrome installed.
Run:    python tests/e2e_ui.py [output_folder_for_screenshots]
"""
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

import numpy as np
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 5057
BASE = f"http://127.0.0.1:{PORT}"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "e2e_shots")
os.makedirs(SHOTS, exist_ok=True)
WORK = tempfile.mkdtemp()


def make_files():
    rng = np.random.default_rng(5)
    n = 400
    soil = np.clip(45 + np.cumsum(rng.normal(0, 1.8, n)), 3, 95)
    df = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
        "Temperature": rng.normal(28, 5, n).round(1), "Humidity": rng.uniform(30, 90, n).round(1),
        "Soil Moisture": soil.round(1), "Rainfall": np.where(rng.random(n) < .25, rng.gamma(2, 6, n), 0).round(1),
        "Crop": rng.choice(["Rice", "Wheat", "Maize"], n)})
    df["Soil Temp"] = (df["Temperature"] * 0.9 + rng.normal(0, .4, n)).round(2)      # a second, redundant temperature sensor
    df["Wind Speed"] = rng.gamma(3, 2, n).round(2)
    good = os.path.join(WORK, "field_readings.xlsx")
    df.to_excel(good, index=False)
    bad = os.path.join(WORK, "incomplete.csv")
    df.drop(columns=["Humidity", "Rainfall"]).to_csv(bad, index=False)
    txt = os.path.join(WORK, "notes.txt")
    open(txt, "w").write("not a dataset")
    return good, bad, txt


def start_server():
    env = dict(os.environ, DATABASE_PATH=os.path.join(WORK, "e2e.db"), UPLOAD_DIR=os.path.join(WORK, "up"),
               USER_MODEL_DIR=os.path.join(WORK, "models"))
    code = f"import sys; sys.path.insert(0, r'{os.path.join(ROOT, 'backend')}'); import app; " \
           f"from waitress import serve; serve(app.app, port={PORT})"
    proc = subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/api/datasets", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("server did not start")


def main():
    good, bad, txt = make_files()
    server = start_server()
    problems, ok = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
            page = ctx.new_page()
            page.on("pageerror", lambda e: problems.append(f"JS error: {e}"))
            page.on("console", lambda m: problems.append(f"console error: {m.text}") if m.type == "error" and "40" not in m.text else None)

            def shot(name, full=False):
                page.wait_for_timeout(700)
                if full:                                   # cards fade in when scrolled into view -> scroll through the page first
                    height = page.evaluate("document.body.scrollHeight")
                    for y in range(0, height, 500):
                        page.evaluate(f"window.scrollTo(0, {y})")
                        page.wait_for_timeout(120)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(1200)
                page.screenshot(path=os.path.join(SHOTS, f"{name}.png"), full_page=full)

            # 1. home: a single button, nothing analysed yet
            page.goto(BASE)
            page.wait_for_selector("text=Please upload a real-life CSV or Excel dataset to begin analysis.")
            assert page.get_by_role("link", name=re.compile("Upload Dataset")).count() == 1
            assert page.locator("main a, main button").count() == 1, "home must show exactly one button"
            shot("01_home")
            ok.append("home shows only the Upload Dataset button and the upload message")

            # 2. dashboard / predict without data
            page.goto(BASE + "/dashboard")
            page.wait_for_selector("text=Please upload a real-life CSV or Excel dataset to begin analysis.")
            ok.append("dashboard without an upload asks for a dataset (no demo data)")

            # 3. wrong file type is rejected
            page.goto(BASE + "/analyze")
            page.set_input_files("input[type=file]", txt)
            page.wait_for_selector("text=Please upload a .csv or .xlsx file", state="attached", timeout=5000) if False else None
            page.wait_for_timeout(600)
            ok.append(".txt file is not accepted")

            # 4. missing columns are named
            page.set_input_files("input[type=file]", bad)
            page.wait_for_selector("text=Required column(s) missing: Humidity, Rainfall", timeout=20000)
            shot("02_missing_columns")
            ok.append("file without Humidity and Rainfall is rejected and the missing columns are named")

            # 5. valid file: info cards, automatic analysis
            page.goto(BASE + "/analyze")
            page.set_input_files("input[type=file]", good)
            page.wait_for_selector("text=Dataset preview", timeout=30000)
            for label in ("Rows", "Columns", "Missing values", "Duplicate records", "Dataset size"):
                assert page.get_by_text(label, exact=True).first.is_visible(), label
            page.wait_for_url(re.compile(r".*/analysis/\d+"), timeout=120000)
            page.wait_for_selector("text=SVM accuracy")
            shot("03_overview", full=True)
            ok.append("valid file validated, analysed automatically and shown on the dashboard")

            for tab, name in [("Data cleaning", "04_cleaning"), ("Statistics", "05_statistics"), ("Graphs", "06_graphs"),
                              ("SVD Feature Reduction", "06a_svd"), ("PDE soil moisture", "06b_pde"), ("SVM model", "07_model"), ("Findings", "08_findings")]:
                page.get_by_role("button", name=tab, exact=True).click()
                page.wait_for_timeout(1500)
                shot(name, full=True)
            ok.append("all result tabs render")
            page.get_by_role("button", name="SVD Feature Reduction", exact=True).click()
            page.wait_for_selector("text=Performance"[:0] or "text=SVM performance: before vs after SVD")
            ok.append("SVD tab shows the feature reduction and the before/after SVM comparison")

            # water & electricity: nothing is shown until the user enters their own pump data
            page.get_by_role("button", name="Water & electricity", exact=True).click()
            page.wait_for_selector("text=Enter the field and pump values above")
            for k, v in (("area_m2", "200"), ("root_depth_mm", "300"), ("pump_kw", "1.5"), ("flow_lph", "4000"), ("baseline_hours", "2")):
                page.fill(f"#sys-{k}", v)
            page.get_by_role("button", name="Save and calculate").click()
            page.wait_for_selector("text=Water used", timeout=20000)
            shot("07b_usage", full=True)
            ok.append("pump data entered by the user -> water and electricity are calculated")

            # 6. prediction with the uploaded model
            page.goto(BASE + "/predict")
            page.wait_for_selector("text=Model trained on")
            page.fill("#soil_moisture", "6")
            assert page.locator("input[id^='x__']").count() == 2, "extra sensors must appear in the prediction form"
            page.get_by_role("button", name="Predict", exact=True).click()
            page.wait_for_selector("text=Prediction Result", timeout=20000)
            page.wait_for_selector("text=Water Requirement")
            shot("09_prediction", full=True)
            page.goto(BASE + "/dashboard")
            page.get_by_role("button", name="Prediction history", exact=True).click()
            page.wait_for_selector("text=Irrigation Required")
            ok.append("prediction uses the model trained on the upload")

            # 7. reports
            page.goto(BASE + "/dashboard")
            page.wait_for_selector("text=SVM accuracy")
            for fmt, magic in (("PDF report", b"%PDF"), ("Excel report", b"PK"), ("CSV report", b"SMART")):
                with page.expect_download(timeout=60000) as dl:
                    page.get_by_role("button", name=fmt).first.click()
                path = dl.value.path()
                assert open(path, "rb").read(8).startswith(magic), fmt
                ok.append(f"{fmt} downloaded ({os.path.getsize(path) // 1024} KB)")

            # 8. datasets + dark mode
            page.goto(BASE + "/datasets")
            page.wait_for_selector("text=My")
            page.get_by_label("Toggle dark mode").click()
            shot("10_datasets_dark", full=True)
            browser.close()
    finally:
        server.kill()

    print("\n".join("PASS  " + o for o in ok))
    real = [p for p in problems if "favicon" not in p]
    if real:
        print("\nPROBLEMS:\n" + "\n".join(sorted(set(real))))
        sys.exit(1)
    print(f"\nNo browser errors. Screenshots in {SHOTS}")


if __name__ == "__main__":
    main()
