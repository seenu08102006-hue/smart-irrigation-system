"""
build_report.py - generates docs/Project_Report.docx (IEEE-style final-year project report).
All numbers in the Results chapter are read from reports/*.json, so the text always matches the code.

Run (after the ML scripts):  python docs/build_report.py
"""
import json
import os

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from report_lib import Report, config

ROOT = config.ROOT
M = json.load(open(config.METRICS_JSON))
EDA = json.load(open(os.path.join(config.REPORT_DIR, "eda_summary.json")))
EN = json.load(open(os.path.join(config.REPORT_DIR, "energy_summary.json")))
MD = M["models"]
pc = lambda v: f"{100 * v:.2f}%"          # noqa: E731
svm = MD["SVM"]
cl = EDA["cleaning"]
cm = M["confusion_matrices"]["SVM"]

R = Report()
d = R.doc

# =============================================================== TITLE PAGE
for _ in range(3):
    d.add_paragraph()
t = R.p("A PROJECT REPORT ON", align="center", size=13)
t = d.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("SMART IRRIGATION USING SUPPORT VECTOR MACHINE (SVM) AND ELECTRICAL OPTIMIZATION")
r.bold = True; r.font.size = Pt(22)
R.p("Submitted in partial fulfilment of the requirements for the award of the degree of", align="center")
R.p("BACHELOR OF ENGINEERING / TECHNOLOGY", align="center", size=14).runs[0].bold = True
d.add_paragraph()
R.p("Submitted by", align="center")
for line in ["[Student Name 1]  -  [Register No.]", "[Student Name 2]  -  [Register No.]", "[Student Name 3]  -  [Register No.]"]:
    R.p(line, align="center")
d.add_paragraph()
R.p("Under the guidance of", align="center")
R.p("[Guide Name], [Designation]", align="center")
d.add_paragraph()
R.p("Department of [Department Name]\n[College / University Name]\nAcademic Year [20XX - 20XX]", align="center", size=12)
R.page_break()

# =============================================================== ABSTRACT
R.h1("Abstract", numbered=False)
R.p(
    "Agriculture consumes the largest share of fresh water, and a considerable part of the electrical energy used on "
    "farms goes into pumping that water. Conventional irrigation controllers switch the pump on a fixed timer and "
    "ignore the real condition of the crop, so water and electricity are wasted on days when the soil is already "
    "wet and the crop is under-watered on hot, dry days. This report presents a complete machine-learning based "
    "irrigation advisory system that decides, from four easily measured quantities - temperature, humidity, soil "
    "moisture and rainfall - together with the crop type, whether irrigation is required. A Support Vector Machine "
    "(SVM) with a radial-basis-function kernel is the core classifier. An electrical-optimisation module then "
    "converts the decision into pump ON/OFF status, the volume of water to deliver, the pump run-time and the "
    "electrical energy used and saved with respect to a fixed two-hour daily timer.")
R.p(
    f"Because no public dataset with exactly these attributes was available, a synthetic dataset of 5,000 days was "
    f"generated from agronomic rules with non-linear heat, humidity and rainfall effects and random sensor noise; the "
    f"raw file was deliberately corrupted with missing values, duplicates and impossible readings so that data "
    f"cleaning could be demonstrated. After cleaning, exploratory analysis, feature scaling and a stratified 80/20 split, "
    f"four classifiers - SVM, Decision Tree, Random Forest and Logistic Regression - were tuned with five-fold grid search "
    f"and compared on the unseen test set. The SVM achieved an accuracy of {pc(svm['Accuracy'])}, precision of "
    f"{pc(svm['Precision'])}, recall of {pc(svm['Recall'])}, F1-score of {pc(svm['F1-score'])} and ROC-AUC of "
    f"{svm['ROC-AUC']:.3f}, the best F1-score of the four models, although its margin over Logistic Regression is small. "
    f"In simulation on the test days, the smart controller used {EN['smart_kwh_per_day']} kWh per day against "
    f"{EN['timer_kwh_per_day']} kWh for the timer, an average saving of {EN['saving_percent']}%. The trained model is "
    f"stored with Joblib and served through a Flask web application with a Bootstrap interface. The results are "
    f"obtained on synthetic data and therefore demonstrate the methodology; validation on real field data is the "
    f"principal direction for future work.")
R.p("Support vector machine, smart irrigation, machine learning, electrical optimisation, pump energy, Flask, scikit-learn.",
    bold_lead="Index Terms-", italic=True)
R.page_break()

R.h1("Table of Contents", numbered=False)
R.toc()
R.page_break()

# =============================================================== I. INTRODUCTION
R.h1("Introduction")
R.h2("Background")
R.p("Water is the most critical input of agriculture. Irrigated land produces a disproportionate share of the world's "
    "food, yet it also accounts for the largest fraction of fresh-water withdrawals. In many regions water is pumped "
    "from wells or canals by electric motors, so every litre wasted also wastes electrical energy, increases the "
    "farmer's bill and, where the grid is carbon-intensive, increases emissions. Improving the efficiency of "
    "irrigation therefore has a double benefit: it conserves water and it conserves energy.")
R.p("The simplest controllers are manual or timer based. A timer switches the pump on at a fixed hour and off after a fixed "
    "duration, regardless of whether it rained during the night or whether a heat wave has dried the soil. More "
    "advanced controllers compare the soil-moisture reading with a fixed threshold. Although better, a single "
    "threshold ignores the interaction between the factors that govern crop water demand - temperature raises "
    "evaporation, humid air slows it down, rain refills the soil, and different crops need different moisture levels. "
    "Data-driven classifiers can learn these interactions automatically from examples.")
