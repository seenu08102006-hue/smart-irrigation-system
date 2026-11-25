# Smart Irrigation System using SVD, PDE, SVM and Electrical Optimization

A web application that analyses **only the dataset you upload**: it validates the file, cleans it, calculates statistics, draws
graphs, reduces the features with **SVD**, solves a **soil-moisture PDE** calibrated on your data, trains an **SVM** on the SVD
components plus the PDE result, and estimates the water and electricity of the pump.

```
Upload -> Validation -> Cleaning -> EDA -> SVD feature reduction -> PDE soil moisture -> SVM prediction -> Water & electricity
```

**Nothing is pre-loaded.** There is no sample data, no demo data, no built-in model, no random or simulated values and no
internet download. Open the site and the only thing you see is the *Upload Dataset* button. Every number, graph and prediction
comes from the uploaded file.

Stack: React + Tailwind CSS (frontend) · Flask (backend) · scikit-learn SVM · NumPy/SciPy PDE solver · SQLite · Chart.js · Pandas.

## Workflow
1. **Home** shows one button, *Upload Dataset*. Nothing is analysed before an upload.
2. **Upload** only `.csv` or `.xlsx` (anything else is rejected, max 25 MB).
3. **Validation** (automatic): file type, empty file, corrupted file, too few rows, **missing required columns**,
   duplicate rows, missing values. A clear message explains what is wrong; for missing columns it names them
   (e.g. *"Required column(s) missing: Humidity, Rainfall"*) and lets you map differently named columns by hand.
4. **Required columns:** Date, Temperature, Humidity, Soil Moisture, Rainfall (names such as `Temp`, `RH`, `Rain`, `Soil_Moisture`
   are recognised). Optional: a crop column and an irrigation-needed (Yes/No) column.
5. **Analysis** (automatic, live progress bar, every step visible): type conversion, duplicate removal, impossible sensor
   values, missing values, outliers (IQR), label preparation, scaling, statistics, graphs, **PDE soil-moisture model**, SVM.
6. **Dashboard** (tabs): dataset summary, data-quality report, cleaning log, statistics, graphs (daily temperature, rainfall,
   humidity, soil moisture ...), **PDE soil moisture** (fit, distribution over depth and time, 7-day forecast), SVM model,
   **water & electricity**, prediction history, findings. Reports download as PDF, Excel or CSV.
7. **Predict**: enter temperature, humidity, soil moisture, rainfall (+ crop) and get *Irrigation required (Yes/No)*, *Pump ON/OFF*,
   confidence, the PDE's soil moisture for tomorrow and, once you entered your field and pump data, the *water requirement (L)*
   and *estimated electricity (kWh)*.

### The SVD module (feature reduction before the SVM)
Why SVD is used: *SVD reduces redundant features, removes noise, improves computational efficiency, and provides optimized input features for the SVM classifier.*

1. **Feature matrix** `X`: all numeric columns of your file are picked automatically (temperature, humidity, rainfall, soil moisture **and any other
   numeric sensor** such as soil temperature, wind speed, nutrients). Identifier / row-counter columns, constant columns and columns with more than 5 % missing
   values are skipped (and listed in the cleaning log).
2. **Normalisation**: every feature is standardised (mean 0, std 1) so that no sensor dominates because of its unit.
3. **Decomposition** `X = U Σ Vᵀ` with `scipy.linalg.svd`: `U` = records in component space, `Σ` = singular values (importance), `Vᵀ` = loadings (how every
   feature contributes to every component). The page checks that `U Σ Vᵀ` reproduces `X` (error ≈ 1e-15).
4. **Reduction**: the smallest number of components that keeps **at least 95 %** of the variance is used; the scores `X·V[:, :k]` become SVM inputs.
5. **No leakage**: inside the SVM pipeline the standardisation and SVD are fitted on the training rows only (`SvdReducer` in `backend/svd_module.py`).

The dashboard tab **SVD Feature Reduction** shows the original features, the components kept, the variance preserved, the singular values, a scree plot,
explained-variance chart, singular-value distribution, feature-reduction comparison, feature contributions, the first two components, the loadings, and
**SVM before vs after SVD** (accuracy, precision, recall, F1, training time, number of inputs). Both SVMs use the same split and grid search and both receive the
PDE features and the crop; the SVD model is the one kept for predictions. The result is measured, not promised: with few, uncorrelated features SVD cannot drop
a component and the two SVMs perform alike; it pays off when a file has many, partly redundant sensors. The PDE is **not** fed with SVD components: it keeps using
the original soil moisture, rainfall, temperature, humidity and irrigation values.

