"""
Automated API tests.   Run:  python backend/test_api.py

The application itself contains NO data. These tests build small throw-away CSV files in a temporary folder
(that is the only way to test an upload feature) and use a temporary database, so nothing real is touched.
"""
import io
import os
import sys
import tempfile
import time
import unittest

import numpy as np
import pandas as pd

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = os.path.join(_tmp, "test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["USER_MODEL_DIR"] = os.path.join(_tmp, "models")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module  # noqa: E402


def make_frame(n=300, label=True, seed=3):
    rng = np.random.default_rng(seed)
    soil = np.clip(45 + np.cumsum(rng.normal(0, 1.8, n)), 3, 95)
    df = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
        "Temp": rng.normal(28, 5, n).round(1),
        "Humidity": rng.uniform(30, 90, n).round(1),
        "Soil_Moisture": soil.round(1),
        "Rainfall": np.where(rng.random(n) < .25, rng.gamma(2, 6, n), 0).round(1),
    })
    if label:
        df["Irrigation_Needed"] = np.where(df["Soil_Moisture"] < 35, "Yes", "No")
    return df


def csv_bytes(df):
    return df.to_csv(index=False).encode()


class UploadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = app_module.app.test_client()

    def upload(self, data, name="data.csv"):
        return self.c.post("/api/datasets", data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data")

    def wait_done(self, ds_id):
        for _ in range(240):
            st = self.c.get(f"/api/datasets/{ds_id}/status").get_json()
            if st["status"] in ("done", "error"):
                return st
            time.sleep(0.5)
        self.fail("analysis did not finish")

    def test_01_nothing_exists_before_upload(self):
        r = self.c.get("/api/datasets").get_json()
        self.assertEqual(r["datasets"], [])
        self.assertIn("Please upload a real-life CSV or Excel dataset", r["message"])
        self.assertEqual(self.c.get("/api/datasets/1/model").status_code, 404)        # no default model
        self.assertEqual(self.c.post("/api/datasets/1/predict", json={}).status_code, 404)
        for gone in ("/api/predict", "/api/meta", "/api/dashboard", "/api/model/metrics"):
            self.assertEqual(self.c.get(gone).status_code, 404, gone)                   # demo-era endpoints are removed

    def test_02_rejects_other_file_types_and_bad_files(self):
        self.assertEqual(self.upload(b"hello", "notes.txt").status_code, 400)
        self.assertEqual(self.upload(b"", "empty.csv").status_code, 400)
        bad = self.upload(b"\x00\x01\x02garbage\xff" * 20, "broken.xlsx")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("corrupted", bad.get_json()["error"])
        few = self.upload(csv_bytes(make_frame(10)), "few.csv")
        self.assertEqual(few.status_code, 400)
        self.assertEqual(self.c.get("/api/datasets").get_json()["datasets"], [])        # nothing was stored

    def test_03_missing_required_columns_are_named(self):
        df = make_frame().drop(columns=["Humidity", "Rainfall"])
        r = self.upload(csv_bytes(df))
        d = r.get_json()
        self.assertEqual(r.status_code, 201)
        self.assertFalse(d["valid"])
        self.assertEqual(d["missing_required"], ["Humidity", "Rainfall"])
        a = self.c.post(f"/api/datasets/{d['id']}/analyze", json={})
        self.assertEqual(a.status_code, 422)
        self.assertIn("Humidity, Rainfall", a.get_json()["error"])

    def test_04_full_flow_with_label_column(self):
        df = make_frame()
        df.loc[5, "Temp"] = np.nan
        df.loc[9, "Soil_Moisture"] = np.nan
        df = pd.concat([df, df.iloc[[20, 21]]])                                          # 2 exact duplicates
        r = self.upload(csv_bytes(df)).get_json()
        self.assertTrue(r["valid"])
        info = r["info"]
        self.assertEqual((info["rows"], info["columns"], info["duplicates"]), (302, 6, 2))
        self.assertEqual(info["missing_cells"], 2)
        ds = r["id"]
        self.assertEqual(self.c.post(f"/api/datasets/{ds}/analyze", json={}).status_code, 202)
        self.assertEqual(self.wait_done(ds)["status"], "done")
        res = self.c.get(f"/api/datasets/{ds}").get_json()["results"]
        self.assertEqual(res["cleaning"]["rows_after"], 298)                             # 302 - 2 dup - 2 rows with a gap
        self.assertFalse(res["target_derived"])
        for k in ("mean", "median", "mode", "std", "min", "max"):
            self.assertIn(k, res["stats"]["soil_moisture"])
        self.assertAlmostEqual(res["stats"]["soil_moisture"]["min"], df["Soil_Moisture"].min())
        ch = res["charts"]
        for k in ("timeseries", "histograms", "boxplots", "scatter"):
            self.assertIn(k, ch)
        self.assertEqual(len(ch["timeseries"]["labels"]), 298)
        self.assertEqual(set(res["model"]["metrics"]), {"accuracy", "precision", "recall", "f1", "roc_auc"})
        self.assertGreater(res["model"]["metrics"]["accuracy"], 0.9)
        self.assertNotIn("monthly", res)
        self.assertNotIn("usage_totals", res)

        mdl = self.c.get(f"/api/datasets/{ds}/model").get_json()
        self.assertEqual(mdl["features"], ["temperature", "humidity", "soil_moisture", "rainfall"])
        p = self.c.post(f"/api/datasets/{ds}/predict", json={"temperature": 30, "humidity": 50, "soil_moisture": 8, "rainfall": 0})
        self.assertEqual(p.status_code, 201)
        self.assertTrue(p.get_json()["irrigation_required"])
        p2 = self.c.post(f"/api/datasets/{ds}/predict", json={"temperature": 30, "humidity": 50, "soil_moisture": 80, "rainfall": 5})
        self.assertFalse(p2.get_json()["irrigation_required"])
        self.assertEqual(self.c.post(f"/api/datasets/{ds}/predict", json={"temperature": "x"}).status_code, 400)
        self.assertEqual(len(self.c.get(f"/api/datasets/{ds}/predictions").get_json()["predictions"]), 2)

        for fmt, magic in (("pdf", b"%PDF"), ("xlsx", b"PK"), ("csv", b"SMART")):
            rep = self.c.get(f"/api/datasets/{ds}/report/{fmt}")
            self.assertEqual(rep.status_code, 200, fmt)
            self.assertTrue(rep.data.startswith(magic), fmt)
        self.assertNotIn(b"electricity", self.c.get(f"/api/datasets/{ds}/report/csv").data.lower())

        self.assertEqual(self.c.delete(f"/api/datasets/{ds}").status_code, 200)
        self.assertEqual(self.c.get(f"/api/datasets/{ds}").status_code, 404)

    def test_05_no_label_column_derives_label_from_the_upload(self):
        r = self.upload(csv_bytes(make_frame(label=False), ), "nolabel.csv").get_json()
        ds = r["id"]
        self.c.post(f"/api/datasets/{ds}/analyze", json={})
        self.assertEqual(self.wait_done(ds)["status"], "done")
        res = self.c.get(f"/api/datasets/{ds}").get_json()["results"]
        self.assertTrue(res["target_derived"])
        self.assertIn("DERIVED from your own data", res["target_note"])
        self.assertEqual(res["cleaning"]["rows_after"], 299)                             # last record has no "next" reading

    def test_06_excel_upload(self):
        buf = io.BytesIO()
        make_frame().to_excel(buf, index=False)
        r = self.upload(buf.getvalue(), "farm.xlsx")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.get_json()["valid"])

    def test_07_too_many_missing_values_is_an_error(self):
        df = make_frame()
        df.loc[:200, "Humidity"] = np.nan
        ds = self.upload(csv_bytes(df)).get_json()["id"]
        self.c.post(f"/api/datasets/{ds}/analyze", json={})
        st = self.wait_done(ds)
        self.assertEqual(st["status"], "error")
        self.assertIn("Too many missing values", st["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