R.h2("Motivation")
R.p("Support Vector Machines are well suited to this decision. They work with a modest number of samples, give a "
    "smooth, well-regularised decision boundary, handle non-linear relationships through kernels and are compact "
    "enough to run on a low-cost computer or an embedded board. Combining such a classifier with an explicit "
    "electrical model of the pump allows the benefit of every decision to be quantified in kilowatt-hours, which is "
    "the figure that matters to a farmer and to an electrical-engineering project.")
R.h2("Scope of the Work")
R.p("This project builds an end-to-end pipeline: data generation, cleaning, exploratory analysis, preprocessing, "
    "model training and comparison, model persistence, an electrical-optimisation module and a web application. "
    "The scope is a software prototype. The pump is represented by a numerical model (1.5 kW motor, 3,000 L/h), "
    "and actuation of a real relay is described as future work rather than implemented.")
R.h2("Organisation of the Report")
R.p("Section II surveys related approaches, Section III states the problem and Section IV lists the objectives. "
    "Section V describes the methodology, Section VI the system architecture and Section VII the algorithms. Section "
    "VIII describes the dataset, Section IX the implementation, Section X presents and discusses results, and "
    "Sections XI and XII give the conclusion and future scope. The complete source code is listed in the Appendix.")

# =============================================================== II. LITERATURE SURVEY
R.h1("Literature Survey")
R.h2("Irrigation Scheduling Approaches")
R.p("Irrigation scheduling methods can be grouped into four families. Calendar or timer scheduling applies a fixed "
    "amount at fixed intervals. Threshold (or on-off) control opens the valve when a soil-moisture sensor falls below a "
    "set value. Model-based scheduling estimates the crop's water requirement from weather data using "
    "evapotranspiration equations such as those standardised in FAO Irrigation and Drainage Paper 56 [8]. "
    "Finally, learning-based scheduling uses statistical or machine-learning models trained on historical "
    "observations. Table I summarises the characteristics of the four families.")
R.table(["Approach", "Inputs used", "Adapts to weather", "Needs training data", "Typical weakness"],
        [["Timer / calendar", "Clock only", "No", "No", "Waters wet soil, under-waters hot days"],
         ["Threshold on-off", "Soil moisture", "Partly", "No", "Ignores heat, humidity, rain, crop"],
         ["Evapotranspiration model [8]", "Weather + crop coefficients", "Yes", "No (needs calibration)", "Many parameters to measure"],
         ["Machine learning (this work)", "Sensors + crop", "Yes", "Yes", "Quality depends on data"]],
        "Comparison of irrigation scheduling approaches", widths=[3.6, 3.4, 2.6, 3.0, 4.2])
R.h2("Support Vector Machines")
R.p("The Support Vector Machine was introduced by Cortes and Vapnik as the support-vector network [1], building on the "
    "optimal-margin training algorithm of Boser, Guyon and Vapnik [2]. The classifier chooses, among all separating "
    "hyperplanes, the one with the largest margin to the nearest training points, which gives strong generalisation "
    "guarantees. The kernel trick lets the same algorithm learn non-linear boundaries by implicitly mapping the data to "
    "a higher-dimensional space [1], [16]. Practical guidance on scaling the inputs and tuning the penalty C and kernel "
    "width gamma is given by Hsu et al. [13], and the widely used LIBSVM library [3] underlies the scikit-learn "
    "implementation [4] used in this project. Platt scaling [14] converts SVM scores into class probabilities, "
    "which we use as a confidence value in the web application.")
R.h2("Comparison Algorithms")
R.p("Three well-known classifiers are used as baselines. Decision trees, formalised as classification and regression "
    "trees (CART) [6], are easily interpreted but can over-fit. Random forests [5] average many randomised trees "
    "to reduce variance. Logistic regression [7] models the log-odds of the class as a linear function of the inputs and "
    "is a standard, fast and interpretable benchmark. Comparing against these baselines shows whether the added "
    "complexity of an SVM is justified.")
R.h2("Evaluation Methodology")
R.p("Classifiers are evaluated with accuracy, precision, recall, F1-score and the confusion matrix [16]. For "
    "threshold-independent comparison the receiver operating characteristic (ROC) curve and its area (AUC) are used [12]. "
    "Hyper-parameters are selected by k-fold cross-validation on training data only, and the final numbers are reported on a "
    "held-out test set, which is the accepted way to avoid an optimistic bias [16].")
R.h2("Research Gap")
R.p("Irrigation-advisory prototypes commonly report a classification accuracy but stop short of translating the "
    "decision into the electrical quantities that determine cost. This project closes that gap by pairing the "
    "classifier with an explicit pump-energy model and by reporting both the model comparison and the energy saving "
    "from the same test set. It also states clearly where the data is synthetic, so that the reported numbers are "
    "not mistaken for field measurements.")

# =============================================================== III. PROBLEM STATEMENT
R.h1("Problem Statement")
R.p("Given the temperature (degrees Celsius), relative humidity (%), soil moisture (%) and rainfall (mm) observed on a given "
    "day, and optionally the crop type, develop a classifier that predicts whether the crop must be irrigated that day. "
    "For the predicted decision, estimate the pump status, the volume of water required and the electrical energy "
    "consumed and saved relative to a conventional fixed-timer system, and make the result available to a non-expert "
    "user through a web interface.")
R.p("Formally, let x = (T, H, S, Rf, c) be the observation and y in {0, 1} the irrigation label. The task is to learn a function "
    "f: x -> y that minimises classification error, followed by a deterministic mapping g(f(x), x) -> (litres, hours, kWh).")

