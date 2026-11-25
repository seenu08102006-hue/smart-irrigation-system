# Code guide - what every file does

Principle: **all results come from the uploaded dataset**. There is no data, model or constant describing a farm anywhere in the code.

## Backend (`backend/`)

### `app.py` - the Flask API
* `upload_dataset` (`POST /api/datasets`): accepts only `.csv`/`.xlsx`, saves the file under a random name, calls
  `dataset_service.read_table` (empty / corrupted / too-small files raise a readable error and the file is deleted), builds the
  file information and preview, detects the columns and reports `missing_required` (Date, Temperature, Humidity, Soil Moisture, Rainfall).
* `analyze_dataset` (`POST /api/datasets/<id>/analyze`): refuses with HTTP 422 if a required column is not mapped, otherwise starts
  `_analysis_worker` in a background thread. The worker stores the finished result (JSON) and the trained model path in SQLite.
  `PROGRESS` (a dictionary guarded by a lock) holds the live progress, which `GET .../status` returns every 700 ms to the UI.
* `get_dataset`, `list_datasets`, `delete_dataset`: read, list and delete uploads (the file, the model and its predictions go together).
* `model_info` / `predict`: the prediction form and the prediction itself. They exist only for an analysed dataset and return
  404 with *"Please upload a real-life CSV or Excel dataset to begin analysis."* when there is none.
* `dataset_report`: builds a PDF / Excel / CSV report from the stored results.
* The last routes serve the compiled React app; unknown `/api/...` paths return 404 JSON.

### `dataset_service.py` - everything that happens to an upload
* `read_table`: reads CSV (separator sniffed, UTF-8 or Latin-1) or the first Excel sheet; raises `DatasetError` for empty, corrupted or
  fewer-than-30-row files.
* `file_info`: rows, columns, missing cells, duplicate rows, size, per-column dtype and a 10-row preview.
* `detect_mapping`: finds each column by name synonyms (`temp`, `RH`, `rain`, `soil moist`, ...); a date column must really parse as dates.
* `missing_required` / `check_required`: the required-column validation.
* `run_analysis`: the visible steps - load, types, duplicates, impossible values, missing values (rows dropped), outliers (reported,
  kept), label, scaling note, statistics, charts, **PDE**, SVM (features include `pde_next`, `pde_change`), findings and the daily pump plan. Each step reports its progress.
* `_positive_mask`: turns a Yes/No (1/0, true/false...) column into 0/1.
* Derived label (only without an irrigation column): next reading of soil moisture at or below the lowest third of the file's own values.
* `build_charts`: time series (daily; weekly if more than 400 days), histograms, box-plot numbers, scatter sample, bar and pie data.
* `train_svm`: 80/20 stratified split, `StandardScaler` (+ `OneHotEncoder` for crop) in a pipeline, `GridSearchCV` over C and gamma, final
  RBF `SVC(probability=True)`, metrics on the unseen 20 %, confusion matrix, ROC points; saves the model with `joblib`.
* `recommendations`: plain-language findings computed from the statistics and metrics.
* `predict_with_model`: loads the saved model and predicts one record.

### `svd_module.py` - SVD feature reduction
* `analyse`: standardises the feature matrix, runs `scipy.linalg.svd` (economy size), returns singular values, explained variance ratio, cumulative variance, loadings (Vᵀ), feature contributions, reconstruction errors, the first two component scores and the chosen number of components.
* `choose_k`: smallest k whose cumulative explained variance reaches 95 %.
* `SvdReducer`: scikit-learn transformer (standardise -> SVD -> project on the first k right singular vectors); fitted on training rows only inside the SVM pipeline.
* In `dataset_service.py`: `select_extra_features` finds the additional numeric sensor columns; `train_svm` fits two SVMs on the same split (original features vs SVD components, both plus the PDE features and crop) and records metrics and training time of each; the SVD model is saved and used for predictions.

