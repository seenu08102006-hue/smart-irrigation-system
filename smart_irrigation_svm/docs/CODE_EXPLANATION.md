# Code Explanation in Simple Language

How to read this: each section quotes a piece of code and explains **what every statement does and why**. The
core files (`config`, `generate_dataset`, `preprocess`, `energy`, `predict`, `app`, `train_models`) are explained
statement by statement. The long plotting scripts (`eda`, `diagrams`, `energy_analysis`) repeat the same
Matplotlib pattern, so they are explained figure by figure.

**Python words used a lot**
* `import x` – bring a ready-made toolbox into the file. `from x import y` – bring just one tool.
* `def name(inputs):` – define a function (a named recipe). `return` hands the answer back.
* `df` – a pandas DataFrame, which is an Excel-like table. `df["col"]` – one column.
* `np` = NumPy (fast maths on arrays). `pd` = pandas (tables). `plt` = Matplotlib (graphs).

---
## 1. `src/config.py` – settings in one place

| Code | Meaning |
|---|---|
| `import os` | Tool for working with file paths. |
| `ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` | `__file__` is this file. `abspath` gives its full path; `dirname` twice climbs two levels up (file → `src` → project folder). So `ROOT` is the project folder wherever it is stored. |
| `DATA_DIR`, `MODEL_DIR`, `FIG_DIR`, `REPORT_DIR` | Folders for data, models, figures and reports, built with `os.path.join` (adds the correct `/` or `\`). Figures go to `static/` so Flask can show them. |
| `RAW_CSV`, `CLEAN_CSV` | Paths of the dirty and the cleaned dataset. |
| `SVM_MODEL_PATH`, `BEST_MODEL_PATH` | Where the Joblib model files are saved. |
| `METRICS_JSON`, `COMPARISON_CSV` | Where the results of training are saved. |
| `NUMERIC_FEATURES = [...]` | The four sensor columns. |
| `CATEGORICAL_FEATURES = ["crop_type"]` | The text column. |
| `TARGET = "irrigation_needed"` | The column we want to predict (1 = yes, 0 = no). |
| `RANDOM_STATE = 42` | Seed number so random steps give the same result every run. |
| `VALID_RANGES = {...}` | Smallest and largest physically possible value for each sensor. Used to catch sensor errors and wrong user input. |
| `CROPS = {...}` | For each crop: `threshold` (moisture % below which it normally needs water) and `water_factor` (how thirsty it is compared with an average crop). |
| `PUMP_POWER_KW = 1.5` | Electric power of the pump motor. |
| `PUMP_FLOW_L_PER_H = 3000.0` | Litres the pump delivers per hour. |
| `LITRES_PER_PCT = 300.0` | Litres needed to raise the soil moisture of a 100 m² plot by 1 %. |
| `LITRES_PER_MM_RAIN = 100.0` | 1 mm of rain on 100 m² is 100 litres. |
| `TIMER_HOURS = 2.0` | How long the old timer system runs the pump every day (the comparison baseline). |

---
## 2. `src/generate_dataset.py` – makes the data

```python
def generate(n_samples=5000, seed=config.RANDOM_STATE):
    rng = np.random.default_rng(seed)
```
`generate` is a function with default settings: 5,000 rows and the fixed seed. `rng` is a random-number generator; with the same seed it gives the same numbers every time.

```python
    crop = rng.choice(list(config.CROPS), size=n_samples)
```
Pick a random crop name for each of the 5,000 days.

```python
    temperature = np.clip(rng.normal(29, 7, n_samples), 5, 50)
```
Draw temperatures from a bell curve (average 29 °C, spread 7). `np.clip(…, 5, 50)` forces every value to stay between 5 and 50 so there are no absurd temperatures.

```python
    humidity = np.clip(rng.normal(62, 15, n_samples) - 0.6 * (temperature - 29), 10, 100)
```
Humidity is drawn the same way but reduced on hotter days (`- 0.6 * (temperature - 29)`), because hot air is usually drier. Then clipped to 10–100 %.

```python
    soil_moisture = np.clip(rng.normal(42, 16, n_samples), 3, 95)
```
Soil moisture: average 42 %, kept between 3 and 95 %.

```python
    rainy_day = rng.random(n_samples) < 0.30
    rainfall = np.where(rainy_day, rng.gamma(2.0, 7.0, n_samples), 0.0)
    rainfall = np.clip(rainfall, 0, 150)
```
`rng.random` gives a number between 0 and 1 for each day; `< 0.30` is `True` on about 30 % of days (rainy). `np.where(condition, a, b)` uses a rain amount from a gamma distribution (many small rains, few big ones) on rainy days and 0 otherwise. Clip at 150 mm.

```python
    threshold = np.array([config.CROPS[c]["threshold"] for c in crop], dtype=float)
```
For each day look up the chosen crop's moisture threshold and make an array of numbers.

```python
    heat = 0.004 * (temperature - 25) * np.abs(temperature - 25)
```
Heat effect that grows faster than a straight line: above 25 °C it adds need, below 25 °C it subtracts, and the effect is squared (so 40 °C matters much more than 30 °C).

```python
    score = (0.12 * (threshold - soil_moisture)
             + heat
             - 0.025 * (humidity - 60) * (temperature / 30)
             - 1.6 * (1 - np.exp(-rainfall / 15))
             + rng.normal(0, 0.55, n_samples))
```
The "water-stress score". Positive = crop is short of water.
1. `0.12 * (threshold - soil_moisture)` – the drier the soil is compared with what the crop likes, the higher the score.
2. `+ heat` – hot weather increases it.
3. `- 0.025 * (humidity - 60) * (temperature / 30)` – humid air lowers it, and this effect is stronger on hot days (multiplying by temperature).
4. `- 1.6 * (1 - np.exp(-rainfall / 15))` – rain lowers it, but with diminishing returns: the first mm help a lot, later mm help less (the soil is already full).
5. `+ rng.normal(0, 0.55, …)` – random noise to mimic sensor error.

```python
    irrigation = (score > 0).astype(int)
```
`score > 0` gives True/False; `.astype(int)` turns it into 1/0. This is our label.

```python
    df = pd.DataFrame({... "temperature": temperature.round(1), ...})
```
Put all columns into a table, rounding sensor values to 1 decimal like a real sensor.

```python
    for col in config.NUMERIC_FEATURES:
        idx = rng.choice(n_samples, size=int(0.02 * n_samples), replace=False)
        df.loc[idx, col] = np.nan
```
For each sensor column choose 2 % of row numbers (no repeats) and blank them (`np.nan` = "not a number" = missing). This makes the file realistically dirty.

```python
    spikes = rng.choice(n_samples, size=20, replace=False)
    df.loc[spikes, "temperature"] = 99.0
    df.loc[rng.choice(n_samples, size=15, replace=False), "soil_moisture"] = -5.0
```
Insert 20 impossible temperatures (99 °C) and 15 impossible negative moistures – like faulty sensors.

```python
    df = pd.concat([df, df.sample(50, random_state=seed)], ignore_index=True)
    return df
```
Copy 50 random rows and add them again at the end (duplicates). `return df` gives the table back.

```python
if __name__ == "__main__":
```
"Run the following only when this file is started directly" (not when another file imports it).
`os.makedirs(..., exist_ok=True)` makes the data folder if missing; `data.to_csv(...)` writes the table to a CSV file; `print` shows the path and size.

---
## 3. `src/preprocess.py` – cleaning and scaling

```python
def clean_data(df, verbose=True):
    report = {"rows_before": len(df)}
    df = df.copy()
```
Start a small notebook (`report`) to count what we fix. `df.copy()` so we do not damage the caller's table.

```python
    df = df.drop_duplicates()
    report["duplicates_removed"] = report["rows_before"] - len(df)
```
Delete rows that are exact copies; the difference in row count is the number removed.

```python
    for col in config.NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
```
Make sure each sensor column is numeric; any text that is not a number becomes NaN instead of crashing.

```python
    for col, (low, high) in config.VALID_RANGES.items():
        df.loc[(df[col] < low) | (df[col] > high), col] = float("nan")
```
For every sensor, find rows below the minimum **or** (`|`) above the maximum and set them to missing. After this, 99 °C and −5 % become NaN.

```python
    report["missing_before_fill"] = int(df[config.NUMERIC_FEATURES].isna().sum().sum())
```
`isna()` marks missing cells; the first `.sum()` counts per column; the second `.sum()` adds them up.

```python
    df = df.dropna(subset=[config.TARGET, "crop_type"])
```
Rows without a label or crop cannot be repaired, so delete them.

```python
    for col in config.NUMERIC_FEATURES:
        df[col] = df[col].fillna(df.groupby("crop_type")[col].transform("median"))
```
For each sensor: group the rows by crop, calculate that crop's median, and put it in the empty cells of the same crop (`fillna`).

```python
    df[config.TARGET] = df[config.TARGET].astype(int)
    df = df.reset_index(drop=True)
```
Make the label whole numbers; renumber the rows 0, 1, 2…

The last lines count the rows after cleaning and missing values left (should be 0), print the report and return `df, report`.

```python
def make_preprocessor():
    return ColumnTransformer([
        ("scale", StandardScaler(), config.NUMERIC_FEATURES),
        ("crop", OneHotEncoder(categories=[list(config.CROPS)], handle_unknown="ignore"), config.CATEGORICAL_FEATURES),
    ])
```
A `ColumnTransformer` applies different treatment to different columns: the 4 sensors are standardised (value − mean) / std; `crop_type` becomes five 0/1 columns (one-hot). `handle_unknown="ignore"` means an unseen crop name will not crash the program.

---
## 4. `src/energy.py` – electrical optimisation

```python
def estimate(irrigation_needed, temperature, soil_moisture, rainfall, crop="Maize"):
    profile = config.CROPS.get(crop, config.CROPS["Maize"])
```
Look up the crop's numbers; if the crop name is unknown fall back to Maize.

```python
    baseline_kwh = config.TIMER_HOURS * config.PUMP_POWER_KW      # 2 h × 1.5 kW = 3.0 kWh
    baseline_litres = config.TIMER_HOURS * config.PUMP_FLOW_L_PER_H  # 2 h × 3000 = 6000 L
    litres = 0.0
```
What the old timer system would use, and start with zero water for our system.

```python
    if irrigation_needed:
        target = profile["threshold"] + 15
        deficit = max(0.0, target - soil_moisture)
```
Only if the SVM said "yes": we water until the soil is 15 points above the crop's threshold. `deficit` is how many % of moisture are missing (never negative).

```python
        heat_factor = 1.0 + max(0.0, temperature - 30) * 0.02
        litres = deficit * config.LITRES_PER_PCT * profile["water_factor"] * heat_factor
        litres -= rainfall * config.LITRES_PER_MM_RAIN
        litres = min(max(litres, 500.0), baseline_litres * 1.5)
```
Heat factor: +2 % of water for every °C above 30. Litres = missing % × 300 L/% × crop thirst × heat factor. Subtract what the rain already gave. Finally keep the answer between 500 L (a useful minimum) and 1.5 × the timer volume (a safety cap).

```python
    hours = litres / config.PUMP_FLOW_L_PER_H
    used = hours * config.PUMP_POWER_KW
    saved = max(0.0, baseline_kwh - used)
```
Hours = litres ÷ litres-per-hour. Energy (kWh) = hours × kW. Saving = timer energy − our energy, never below 0.

The `return {...}` builds a dictionary (a labelled bundle) with pump ON/OFF, litres, minutes, kWh used, baseline, kWh saved and percentage saved, all rounded.

---
## 5. `src/predict.py` – use the saved model

* `_model = None` – a cache variable so the file is read only once.
* `load_model()` – `global _model` lets the function change that variable; if it is still `None`, `joblib.load(path)` reads the saved pipeline from disk; then it returns it.
* `validate(...)` – puts the four values in a dictionary, loops over them, and for each one adds a message to `problems` if the value is `None` (not a number) or outside the allowed range. An empty list means everything is fine.
* `predict_irrigation(...)`:
  1. `row = pd.DataFrame([{...}])` – one-row table with the same column names used in training.
  2. `needed = bool(model.predict(row)[0])` – the pipeline scales/encodes the row and the SVM answers 0 or 1; `[0]` takes the first (only) answer.
  3. `prob_yes = float(model.predict_proba(row)[0][1])` – probability that the class is 1.
  4. `result = energy.estimate(...)` – electrical numbers for this decision.
  5. `result.update({...})` – add the text prediction, the confidence (the probability of the class that was chosen, ×100) and the crop.
* The bottom `if __name__ == "__main__":` runs two example predictions when you start the file directly.

---
## 6. `app.py` – the Flask web app

* `sys.path.insert(0, ".../src")` – tells Python to also look inside `src/` when importing.
* `app = Flask(__name__)` – creates the web application object.
* `read_float(name)` – reads a field from the form (or from JSON) and tries `float(value)`; if it is empty or text it returns `None` instead of crashing.
* `@app.route("/", methods=["GET", "POST"])` – a *decorator* that says: when the browser asks for `/`, run the function below. GET = just open the page, POST = the form was submitted.
* `home()`:
  - sets `result = None`, `errors = []` and default form values;
  - if the request is POST: read four numbers and the crop, remember the typed values (so the form is not emptied), call `validate`, add an error if the crop is unknown, and if there are no errors call `predict_irrigation`;
  - `render_template("index.html", ...)` fills the HTML template with these variables.
* `@app.route("/api/predict", methods=["POST"])` – same logic but for programs: reads JSON, returns `jsonify(...)`; status `400` means "bad request" when validation fails.
* `/results` – opens `metrics.json` and sends it to `results.html` to build the table.
* `/about` – shows the static about page.
* `app.run(debug=True)` – starts the development server (auto-reloads on code change).

---
## 7. `src/train_models.py` – training and comparing

**Top of the file.** The `os.environ[...]` and `warnings.filterwarnings(...)` lines hide a harmless deprecation warning from scikit-learn. Then the imports: `joblib` (saving), `matplotlib` (with `Agg` = draw to files only), pandas/numpy, the four model classes, the metric functions, `GridSearchCV` (tries parameter combinations), `StratifiedKFold`, `cross_val_score`, `train_test_split`, `Pipeline`.

**`candidates()`** returns a dictionary: model name → (empty model, grid of settings to try). The `clf__C` notation means "the parameter `C` of the step named `clf` in the pipeline". For the SVM we try 5 values of `C` and 5 of `gamma` (25 combinations).

**`decision_boundary_figure`** trains a small extra SVM that only sees soil moisture and temperature so that its decision regions can be drawn in 2-D: `np.meshgrid` builds a grid of points over the plot, `svm.predict` colours each grid point by class, `contourf` fills the regions, `scatter` draws sample days on top.

**`main()` step by step**
1. `df = pd.read_csv(config.CLEAN_CSV)` – load clean data.
2. `X` = the 5 input columns, `y` = the label.
3. `train_test_split(..., test_size=0.2, stratify=y, random_state=42)` – 80 % to learn, 20 % locked away for the final exam; `stratify` keeps the same yes/no ratio in both.
4. `cv = StratifiedKFold(5, shuffle=True, ...)` – the rule for 5-fold cross-validation.
5. Loop `for name, (clf, grid) in candidates().items():`
   - `pipe = Pipeline([("prep", make_preprocessor()), ("clf", clf)])` – scaling + model in one object.
   - `GridSearchCV(pipe, grid, cv=cv, scoring="f1", n_jobs=-1).fit(X_train, y_train)` – try every setting, score each by 5-fold F1 on training data, keep the best (`n_jobs=-1` uses all CPU cores).
   - `model = search.best_estimator_` – the winner, already re-trained on all training data.
   - `pred = model.predict(X_test)`; `proba = model.predict_proba(X_test)[:, 1]` – answers and probabilities on the locked-away data.
   - Compute accuracy, precision, recall, F1, ROC-AUC, the cross-validation F1 mean/std and training time; store them in `row` and the model/confusion matrix/ROC points in dictionaries; print one summary line.
6. `table = pd.DataFrame(results)` and `to_csv` – save the comparison table.
7. **Figures:** confusion matrices (2×2 grid, numbers written inside the squares), grouped bar chart of the four metrics, ROC curves (with the diagonal "random" line), Random Forest feature importance.
8. `best_name = table.sort_values(["F1-score","Accuracy"], ascending=False).iloc[0]["Model"]` – sort by F1, then accuracy, and take the top model's name.
9. `joblib.dump(fitted["SVM"], ...)` saves the SVM (used by the web app); `joblib.dump(fitted[best_name], ...)` saves the numerically best model.
10. Build the dictionary `out` and write it as `metrics.json` (the report, slides and web page all read this file so every number matches).

---
## 8. Plotting scripts (explained by figure)

**`eda.py`** – `main()` loads the raw csv and prints `describe()` statistics; draws (1) bar chart of missing values per column; calls `clean_data` and saves the clean csv; then (2) class-balance bars, (3) histograms of each feature split by class, (4) box plots (middle line = median, box = middle 50 %), (5) correlation heat-map (`corr()` gives −1…+1; `imshow` colours it), (6) scatter of soil moisture vs temperature, (7) bar of irrigation rate per crop (`groupby().mean()`), (8) irrigation rate per rainfall band (`pd.cut` sorts rainfall into bands). Each figure uses the same pattern: `plt.subplots` (canvas) → draw → title/labels → `save()` (`tight_layout` then `savefig`, then `plt.close` to free memory). Finally the summary numbers go to `eda_summary.json`.

**`energy_analysis.py`** – recreates the same 20 % test split, asks the SVM for a decision for each test day, runs `energy.estimate` for each, and stores the results in a DataFrame `e`. It then takes averages (`mean`), the share of days cheaper/costlier than the timer, a 30-day projection, draws a 2-bar chart and a histogram with the timer value as a dashed line, and writes `energy_summary.json`.

**`diagrams.py`** – helper `box()` draws a rounded coloured rectangle with text, `arrow()` draws an arrow, `canvas()` makes an empty drawing area. `architecture()`, `pipeline()`, `flowchart()` and `svm_concept()` place boxes and arrows at fixed coordinates to draw the block diagram, ML pipeline, flowchart (a `Polygon` makes the diamond decision shape) and the SVM margin picture.

---
## 9. HTML / CSS

* `templates/base.html` – common page frame: loads Bootstrap CSS/JS from a CDN, the navigation bar, and `{% block content %}{% endblock %}` where each page puts its own content. `url_for('static', filename=...)` builds the correct file link.
* `templates/index.html` – `{% extends "base.html" %}` inherits the frame. `{{ form.temperature }}` prints a variable; `{% if result %}…{% else %}…{% endif %}` shows the result cards only after a prediction; `{% for e in errors %}` prints each error; `{% for c in crops %}` builds the crop `<option>` list. Bootstrap classes (`row`, `col-lg-5`, `card`, `btn btn-success`) give the responsive grid and styling.
* `templates/results.html` – loops over `metrics.models.items()` to build the comparison table and shows the saved figures.
* `static/css/style.css` – green colour variables (`:root`), gradient navigation bar, striped "crop rows" hero background, hover animation on cards, and a small pop-in animation for the result banner.

---
## 10. `tests/test_app.py`
`unittest` runs each method whose name starts with `test_`. `self.assertTrue/Equal/In` stop with an error if the statement is false. The tests check: a dry hot field → pump ON; a wet field → pump OFF with the full timer energy saved; validation catches bad numbers; the energy is never negative; rain reduces water; all pages return HTTP 200; the form and the JSON API work, and bad input is rejected.