# =============================================================== IV. OBJECTIVES
R.h1("Objectives")
R.numbered([
    "To generate and document an irrigation dataset containing temperature, humidity, soil moisture, rainfall, crop type and an irrigation-needed label.",
    "To clean the data, handle missing values, scale the features and explore it through statistics and visualisation.",
    "To train a Support Vector Machine classifier and tune its hyper-parameters.",
    "To compare the SVM with Decision Tree, Random Forest and Logistic Regression using accuracy, precision, recall, F1-score, ROC-AUC and confusion matrices.",
    "To save the trained model with Joblib so that it can be reused without retraining.",
    "To develop an electrical-optimisation module that estimates pump run-time, electricity consumption and electricity saving.",
    "To build a Flask web application with a professional Bootstrap interface that returns the irrigation decision, pump status and energy figures.",
    "To document the system fully so that it can be reproduced, evaluated and extended.",
])

# =============================================================== V. METHODOLOGY
R.h1("Methodology")
R.p("The work follows the standard machine-learning workflow shown in Fig. 1: data acquisition, cleaning, "
    "exploration, preprocessing, model training, evaluation, persistence and deployment. Every step is "
    "implemented as a separate, re-runnable Python script so that the whole study is reproducible from a "
    "fixed random seed (42).")
R.figure("21_ml_pipeline.png", "Machine-learning pipeline followed in this project.", 16)
R.h2("Data Acquisition (Synthetic Generation)")
R.p("A literature and repository search did not yield an open dataset that combines temperature, humidity, soil moisture, "
    "rainfall, crop type and a binary irrigation label in one table. The dataset was therefore generated "
    "(src/generate_dataset.py). Temperature, humidity and soil moisture are drawn from normal distributions and "
    "clipped to physical limits, with humidity made slightly lower on hotter days. Rain occurs on about 30% of days "
    "with a gamma-distributed depth. For each crop a soil-moisture threshold is defined (Table III). The label is then "
    "obtained from a water-stress score:")
R.equation("score = 0.12(θc − S) + 0.004(T − 25)|T − 25| − 0.025(H − 60)(T/30) − 1.6(1 − e^(−Rf/15)) + ε", 1)
R.p("where θc is the crop threshold, S the soil moisture, T the temperature, H the humidity, Rf the rainfall and ε ~ N(0, 0.55²) "
    "is noise representing sensor error and local variation. Irrigation is needed when the score is positive. "
    "The terms reflect agronomy: a drier soil raises the need; evaporation grows faster than linearly with "
    "temperature; low humidity matters more on hot days; and the benefit of rain saturates. Because the score is "
    "non-linear, simple linear models are not given an unfair advantage.")
R.h2("Data Cleaning and Missing Values")
R.p(f"The raw file contains {cl['rows_before']} rows with injected faults. Cleaning (src/preprocess.py) performs: (1) removal of "
    f"{cl['duplicates_removed']} duplicate rows; (2) conversion of sensor columns to numbers; (3) replacement of impossible "
    f"readings (temperature above 55 C, negative soil moisture) by missing values; (4) filling the {cl['missing_before_fill']} "
    f"missing sensor values with the median of the same crop, a statistic that is robust to outliers; and (5) deletion of rows "
    f"lacking a label or crop. After cleaning {cl['rows_after']} rows remain and no missing values are left.")
R.h2("Exploratory Data Analysis")
R.p("Exploratory analysis (src/eda.py) was used to understand class balance, feature distributions, "
    "relationships between variables and differences between crops. The findings are presented in Section X.")
R.h2("Feature Scaling and Encoding")
R.p("SVMs and logistic regression are sensitive to the numerical range of features: a variable measured in the range 0-300 (rainfall) "
    "would dominate one in the range 0-1. The four sensor features are therefore standardised, z = (x − μ)/σ, "
    "and the crop name is one-hot encoded. Both operations are placed inside a scikit-learn Pipeline together with "
    "the classifier. Consequently μ and σ are computed from the training folds only, which prevents information from "
    "the test set leaking into training.")
R.h2("Train/Test Split and Hyper-parameter Tuning")
R.p(f"The cleaned data is split 80%/20% with stratification, giving {M['train_rows']} training and {M['test_rows']} test samples. "
    "Each model is tuned with five-fold stratified cross-validation (GridSearchCV, scoring = F1) on the training set only. "
    "The grids are listed in Table II. The test set is touched exactly once, to produce the final figures.")
R.table(["Model", "Hyper-parameter grid", "Selected values"],
        [["SVM (RBF)", "C in {0.5, 1, 5, 10, 50}; gamma in {scale, 0.02, 0.05, 0.1, 0.3}", str(svm["Best params"])],
         ["Decision Tree", "max_depth in {3, 5, 8, 12, None}; min_samples_leaf in {1, 5, 20}", str(MD["Decision Tree"]["Best params"])],
         ["Random Forest", "n_estimators in {100, 200}; max_depth in {6, 12, None}", str(MD["Random Forest"]["Best params"])],
         ["Logistic Regression", "C in {0.01, 0.1, 1, 10, 100}", str(MD["Logistic Regression"]["Best params"])]],
        "Hyper-parameter search space and selected values", widths=[3.2, 8.2, 5.4])
R.h2("Evaluation Metrics")
R.p("With the positive class defined as 'irrigation needed', TP, TN, FP and FN denote the counts of the confusion matrix.")
R.equation("Accuracy = (TP + TN) / (TP + TN + FP + FN)", 2)
R.equation("Precision = TP / (TP + FP)", 3)
R.equation("Recall = TP / (TP + FN)", 4)
R.equation("F1 = 2 · Precision · Recall / (Precision + Recall)", 5)
R.p("A false negative means a thirsty crop is not watered, which harms yield; a false positive means water and energy are wasted. "
    "Recall therefore protects the crop, precision protects the resources, and F1 balances both.")
