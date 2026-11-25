# Smart Irrigation Data Analysis System

A web application that analyses **only the dataset you upload**: it validates the file, cleans it, calculates statistics, draws
graphs and trains an SVM (Support Vector Machine) on your data.

**Nothing is pre-loaded.** There is no sample data, no demo data, no built-in model, no random or simulated values and no
internet download. Open the site and the only thing you see is the *Upload Dataset* button. Every number, graph and prediction
comes from the uploaded file.

Stack: React + Tailwind CSS (frontend) · Flask (backend) · scikit-learn SVM · SQLite · Chart.js · Pandas + NumPy.

## Workflow
1. **Home** shows one button, *Upload Dataset*. Nothing is analysed before an upload.
2. **Upload** only `.csv` or `.xlsx` (anything else is rejected, max 25 MB).
3. **Validation** (automatic): file type, empty file, corrupted file, too few rows, **missing required columns**,
   duplicate rows, missing values. A clear message explains what is wrong; for missing columns it names them
   (e.g. *"Required column(s) missing: Humidity, Rainfall"*) and lets you map differently named columns by hand.
4. **Required columns:** Date, Temperature, Humidity, Soil Moisture, Rainfall (names such as `Temp`, `RH`, `Rain`, `Soil_Moisture`
   are recognised). Optional: a crop column and an irrigation-needed (Yes/No) column.
5. **Analysis** (automatic, live progress bar, every step visible): type conversion, duplicate removal, impossible sensor
   values, missing values, outliers (IQR), label preparation, scaling, statistics, graphs, SVM.
6. **Dashboard** (tabs): dataset summary, data-quality report, cleaning log, statistics (mean, median, mode, standard deviation,
   min, max, correlation), graphs, AI model performance, findings. Reports can be downloaded as PDF, Excel or CSV.
7. **Predict**: enter temperature, humidity, soil moisture, rainfall (+ crop) and get Yes/No with a confidence score from the SVM
   trained on **your** file.

### Graphs (all from the uploaded file)
Daily soil-moisture, rainfall, temperature and humidity history · combined weather trend · correlation heatmap · histograms ·
box plots · scatter plot · bar and pie charts · confusion matrix · ROC curve.

### How the data is treated (no invented values)
* Rows with a **missing value are removed**, never filled with estimated numbers. If more than half of the rows would be lost, the
  analysis stops with an explanation.
* **Outliers are detected (IQR rule) and reported but kept unchanged.**
* Impossible readings (e.g. humidity above 100 %) are treated as missing.
* If the file has **no irrigation column**, the label is derived from *your own* soil moisture: "irrigation needed" = the **next**
  reading is at or below the lowest third of your soil-moisture values. The page and the reports say clearly that the label is derived.
  Upload a file with a real irrigation column for decision-based predictions.
* The SVM (RBF kernel) uses an 80/20 stratified split, scaling fitted on the training rows only, a small grid search
  (C, gamma) and reports accuracy, precision, recall, F1, ROC-AUC, confusion matrix and ROC curve on the unseen 20 %.

## Run it
Requirements: Python 3.10+, Node.js 18+.
```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
python backend/app.py             # open http://localhost:5000
```
On Windows `run.bat` does all of this. For frontend development run `npm run dev` in `frontend/` (port 5173, proxies `/api` to Flask).

## Tests
```bash
python backend/test_api.py                              # 7 API tests (validation, analysis, prediction, reports)
pip install playwright && python tests/e2e_ui.py        # end-to-end test in real Chrome, saves screenshots
```
The tests create small throw-away files in a temporary folder because an upload feature cannot be tested without a file;
the application itself contains no data.

## Folder structure
```
backend/
  app.py              Flask API: upload, validation, analysis (background thread), status, prediction, reports, serves the React build
  dataset_service.py  reading, column detection, cleaning, statistics, chart data, SVM training, findings, prediction
  reports.py          PDF (ReportLab + matplotlib) / Excel (openpyxl, native charts) / CSV report builders
  database.py config.py  SQLite helpers and settings
  test_api.py         API tests
  templates/          help page shown if the React build is missing
database/schema.sql   tables: datasets, predictions
frontend/src/
  pages/              Home, Upload, Analysis (the dashboard), Dashboard (opens the analysis), Predict, Datasets
  components/         Navbar, Footer, Loader, ChartCard, DatasetCharts, Heatmap, BoxPlots, CleaningSteps, ReportButtons
  api.js utils/active.js context/   API client, "dataset in use" helper, theme and toast providers
tests/e2e_ui.py       browser test
docs/                 CODE_GUIDE.md (every file explained), DEPLOYMENT.md
smart_irrigation_svm/ a separate earlier Python/Bootstrap project (model comparison, report, slides); not used by this app
uploads/ user_models/ created at run time: your uploaded files and the SVMs trained on them
```

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/datasets` | upload `.csv/.xlsx` (multipart `file`): validation, file info, preview, detected columns, `missing_required` |
| POST | `/api/datasets/<id>/analyze` | start the analysis (optional `mapping`, `derive_threshold`); 422 if required columns are missing |
| GET | `/api/datasets/<id>/status` | live progress (percent, current step, steps) |
| GET | `/api/datasets/<id>` | full results: cleaning log, statistics, chart data, SVM metrics, findings |
| GET | `/api/datasets` / DELETE `/api/datasets/<id>` | list / delete uploads |
| GET | `/api/datasets/<id>/model` | features, crops and observed ranges of the trained model |
| POST | `/api/datasets/<id>/predict` | prediction with the SVM trained on that upload |
| GET | `/api/datasets/<id>/predictions` | predictions made with that model |
| GET | `/api/datasets/<id>/report/pdf\|xlsx\|csv` | download a report |

## Limits to be aware of
* There is **no login**: put the site behind a VPN / basic auth if it is exposed to others (see `docs/DEPLOYMENT.md`).
* Only the first sheet of an Excel file is read.
* An SVM on a derived label mostly learns the soil-moisture pattern of your own file; its accuracy says little about real irrigation
  decisions. Quality depends entirely on the quality of the uploaded data.
