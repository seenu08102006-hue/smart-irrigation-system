# Smart Irrigation using Support Vector Machine (SVM) and Electrical Optimization

A final-year project: an SVM decides whether a crop needs irrigation from temperature, humidity, soil moisture,
rainfall (and crop type); an electrical-optimisation module turns that decision into **pump ON/OFF, litres, run-time and
electricity used / saved** compared with a fixed 2-hour daily timer. Delivered as a Flask + Bootstrap web application with a
full report, slides, viva Q&A and code explanation.

> **Data note:** the dataset is **synthetic** (generated from agronomy rules, see `src/generate_dataset.py`) because no open
> dataset has exactly these columns. Pump power, flow, plot size and the timer baseline are **assumptions** in `src/config.py`.
> Results therefore demonstrate the method; they are not field measurements.

## Results (this repository)
| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| **SVM (RBF)** | 92.5 % | 91.1 % | 94.8 % | **92.9 %** | 0.982 |
| Logistic Regression | 92.1 % | 90.8 % | 94.2 % | 92.5 % | 0.981 |
| Random Forest | 91.1 % | 89.3 % | 94.0 % | 91.6 % | 0.975 |
| Decision Tree | 89.9 % | 90.3 % | 90.1 % | 90.2 % | 0.960 |

SVM is best, but its margin over Logistic Regression is smaller than the cross-validation noise (see the report for the honest
discussion). Simulated pump-energy saving vs. the timer: **28.6 %** on average over 1,000 test days.

## Folder structure
```
smart_irrigation_svm/
├── app.py                  Flask web application
├── run_all.py              runs the whole ML pipeline in order
├── requirements.txt
├── src/
│   ├── config.py           paths, ranges, crop + pump constants
│   ├── generate_dataset.py creates data/irrigation_raw.csv
│   ├── preprocess.py       cleaning + scaling/encoding transformer
│   ├── eda.py              statistics + 8 figures, writes irrigation_clean.csv
│   ├── train_models.py     tunes/compares SVM, DT, RF, LR; saves models + metrics
│   ├── energy.py           electrical optimisation formulas
│   ├── energy_analysis.py  energy saving over the test days
│   ├── predict.py          loads Joblib model -> full decision
│   └── diagrams.py         architecture / pipeline / flowchart / SVM figures
├── templates/              base.html, index.html, results.html, about.html (Bootstrap 5)
├── static/css/style.css    green theme      static/figures/  all generated graphs
├── data/                   irrigation_raw.csv, irrigation_clean.csv
├── models/                 svm_model.joblib, best_model.joblib
├── reports/                metrics.json, model_comparison.csv, eda_summary.json, energy_summary.json
├── src/analyzer.py         upload analysis engine (cleaning, EDA, SVM graphs)
├── tests/test_app.py       13 automated tests
└── docs/
    ├── Project_Report.docx / .pdf     33-page IEEE-style report (incl. source-code appendix)
    ├── Project_Presentation.pptx      20 slides with speaker notes
    ├── VIVA_QUESTIONS.md              58 questions and answers
    ├── CODE_EXPLANATION.md            statement-by-statement explanation in simple language
    └── build_report.py, build_slides.py, report_lib.py, make_screenshot.py   (regenerate the documents)
```

## Installation
Requires **Python 3.10+**.
```bash
cd smart_irrigation_svm
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```
The web pages load Bootstrap from a CDN, so the first view needs an internet connection.

## Execution
```bash
python run_all.py                # 1. dataset -> EDA -> training -> energy analysis -> diagrams (about 1 minute)
python app.py                    # 2. open http://127.0.0.1:5000
```
Individual steps: `python src/generate_dataset.py`, `python src/eda.py`, `python src/train_models.py`,
`python src/energy_analysis.py`, `python src/diagrams.py`, `python src/predict.py` (command-line test).
Rebuild the report and slides (needs python-docx and python-pptx): `python run_all.py --docs`.

## Testing
```bash
python tests/test_app.py
```
Manual test: enter 36 °C, 40 %, soil 18 %, rain 0, Rice → *Irrigation Required, Pump ON*.
Enter 22 °C, 85 %, soil 75 %, rain 30, Wheat → *Not Required, Pump OFF, 3.0 kWh saved*.

## Upload & Analyze your own dataset (new)
Open **Upload & Analyze** in the top menu (`/upload`).
1. Upload any CSV (max 10 MB, at least 30 rows) or press *Use sample data*.
2. Check the preview and choose the **target column** (the class to predict, e.g. `irrigation_needed`, Yes/No, 0/1, or any label column).
3. Press *Analyze & train SVM*. You get: a data-cleaning summary (duplicates, missing values, ID/constant columns removed), EDA graphs
   (missing values, class balance, histograms, correlation heat-map) and **SVM graphs** - confusion matrix, ROC curve (two-class data),
   decision regions, C/gamma tuning heat-map, kernel comparison (linear / poly / RBF / sigmoid), learning curve, metric bars - plus a
   download of the trained SVM (`.joblib`).

It works for two-class and multi-class targets and for numeric and text-category inputs. Files over 6,000 rows are sampled to keep
training fast. Uploads are stored in `workspace/` and graphs in `static/generated/` (safe to delete). Code: `src/analyzer.py`.

## JSON API
```bash
curl -X POST http://127.0.0.1:5000/api/predict -H "Content-Type: application/json" \
     -d '{"temperature":36,"humidity":40,"soil_moisture":18,"rainfall":0,"crop":"Rice"}'
```

## Using your own (real) data
Put a CSV named `data/irrigation_raw.csv` with columns `temperature, humidity, soil_moisture, rainfall, crop_type,
irrigation_needed` (0/1) in place of the generated one, skip `generate_dataset.py`, and run `eda.py`, `train_models.py`,
`energy_analysis.py`. Add any new crop names to `CROPS` in `src/config.py`. Edit the pump constants to match your hardware.

## Before you submit
* Replace the `[Student Name]`, guide, department and college placeholders on the report title page (`docs/build_report.py`) and slide 1 (`docs/build_slides.py`), then run `python run_all.py --docs`.
* Open the report in Word and press **F9** on the table of contents if page numbers look stale.
* Read the Literature Survey and References yourself; add papers from your own domain reading. All 16 listed references are real, widely-cited works, but check each citation against the source before submission.
* Run a plagiarism check as your university requires. The code, data generator, text and diagrams were written for this project; the algorithms are standard and are cited.