R.h2("Electrical Optimisation Model")
R.p("The electrical model converts the classifier's decision into physical quantities. When irrigation is required, the "
    "water volume is the soil-moisture deficit multiplied by a litres-per-percent constant, scaled by the crop's relative "
    "water demand and a heat factor, minus the water supplied by rainfall:")
R.equation("V = [(θc + 15 − S) · 300 · wc · (1 + 0.02·max(T − 30, 0))] − 100·Rf,   500 ≤ V ≤ 1.5·Vtimer", 6)
R.equation("t = V / Q,    E = P · t,    Etimer = P · ttimer,    Esaved = max(Etimer − E, 0)", 7)
R.p("Here wc is the crop water factor, Q = 3,000 L/h is the pump discharge, P = 1.5 kW is the motor power and ttimer = 2 h is the "
    "run-time of the conventional timer, giving Etimer = 3.0 kWh per day. If the SVM predicts that no irrigation is needed, "
    "V = 0, E = 0 and the whole timer energy is saved. These constants are assumptions chosen for a 100 m² plot; they are "
    "isolated in src/config.py so they can be replaced with the parameters of a real installation.")
R.table(["Crop", "Moisture threshold (%)", "Water factor"],
        [[k, v["threshold"], v["water_factor"]] for k, v in config.CROPS.items()],
        "Crop parameters used for data generation and water estimation", widths=[4, 5, 4])

# =============================================================== VI. SYSTEM ARCHITECTURE
R.h1("System Architecture")
R.p("The system is organised into five layers, shown in Fig. 2. Field sensors provide the readings; the "
    "preprocessing layer validates and scales them; the SVM classifier predicts the irrigation need; the "
    "electrical-optimisation module computes the pump control and the energy figures; and the Flask web "
    "application presents the output to the user and can forward the ON/OFF command to a relay.")
R.figure("20_system_architecture.png", "System architecture of the proposed smart irrigation system.", 16)
R.h2("Functional Modules")
R.table(["Module", "File", "Responsibility"],
        [["Configuration", "src/config.py", "Paths, valid ranges, crop and pump constants"],
         ["Dataset generator", "src/generate_dataset.py", "Creates the raw synthetic dataset"],
         ["Preprocessing", "src/preprocess.py", "Cleaning, imputation, scaling and encoding"],
         ["EDA", "src/eda.py", "Statistics and eight visualisations"],
         ["Training", "src/train_models.py", "Tunes, compares and saves the models"],
         ["Energy model", "src/energy.py", "Water volume, pump hours, kWh used and saved"],
         ["Prediction", "src/predict.py", "Loads the Joblib model, returns the decision"],
         ["Web application", "app.py + templates/", "Flask routes and Bootstrap pages"]],
        "Software modules of the system", widths=[3.4, 4.6, 8.8])
R.h2("Control Flow")
R.p("Fig. 3 shows the flow of one decision. The inputs are validated against physical ranges; invalid inputs are rejected "
    "with a message instead of being passed to the model. The SVM then predicts the class, and the pump branch computes either the "
    "water volume and run-time or a zero-energy OFF state.")
R.figure("22_flowchart.png", "Flowchart of the irrigation decision and pump control.", 8.2)
R.h2("Web Application and API")
R.p("The Flask application exposes four pages (prediction form, model results, about) and a JSON endpoint, "
    "POST /api/predict, which accepts the four readings and the crop and returns the prediction, pump status, "
    "water volume, run-time, energy used, energy saved and confidence. The same endpoint could be called by a "
    "microcontroller such as an ESP32 or Raspberry Pi to automate the pump. The interface is written in HTML, CSS and "
    "Bootstrap 5 with a green-and-white theme and is responsive down to mobile width.")

# =============================================================== VII. ALGORITHMS
R.h1("Algorithms")
R.h2("Support Vector Machine")
R.figure("23_svm_concept.png", "Maximum-margin hyperplane of an SVM (conceptual).", 8.5)
R.p("For training samples (xi, yi) with yi in {−1, +1}, a linear SVM seeks the hyperplane w·x + b = 0 that "
    "separates the classes with the largest margin 2/||w||. For data that are not perfectly separable, slack "
    "variables ξi are introduced (soft margin):")
R.equation("minimise  ½||w||² + C Σ ξi   subject to   yi (w·xi + b) ≥ 1 − ξi,  ξi ≥ 0", 8)
R.p("The parameter C controls the trade-off: a large C punishes training errors heavily and gives a narrow margin, "
    "while a small C accepts some errors for a wider margin. Solving the dual problem expresses the decision "
    "function using only the support vectors, the training points on or inside the margin:")
R.equation("f(x) = sign( Σ αi yi K(xi, x) + b )", 9)
R.p("The kernel K computes an inner product in a feature space without constructing it explicitly. This project uses the "
    "radial-basis-function (RBF) kernel:")
R.equation("K(xi, x) = exp( −γ ||xi − x||² )", 10)
R.p("where γ sets how far the influence of a single training point reaches: a large γ gives a wiggly boundary that may over-fit, a small γ a "
    "smooth one. Both C and γ are selected by grid search. Class probabilities are obtained with Platt scaling [14] and "
    "are used as the 'confidence' value shown to the user; they should be read as the model's own estimate and not as a guarantee.")