### `pde_model.py` - soil-moisture PDE
* `step`: advances moisture profiles by one day (finite volumes, implicit Euler, 4 sub-steps) for many days at once; `_thomas` is the vectorised tridiagonal solver.
* `daily_series`: one row per calendar day (mean T, H, soil; rain summed, or averaged when several crops share the weather).
* `calibrate`: SciPy `least_squares` fits D, alpha, k_e, k_d (beta if an irrigation column exists) so the PDE reproduces the next day's soil moisture; reports RMSE, the naive-guess RMSE, skill and R² of the daily change.
* `simulate`: builds the dashboard data - one-day-ahead fit, depth-by-time distribution (last 60 days), 7-day forecast for two rain scenarios taken from the file, depth profiles.
* `one_step_mean`: used for the SVM feature `pde_next` and for manual predictions.

### `water_energy.py`
Validates the field/pump values typed by the user and computes litres, pump hours and kWh per day, month and in total, plus the saving versus the user's current pump hours.

### `reports.py`
`build_pdf` (ReportLab text/tables + matplotlib graphs), `build_xlsx` (openpyxl sheets with native Excel charts), `build_csv`.

### `database.py`, `config.py`, `database/schema.sql`
SQLite helpers, paths/limits (upload folder, model folder, 25 MB), and the two tables: `datasets` (file, status, JSON results, model file)
and `predictions` (manual predictions per dataset). An old database from a previous version (with users/energy columns) is cleaned
up on start.

### `test_api.py`
9 tests: nothing exists before upload, wrong/empty/corrupt files rejected, missing columns named, full flow with a label column
(statistics equal pandas values, metrics, prediction, reports, delete), derived-label flow, Excel upload, too-many-missing-values error.

## Frontend (`frontend/src/`)
* `main.jsx`, `App.jsx`: providers and routes (`/`, `/analyze`, `/analysis/:id`, `/dashboard`, `/predict`, `/datasets`).
* `pages/Home.jsx`: the single *Upload Dataset* button and the upload message.
* `pages/Upload.jsx`: drag & drop / browse, upload progress, validation messages, file info cards, preview, live analysis progress
  and cleaning steps, missing-column message with a manual column-mapping form.
* `pages/Analysis.jsx`: the dashboard with tabs - Overview (summary, data quality, model result), Data cleaning, Statistics, Graphs,
  AI model, Findings, and the report buttons.
* `pages/Dashboard.jsx`: opens the analysis of the dataset in use, or shows the upload message if there is none.
* `components/SvdPanel.jsx`: the SVD Feature Reduction tab (cards, scree plot, explained variance, singular value distribution, reduction comparison, loadings, before/after SVM table and charts).
* `components/PdePanel.jsx`, `UsagePanel.jsx`, `HistoryPanel.jsx`: the PDE tab (equation, fitted constants, fit chart, depth-time grid, forecast), the water & electricity tab with the pump form, and the prediction history.
* `pages/Predict.jsx`: manual prediction with the model of the chosen upload; ranges shown are the ones seen in that file.
* `pages/Datasets.jsx`: list of uploads with accuracy, switch / view / delete.
* `components/`: `Navbar` (menu appears after the first upload, dark-mode switch), `Footer`, `Loader`, `ChartCard`, `DatasetCharts`
  (all Chart.js graphs), `Heatmap` and `BoxPlots` (SVG/CSS), `CleaningSteps`, `ReportButtons`.
* `api.js`: fetch/XHR client. `utils/active.js`: remembers the dataset in use (localStorage). `charts.js`: Chart.js setup and colours.
  `context/`: dark-mode and toast providers. `index.css`: Tailwind plus the glass-card styles.

## Other
* `tests/e2e_ui.py`: Chrome test of the complete flow. `run.bat`: Windows launcher.
* `smart_irrigation_svm/`: an unrelated, earlier standalone project; this app does not import it.
