"""
make_screenshot.py - renders the real Flask result page and captures it with headless Chrome/Edge
(for the slides). Needs Chrome or Edge installed and internet access for the Bootstrap CDN.
Run:  python docs/make_screenshot.py
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
import app as webapp  # noqa: E402
import config  # noqa: E402

BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "/usr/bin/google-chrome", "/usr/bin/chromium"]

client = webapp.app.test_client()
resp = client.post("/", data=dict(temperature=36, humidity=40, soil_moisture=18, rainfall=0, crop="Rice"))
html = resp.get_data(as_text=True)
static_uri = "file:///" + os.path.join(ROOT, "static").replace("\\", "/")
html = html.replace('href="/static/', f'href="{static_uri}/').replace('src="/static/', f'src="{static_uri}/')
tmp = os.path.join(tempfile.mkdtemp(), "page.html")
open(tmp, "w", encoding="utf-8").write(html)

browser = next((b for b in BROWSERS if os.path.exists(b)), None)
if not browser:
    sys.exit("No Chrome/Edge found - take the screenshot manually.")
out = os.path.join(config.FIG_DIR, "30_webapp_screenshot.png")
subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000",
                "--window-size=1280,800", f"--screenshot={out}", "file:///" + tmp.replace("\\", "/")],
               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("Screenshot ->", out, os.path.exists(out))