R.h3("Pseudocode - training and deployment")
R.code("""1.  Load raw data D
2.  D <- clean(D)                      # duplicates, invalid values, median imputation
3.  Split D into train (80 %) and test (20 %), stratified by label
4.  Build pipeline P = [StandardScaler + OneHotEncoder] -> SVC(kernel = RBF)
5.  for C in grid_C, for gamma in grid_gamma:
6.      score <- mean F1 over 5-fold cross-validation of P on train
7.  Choose (C*, gamma*) with the best score; refit P on all training data
8.  Evaluate P on test: accuracy, precision, recall, F1, confusion matrix
9.  Save P with joblib.dump
10. At run time: load P; x <- validated sensor readings
11. y <- P.predict(x); if y = 1 then compute litres, hours, kWh else pump OFF""", size=9)
R.h2("Decision Tree")
R.p("A decision tree recursively splits the data on the feature and threshold that most reduce the Gini impurity "
    "G = 1 − Σ pk², where pk is the proportion of class k in a node. It is easy to explain, but an unrestricted tree "
    "memorises noise, so max_depth and min_samples_leaf are tuned.")
R.h2("Random Forest")
R.p("A random forest trains many trees on bootstrap samples of the data, each split considering only a random subset of "
    "features, and predicts by majority vote. Averaging decorrelated trees reduces variance and normally outperforms a single tree [5].")
R.h2("Logistic Regression")
R.p("Logistic regression estimates P(y = 1 | x) = 1/(1 + e^−(w·x + b)) by maximising the likelihood. Its decision boundary is a "
    "hyperplane in the scaled feature space; it is fast, interpretable and a strong baseline when the classes are close "
    "to linearly separable [7].")
R.h2("Why the SVM Was Selected")
R.p("The SVM is selected as the project's classifier for the following reasons, supported by Section X:")
R.bullets([
    ("Best measured F1-score and ROC-AUC.", f"On the test set the SVM obtained F1 = {pc(svm['F1-score'])} and AUC = {svm['ROC-AUC']:.3f}, the highest among the four models, with the highest recall among the four models."),
    ("Handles non-linear interactions.", "The RBF kernel models the heat-humidity-rain interactions without manual feature engineering."),
    ("Robust to noise.", "The soft-margin parameter C explicitly trades training errors for a wider margin, which suits noisy sensor data."),
    ("Compact and fast at prediction time.", "Only the support vectors are stored, so inference is quick enough for a low-cost controller."),
    ("Probability output.", "Platt scaling [14] gives a confidence score for display."),
])
R.p(f"An honest reading of the numbers is needed: the SVM's F1 advantage over Logistic Regression is "
    f"{100 * (svm['F1-score'] - MD['Logistic Regression']['F1-score']):.2f} percentage points, which is smaller than "
    f"the cross-validation standard deviation ({svm['CV F1 (std)']:.3f}). The result therefore shows that the SVM is at "
    f"least as good as the other models on this data, not that it is decisively superior. The non-linear structure of the "
    f"data is the reason an RBF-kernel SVM is expected to do at least as well as a linear model.")

# =============================================================== VIII. DATASET
R.h1("Dataset Description")
R.p("The dataset has six attributes and, after cleaning, 5,000 records. Its provenance is synthetic and it is generated by "
    "src/generate_dataset.py, so the reader can recreate it exactly. Table V lists the attributes.")
R.table(["Attribute", "Type", "Unit", "Valid range", "Description"],
        [["temperature", "Numeric", "°C", "0 - 55", "Air temperature at the field"],
         ["humidity", "Numeric", "%", "0 - 100", "Relative humidity of the air"],
         ["soil_moisture", "Numeric", "%", "0 - 100", "Volumetric soil-moisture percentage"],
         ["rainfall", "Numeric", "mm", "0 - 300", "Rain received during the day"],
         ["crop_type", "Categorical", "-", "5 crops", "Rice, Sugarcane, Maize, Cotton, Wheat"],
         ["irrigation_needed", "Binary (target)", "-", "0 / 1", "1 = irrigation required (Yes), 0 = not required (No)"]],
        "Attributes of the irrigation dataset", widths=[3.2, 2.6, 1.5, 2.4, 7.2])
desc = EDA["describe"]
R.table(["Feature", "Mean", "Std", "Min", "25%", "Median", "75%", "Max"],
        [[k.replace("_", " "), desc[k]["mean"], desc[k]["std"], desc[k]["min"], desc[k]["25%"], desc[k]["50%"], desc[k]["75%"], desc[k]["max"]]
         for k in config.NUMERIC_FEATURES],
        "Descriptive statistics of the cleaned data (5,000 rows)", widths=[3.2, 1.8, 1.8, 1.8, 1.8, 2, 1.8, 1.8])
R.table(["Cleaning step", "Result"],
        [["Rows in raw file", cl["rows_before"]], ["Duplicate rows removed", cl["duplicates_removed"]],
         ["Missing / invalid sensor values filled (crop-wise median)", cl["missing_before_fill"]],
         ["Rows in cleaned file", cl["rows_after"]], ["Missing values remaining", cl["missing_after_fill"]]],
        "Data-cleaning summary", widths=[10, 4])
cc = EDA["class_counts"]
R.p(f"The target is well balanced: {cc['0']} days (not required) and {cc['1']} days (required), so accuracy is a meaningful metric and no "
    f"re-sampling is needed. Because the data is synthetic, every conclusion about absolute accuracy applies to this generator only.")

# =============================================================== IX. IMPLEMENTATION
R.h1("Implementation")
R.h2("Tools and Libraries")
R.table(["Library / tool", "Use in the project"],
        [["Python 3", "Programming language"], ["Pandas [11]", "Tables, cleaning, CSV input/output"],
         ["NumPy [10]", "Random generation, numerical operations"], ["Scikit-learn [4]", "Pipelines, SVM, tree, forest, logistic regression, metrics"],
         ["Matplotlib [9]", "All graphs and block diagrams"], ["Joblib", "Saving and loading the trained model"],
         ["Flask [15]", "Web server and JSON API"], ["Bootstrap 5, HTML, CSS", "Responsive user interface"]],
        "Technology stack", widths=[5, 11.4])