### The PDE module
`∂θ/∂t = D ∂²θ/∂z²` over the root-zone depth (0 = surface, 1 = bottom), with rainfall (and irrigation, if the file has an irrigation
column) entering at the surface, evaporation leaving at the surface (rising with temperature, falling with humidity) and drainage at
the bottom. It is solved by finite volumes in space and implicit Euler in time (Thomas algorithm in NumPy). The constants
`D, α, k_e, k_d (, β)` are **fitted to your soil-moisture series with SciPy least squares** (one day ahead), not assumed. The page shows the
error next to the error of the naive guess "tomorrow = today", so you can see whether the PDE really helps on your file. It needs at least 20
pairs of consecutive daily records. The forecast starts from the last reading; future weather comes only from your data (mean of the last
7 days, rain either 0 mm or your average daily rain: two scenarios). The PDE estimate of tomorrow's moisture and its change are **features of the SVM**.

### Water and electricity
A weather file cannot contain the size of your field or the specification of your pump, so you **enter** them (Dashboard → *Water & electricity*):
area, root depth, pump power, pump flow, and optionally the hours the pump runs per day today and the price per kWh. Until then no litres or kWh are shown.
`water (L) = deficit/100 × root depth (mm) × area (m²)`, `kWh = litres / flow × power`, on the days the SVM switches the pump ON; the deficit is the gap
between the 75th percentile of your soil moisture and the PDE's value for tomorrow. Pump status = ON exactly when irrigation is required.
The saving is computed against the pump hours you entered, if any.

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
python backend/test_api.py                              # 9 API tests (validation, analysis, SVD, PDE, prediction, pump data, reports)
pip install playwright && python tests/e2e_ui.py        # end-to-end test in real Chrome, saves screenshots
```
The tests create small throw-away files in a temporary folder because an upload feature cannot be tested without a file;
the application itself contains no data.

## Folder structure
```
backend/
  app.py              Flask API: upload, validation, analysis (background thread), status, prediction, reports, serves the React build
  dataset_service.py  reading, column detection, cleaning, statistics, chart data, PDE + SVM training, findings, prediction
  svd_module.py       SVD analysis + SvdReducer (scikit-learn transformer used in the SVM pipeline)
  pde_model.py        soil-moisture PDE: finite-volume solver, calibration (SciPy), distribution, forecast
  water_energy.py     litres and kWh from the SVM plan, PDE deficit and the user's pump data
  reports.py          PDF (ReportLab + matplotlib) / Excel (openpyxl, native charts) / CSV report builders
  database.py config.py  SQLite helpers and settings
  test_api.py         API tests
  templates/          help page shown if the React build is missing
database/schema.sql   tables: datasets, predictions
frontend/src/
  pages/              Home, Upload, Analysis (the dashboard), Dashboard (opens the analysis), Predict, Datasets
  components/         Navbar, Footer, Loader, ChartCard, DatasetCharts, SvdPanel, PdePanel, UsagePanel, HistoryPanel, Heatmap, BoxPlots, CleaningSteps, ReportButtons
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
| GET | `/api/datasets/<id>/svd` | SVD analysis: singular values, explained variance, loadings, SVM before/after comparison |
| GET | `/api/datasets/<id>/model` | features, crops and observed ranges of the trained model |
| POST | `/api/datasets/<id>/predict` | prediction (irrigation, pump ON/OFF, PDE moisture, water/kWh if pump data exists) |
| POST | `/api/datasets/<id>/system` | save the user's field area, root depth, pump power / flow (+ optional baseline hours, tariff) |
| GET | `/api/datasets/<id>/usage` | water and electricity over the uploaded period, monthly, saving vs baseline |
| GET | `/api/datasets/<id>/predictions` | predictions made with that model |
| GET | `/api/datasets/<id>/report/pdf\|xlsx\|csv` | download a report |

## Limits to be aware of
* There is **no login**: put the site behind a VPN / basic auth if it is exposed to others (see `docs/DEPLOYMENT.md`).
* Only the first sheet of an Excel file is read.
* The PDE is a simple 1-D model fitted to a single soil-moisture series. If the readings are noisy, irrigation is not recorded or the data is not daily, it may
  not beat the naive "tomorrow = today" guess; the dashboard shows this comparison and the findings say so.
* An SVM on a derived label mostly learns the soil-moisture pattern of your own file; its accuracy says little about real irrigation
  decisions. Quality depends entirely on the quality of the uploaded data.
