"""
tests/test_app.py - automated checks for the prediction logic, energy model and Flask app.
Run:  python tests/test_app.py        (after the model has been trained)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import app as webapp                      # noqa: E402
import energy                             # noqa: E402
from predict import predict_irrigation, validate   # noqa: E402


class PredictionTests(unittest.TestCase):
    def test_dry_hot_field_needs_water(self):
        r = predict_irrigation(36, 40, 18, 0, "Rice")
        self.assertTrue(r["irrigation_needed"])
        self.assertEqual(r["pump_status"], "ON")
        self.assertGreater(r["water_litres"], 0)

    def test_wet_field_pump_off_and_full_saving(self):
        r = predict_irrigation(22, 85, 75, 30, "Wheat")
        self.assertFalse(r["irrigation_needed"])
        self.assertEqual(r["pump_status"], "OFF")
        self.assertEqual(r["energy_used_kwh"], 0)
        self.assertEqual(r["energy_saved_kwh"], r["energy_baseline_kwh"])

    def test_validation(self):
        self.assertEqual(validate(30, 50, 40, 0), [])
        self.assertTrue(validate(300, 50, 40, 0))
        self.assertTrue(validate(None, 50, 40, 0))


class EnergyTests(unittest.TestCase):
    def test_energy_never_negative(self):
        for needed in (True, False):
            r = energy.estimate(needed, 40, 5, 0, "Rice")
            self.assertGreaterEqual(r["energy_saved_kwh"], 0)
            self.assertGreaterEqual(r["energy_used_kwh"], 0)

    def test_rain_reduces_water(self):
        dry = energy.estimate(True, 30, 20, 0, "Maize")["water_litres"]
        wet = energy.estimate(True, 30, 20, 20, "Maize")["water_litres"]
        self.assertLessEqual(wet, dry)


class FlaskTests(unittest.TestCase):
    def setUp(self):
        self.c = webapp.app.test_client()

    def test_pages(self):
        for path in ("/", "/results", "/about"):
            self.assertEqual(self.c.get(path).status_code, 200)

    def test_form_prediction(self):
        r = self.c.post("/", data=dict(temperature=36, humidity=40, soil_moisture=18, rainfall=0, crop="Rice"))
        self.assertIn(b"Irrigation Required", r.data)
        self.assertIn(b"Pump ON", r.data)

    def test_form_rejects_bad_input(self):
        r = self.c.post("/", data=dict(temperature=900, humidity=40, soil_moisture=18, rainfall=0, crop="Rice"))
        self.assertIn(b"must be between", r.data)

    def test_api(self):
        r = self.c.post("/api/predict", json=dict(temperature=22, humidity=85, soil_moisture=75, rainfall=30, crop="Wheat"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["pump_status"], "OFF")
        bad = self.c.post("/api/predict", json=dict(temperature="abc", humidity=1, soil_moisture=1, rainfall=1))
        self.assertEqual(bad.status_code, 400)


class UploadAnalyzeTests(unittest.TestCase):
    """Upload a CSV -> choose target -> SVM analysis page with graphs."""

    def setUp(self):
        self.c = webapp.app.test_client()

    def _upload(self, name, content):
        import io
        return self.c.post("/upload", data={"file": (io.BytesIO(content), name)}, content_type="multipart/form-data")

    def test_full_flow_with_sample_data(self):
        r = self.c.post("/upload", data={"use_sample": "1"})
        self.assertEqual(r.status_code, 302)
        configure_url = r.headers["Location"]
        self.assertEqual(self.c.get(configure_url).status_code, 200)
        r = self.c.post(configure_url, data={"target": "irrigation_needed"})
        self.assertIn("/analysis/", r.headers["Location"])
        page = self.c.get(r.headers["Location"])
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"SVM graphs", page.data)
        rid = r.headers["Location"].rsplit("/", 1)[1]
        self.assertEqual(self.c.get(f"/download/model/{rid}").status_code, 200)

    def test_rejects_non_csv(self):
        r = self._upload("notes.txt", b"hello")
        self.assertTrue(r.headers["Location"].endswith("/upload"))

    def test_rejects_tiny_file_and_continuous_target(self):
        r = self._upload("tiny.csv", b"a,b\n1,2\n")
        url = r.headers["Location"]
        r = self.c.post(url, data={"target": "b"})
        self.assertIn("/configure/", r.headers["Location"])          # sent back with an error message
        rows = "x,y\n" + "\n".join(f"{i},{i * 0.37}" for i in range(100))
        url = self._upload("cont.csv", rows.encode()).headers["Location"]
        r = self.c.post(url, data={"target": "y"})
        self.assertIn("/configure/", r.headers["Location"])

    def test_bad_ids_are_404(self):
        self.assertEqual(self.c.get("/analysis/not-a-valid-id").status_code, 404)
        self.assertEqual(self.c.get("/analysis/" + "0" * 32).status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