R.h2("Project Structure")
R.code("""smart_irrigation_svm/
  app.py                    Flask application
  requirements.txt
  run_all.py                runs the whole pipeline in order
  src/    config.py  generate_dataset.py  preprocess.py  eda.py
          train_models.py  energy.py  energy_analysis.py  predict.py  diagrams.py
  templates/  base.html  index.html  results.html  about.html
  static/     css/style.css   figures/*.png
  data/       irrigation_raw.csv  irrigation_clean.csv
  models/     svm_model.joblib  best_model.joblib
  reports/    metrics.json  model_comparison.csv  eda_summary.json  energy_summary.json
  docs/       report, slides, viva questions, code explanation""", size=9)
R.h2("User Interface")
R.p("The home page contains a form with four numeric fields (temperature, humidity, soil moisture, rainfall) and a crop drop-down. HTML5 "
    "attributes limit the ranges in the browser, and the server validates again because browser checks can be bypassed. "
    "After the user presses Predict, a coloured banner shows 'Irrigation Required' or 'Irrigation Not Required', the "
    "pump status, the confidence, and cards for estimated electricity consumption, estimated electricity "
    "savings, water required and pump run-time. The Model Results page shows the comparison table and graphs, "
    "and the About page explains the system.")
R.h2("Persistence with Joblib")
R.p("After training, the complete Pipeline - scaler, encoder and SVM - is saved with joblib.dump. Saving the whole "
    "pipeline is important because the web application must scale new inputs with the same mean and standard "
    "deviation that were learned in training. At start-up, predict.py loads the file once and re-uses it for every request.")
R.h2("Testing")
R.bullets([
    "Unit-style checks of src/predict.py with a dry-soil and a wet-soil scenario (Table XI).",
    "Flask test-client requests to every page and to /api/predict, including invalid input.",
    "Input validation tests: out-of-range temperature, text instead of numbers and an unknown crop are all rejected.",
])

# =============================================================== X. RESULTS
R.h1("Results and Discussion")
R.h2("Exploratory Data Analysis")
R.figure("01_missing_values.png", "Missing values per sensor column in the raw dataset.", 9)
R.figure("02_class_balance.png", "Class distribution of the target variable.", 8)
R.p("Fig. 5 shows that about 2% of each sensor column was missing before cleaning, and Fig. 6 shows that the two classes are "
    "nearly balanced, so accuracy is a fair metric.")
R.figure("03_feature_histograms.png", "Feature distributions for the two classes.", 14.5)
R.p("Soil moisture shows the clearest separation: days that need irrigation concentrate at low moisture values. Temperature "
    "shifts the 'needed' class to the right, while rainfall is nearly always zero on days that need irrigation.")
R.figure("04_boxplots.png", "Box plots of each feature by irrigation need.", 15.5)
R.figure("05_correlation_heatmap.png", "Correlation matrix of numeric features and the target.", 10)
ct = EDA["correlation_with_target"]
R.p(f"The correlation of soil moisture with the target is {ct['soil_moisture']:.2f} (strong, negative), temperature {ct['temperature']:.2f}, "
    f"humidity {ct['humidity']:.2f} and rainfall {ct['rainfall']:.2f}. The correlation between humidity and temperature is negative by "
    f"construction of the generator, as it is in many climates.")
R.figure("06_scatter_soil_temp.png", "Soil moisture versus temperature, coloured by class.", 11)
R.p("The scatter plot reveals a diagonal, curved boundary: the soil-moisture level at which irrigation becomes necessary rises with temperature. "
    "A single fixed soil-moisture threshold cannot represent this, which motivates a learned classifier.")
R.figure("07_crop_irrigation_rate.png", "Share of days that need irrigation for each crop.", 10)
R.figure("08_rainfall_effect.png", "Effect of rainfall on irrigation need.", 9.5)
R.h2("Model Comparison")
R.table(["Model", "Accuracy", "Precision", "Recall", "F1-score", "ROC-AUC", "CV F1 (mean ± std)"],
        [[n, pc(m["Accuracy"]), pc(m["Precision"]), pc(m["Recall"]), pc(m["F1-score"]), f"{m['ROC-AUC']:.3f}",
          f"{m['CV F1 (mean)']:.3f} ± {m['CV F1 (std)']:.3f}"] for n, m in MD.items()],
        "Performance of the four classifiers on the 1,000-sample test set", widths=[3.6, 2.1, 2.1, 2.0, 2.1, 2.0, 3.4])
R.figure("11_model_comparison.png", "Comparison of accuracy, precision, recall and F1-score.", 14)
best = M["best_model_by_f1"]
R.p(f"Table IX shows that {best} achieves the highest F1-score ({pc(MD[best]['F1-score'])}). The Random Forest and Logistic Regression are close "
    f"behind, and the single Decision Tree is clearly weaker ({pc(MD['Decision Tree']['F1-score'])}) because a single tree "
    f"approximates the curved boundary with axis-parallel steps. The spread between SVM, Logistic Regression and Random Forest is within about "
    f"{100 * (svm['F1-score'] - MD['Random Forest']['F1-score']):.1f} percentage points, similar to the fold-to-fold variation, so "
    f"these three should be regarded as comparable with a slight edge to the SVM.")
R.h2("Confusion Matrices")
R.figure("09_confusion_matrices.png", "Confusion matrices of the four models on the test set.", 12)
R.p(f"For the SVM, TN = {cm[0][0]}, FP = {cm[0][1]}, FN = {cm[1][0]} and TP = {cm[1][1]}. The SVM missed {cm[1][0]} days that needed "
    f"irrigation (false negatives) and triggered {cm[0][1]} unnecessary irrigations (false positives). Its recall is higher than its precision, "
    f"which is the preferable direction for a farm because an unnecessary cycle costs water and energy while a missed cycle can cost yield.")
