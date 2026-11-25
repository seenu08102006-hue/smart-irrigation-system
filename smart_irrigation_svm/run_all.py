"""
run_all.py - runs the whole project pipeline in the correct order.

    python run_all.py           -> data, EDA, training, energy analysis, diagrams
    python run_all.py --docs    -> ... and also rebuilds the report (.docx) and slides (.pptx)
Afterwards start the web app with:  python app.py
"""
import subprocess
import sys

STEPS = [
    ("Generating dataset", "src/generate_dataset.py"),
    ("Cleaning + EDA", "src/eda.py"),
    ("Training and comparing models", "src/train_models.py"),
    ("Energy analysis", "src/energy_analysis.py"),
    ("Drawing diagrams", "src/diagrams.py"),
]
DOCS = [
    ("Building report", "docs/build_report.py"),
    ("Building slides", "docs/build_slides.py"),
]

steps = STEPS + (DOCS if "--docs" in sys.argv else [])
for i, (label, script) in enumerate(steps, 1):
    print(f"\n=== [{i}/{len(steps)}] {label} ({script}) ===")
    if subprocess.call([sys.executable, script]) != 0:
        sys.exit(f"Step failed: {script}")
print("\nAll done. Start the web app with:  python app.py")