R.h2("ROC Analysis")
R.figure("12_roc_curves.png", "ROC curves of the four classifiers.", 10)
R.p("All models lie well above the diagonal chance line. The SVM and Logistic Regression curves almost overlap, while the Decision "
    "Tree curve is lowest, meaning it ranks days by irrigation need less reliably.")
R.h2("SVM Decision Regions and Feature Importance")
R.figure("10_svm_decision_boundary.png", "Decision regions of an RBF SVM trained on soil moisture and temperature only.", 11)
R.p("Fig. 16 is a two-dimensional illustration obtained by training a separate SVM on two features. The boundary is a smooth "
    "curve that moves toward higher soil moisture as temperature rises, matching the physical expectation.")
R.figure("13_feature_importance.png", "Feature importance reported by the Random Forest.", 10)
R.p("Soil moisture is by far the most important feature, followed by temperature, rainfall and humidity; the crop type contributes through "
    "its threshold.")
R.h2("Electrical Optimisation Results")
R.p(f"The saved SVM was applied to the {EN['test_days']} test days, and the energy model was run for each day. Table X summarises the "
    f"comparison with the fixed two-hour timer.")
R.table(["Quantity", "Timer system", "Smart system (SVM)"],
        [["Average pump energy per day (kWh)", EN["timer_kwh_per_day"], EN["smart_kwh_per_day"]],
         ["Average water per day (litres)", f"{EN['timer_litres_per_day']:.0f}", f"{EN['smart_litres_per_day']:.0f}"],
         ["Energy saving", "-", f"{EN['saving_percent']}%"], ["Water saving", "-", f"{EN['water_saving_percent']}%"],
         ["Days the pump is ON", "100%", f"{EN['pump_on_days_percent']}%"],
         ["Energy saved per 30 days, one 100 m² plot (kWh)", "-", EN["kwh_saved_per_30_days"]]],
        "Electrical comparison on the test days", widths=[8, 3.6, 4.4])
R.figure("14_energy_comparison.png", "Average daily pump energy of the two systems.", 8)
R.figure("15_energy_distribution.png", "Distribution of daily pump energy of the smart system.", 10)
R.p(f"On average the smart system saves {EN['saving_percent']}% of the pump energy. The distribution in Fig. 19 is informative: the smart system "
    f"used less energy than the timer on {EN['days_smart_cheaper_percent']}% of days (mostly days with no irrigation, i.e. zero energy), but "
    f"more energy than the timer on {EN['days_smart_costlier_percent']}% of days, namely very dry or hot days on which the crop genuinely needs more "
    f"than the fixed two hours. This is the intended behaviour: the controller moves the energy from days when it is not needed to the days "
    f"when it is, rather than simply reducing energy at the expense of the crop. These savings depend directly on the assumed timer "
    f"duration and pump rating, so they are an estimate under stated assumptions, not a field measurement.")
R.h2("Example Predictions")
import sys
sys.path.insert(0, os.path.join(ROOT, "src"))
from predict import predict_irrigation  # noqa: E402
scen = [("Hot and dry", 36, 40, 18, 0, "Rice"), ("After heavy rain", 22, 85, 75, 30, "Wheat"),
        ("Moderate", 30, 55, 36, 0, "Maize"), ("Mild, humid", 25, 75, 48, 5, "Cotton")]
rows = []
for name, t_, h_, s_, r_, c_ in scen:
    o = predict_irrigation(t_, h_, s_, r_, c_)
    rows.append([name, f"{t_}/{h_}/{s_}/{r_}", c_, o["prediction"], o["pump_status"], f"{o['water_litres']:.0f}",
                 o["energy_used_kwh"], o["energy_saved_kwh"]])
R.table(["Scenario", "T/H/S/R", "Crop", "Prediction", "Pump", "Water (L)", "kWh used", "kWh saved"], rows,
        "Example predictions of the deployed model", widths=[2.6, 2.6, 1.7, 3.3, 1.2, 1.6, 1.8, 1.8], size=8.5)
R.p("The first scenario shows an important property: on a very hot, dry day the rice crop needs more water than the timer provides, so the "
    "saving is zero and the system uses more energy than the timer. In the second scenario the pump stays OFF and the entire timer energy is saved.")
R.h2("Web Application")
R.p("The Flask application was exercised with the Flask test client. All pages return HTTP 200, the prediction page returns the "
    "banner, pump status and energy cards, invalid input produces readable error messages, and the JSON endpoint returns the same "
    "values as the Python function. Fig. 20 shows the prediction page for a hot, dry rice field.")
R.figure("30_webapp_screenshot.png", "Prediction page of the Flask web application (result for a hot, dry rice field).", 14.5)
R.h2("Limitations")
R.bullets([
    "The dataset is synthetic. High scores show that the SVM can learn the generating rules, not that it will reach the same accuracy in a real field.",
    "The pump power, flow rate, plot size and 2-hour timer baseline are assumptions; real installations differ.",
    "The decision uses a single day's readings and does not model soil type, crop growth stage or weather forecasts.",
    "The probability 'confidence' of an SVM is a calibrated estimate from training data and can be over-confident for unusual inputs.",
    "No hardware (sensors or relay) was connected in this prototype.",
])

# =============================================================== XI. CONCLUSION
R.h1("Conclusion")
R.p(f"This project implemented an end-to-end smart irrigation system based on a Support Vector Machine and an electrical-optimisation model. A "
    f"synthetic dataset was generated and cleaned, explored with eight visualisations, scaled and used to tune and compare four "
    f"classifiers under identical conditions. The RBF-kernel SVM obtained an accuracy of {pc(svm['Accuracy'])}, an F1-score of {pc(svm['F1-score'])} and an "
    f"ROC-AUC of {svm['ROC-AUC']:.3f}, the best of the four models, although the margin over Logistic Regression and Random Forest is small. The "
    f"electrical module estimated an average pump-energy saving of {EN['saving_percent']}% against a fixed timer, while still providing more "
    f"water on days when the crop needs it. The trained pipeline was saved with Joblib and deployed in a responsive Flask web application that reports "
    f"irrigation need, pump status, electricity consumption and electricity saving.")
R.p("The study demonstrates that coupling a machine-learning decision with an explicit energy model gives results in the units that matter to "
    "a farmer. Its principal limitation is the use of synthetic data and assumed pump parameters, so the next step must be validation on "
    "measured field data.")

# =============================================================== XII. FUTURE SCOPE
R.h1("Future Scope")
R.bullets([
    ("Real data collection.", "Install soil-moisture, temperature and humidity sensors and train on measured data from several seasons and soils."),
    ("Hardware integration.", "Connect an ESP32 or Raspberry Pi with a relay and a flow meter so that the pump is switched automatically, and measure the real energy with a power meter."),
    ("Weather forecasts.", "Include forecast rainfall so that irrigation is postponed when rain is expected."),
    ("Regression of water quantity.", "Replace the rule-based volume formula with a regression model (e.g. support vector regression) trained on measured volumes."),
    ("Solar and tariff awareness.", "Schedule pumping when solar generation is high or when the electricity tariff is lowest to optimise cost as well as energy."),
    ("Edge deployment and IoT.", "Run the model on-device and report through MQTT to a cloud dashboard, with SMS alerts."),
    ("Model monitoring.", "Track prediction drift and retrain periodically; add explainability (e.g. SHAP) so that farmers can see why the pump was switched."),
])

# =============================================================== REFERENCES
R.h1("References", numbered=False)
refs = [
    'C. Cortes and V. Vapnik, "Support-vector networks," Machine Learning, vol. 20, no. 3, pp. 273-297, 1995.',
    'B. E. Boser, I. M. Guyon, and V. N. Vapnik, "A training algorithm for optimal margin classifiers," in Proc. 5th Annu. Workshop Computational Learning Theory (COLT), Pittsburgh, PA, USA, 1992, pp. 144-152.',
    'C.-C. Chang and C.-J. Lin, "LIBSVM: A library for support vector machines," ACM Trans. Intell. Syst. Technol., vol. 2, no. 3, pp. 27:1-27:27, 2011.',
    'F. Pedregosa et al., "Scikit-learn: Machine learning in Python," J. Mach. Learn. Res., vol. 12, pp. 2825-2830, 2011.',
    'L. Breiman, "Random forests," Machine Learning, vol. 45, no. 1, pp. 5-32, 2001.',
    'L. Breiman, J. H. Friedman, R. A. Olshen, and C. J. Stone, Classification and Regression Trees. Belmont, CA, USA: Wadsworth, 1984.',
    'D. W. Hosmer, S. Lemeshow, and R. X. Sturdivant, Applied Logistic Regression, 3rd ed. Hoboken, NJ, USA: Wiley, 2013.',
    'R. G. Allen, L. S. Pereira, D. Raes, and M. Smith, Crop Evapotranspiration - Guidelines for Computing Crop Water Requirements, FAO Irrigation and Drainage Paper 56. Rome, Italy: FAO, 1998.',
    'J. D. Hunter, "Matplotlib: A 2D graphics environment," Comput. Sci. Eng., vol. 9, no. 3, pp. 90-95, 2007.',
    'C. R. Harris et al., "Array programming with NumPy," Nature, vol. 585, pp. 357-362, 2020.',
    'W. McKinney, "Data structures for statistical computing in Python," in Proc. 9th Python in Science Conf. (SciPy), 2010, pp. 56-61.',
    'T. Fawcett, "An introduction to ROC analysis," Pattern Recognit. Lett., vol. 27, no. 8, pp. 861-874, 2006.',
    'C.-W. Hsu, C.-C. Chang, and C.-J. Lin, "A practical guide to support vector classification," Dept. Comput. Sci., National Taiwan Univ., Taipei, Taiwan, Tech. Rep., 2003.',
    'J. C. Platt, "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods," in Advances in Large Margin Classifiers, A. J. Smola et al., Eds. Cambridge, MA, USA: MIT Press, 1999, pp. 61-74.',
    'M. Grinberg, Flask Web Development, 2nd ed. Sebastopol, CA, USA: O\'Reilly Media, 2018.',
    'T. Hastie, R. Tibshirani, and J. Friedman, The Elements of Statistical Learning, 2nd ed. New York, NY, USA: Springer, 2009.',
]
for i, ref in enumerate(refs, 1):
    para = R.p(f"[{i}]  {ref}", align="left", size=10.5)
    para.paragraph_format.left_indent = Pt(24)
    para.paragraph_format.first_line_indent = Pt(-24)

# =============================================================== APPENDIX: SOURCE CODE
R.page_break()
R.h1("Appendix A - Source Code Listings", numbered=False)
R.p("Complete listings of the principal source files. Line-by-line explanations are provided in the separate document docs/CODE_EXPLANATION.md.")
for rel in ["src/config.py", "src/generate_dataset.py", "src/preprocess.py", "src/energy.py", "src/train_models.py",
            "src/predict.py", "app.py"]:
    R.h3(rel)
    R.code(open(os.path.join(ROOT, rel), encoding="utf-8").read(), size=7)

out = os.path.join(ROOT, "docs", "Project_Report.docx")
R.save(out)
print("Report saved ->", out, " figures:", R.fig_no, " tables:", R.tab_no)
