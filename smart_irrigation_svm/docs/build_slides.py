"""
build_slides.py - generates docs/Project_Presentation.pptx (20 slides, speaker notes on every slide).
Numbers come from reports/*.json so the slides always match the code.

Run:  python docs/build_slides.py
"""
import json
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import config  # noqa: E402

M = json.load(open(config.METRICS_JSON))
EN = json.load(open(os.path.join(config.REPORT_DIR, "energy_summary.json")))
EDA = json.load(open(os.path.join(config.REPORT_DIR, "eda_summary.json")))
MD = M["models"]
S = MD["SVM"]
pc = lambda v: f"{100 * v:.1f}%"      # noqa: E731

DARK, GREEN, LIGHT, GREY = RGBColor(0x14, 0x53, 0x2D), RGBColor(0x16, 0xA3, 0x4A), RGBColor(0xF0, 0xFD, 0xF4), RGBColor(0x47, 0x55, 0x69)
WHITE = RGBColor(255, 255, 255)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height
count = [0]


def fig(name):
    return os.path.join(config.FIG_DIR, name)


def text(slide, x, y, w, h, content, size=18, bold=False, color=GREY, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    lines = content if isinstance(content, list) else [content]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bold, color
        r.font.name = "Calibri"
        p.space_after = Pt(8)
    return tb


def bullets(slide, x, y, w, h, items, size=19):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = "•  " + it
        r.font.size, r.font.color.rgb, r.font.name = Pt(size), GREY, "Calibri"
        p.space_after = Pt(10)


def new_slide(title, notes):
    s = prs.slides.add_slide(BLANK)
    count[0] += 1
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(1.05))
    bar.fill.solid(); bar.fill.fore_color.rgb = DARK; bar.line.fill.background()
    text(s, Inches(.5), Inches(.18), Inches(11.5), Inches(.8), title, 30, True, WHITE)
    acc = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(1.05), W, Inches(.07))
    acc.fill.solid(); acc.fill.fore_color.rgb = GREEN; acc.line.fill.background()
    text(s, Inches(12.2), Inches(6.95), Inches(1), Inches(.4), str(count[0]), 12, False, GREY, PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = notes
    return s


def image(s, name, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = w
    if h: kw["height"] = h
    s.shapes.add_picture(fig(name), x, y, **kw)


def card(s, x, y, w, h, big, small, color=GREEN):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    box.fill.solid(); box.fill.fore_color.rgb = color; box.line.fill.background()
    text(s, x, y + Inches(.15), w, Inches(.8), big, 32, True, WHITE, PP_ALIGN.CENTER)
    text(s, x, y + Inches(.95), w, Inches(.6), small, 14, False, WHITE, PP_ALIGN.CENTER)


def table(s, x, y, w, rows, col_w=None, size=14):
    shape = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, Inches(.45) * len(rows))
    t = shape.table
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = t.cell(r, c)
            cell.text = str(val)
            para = cell.text_frame.paragraphs[0]
            para.font.size = Pt(size)
            para.font.bold = r == 0
            para.font.color.rgb = WHITE if r == 0 else GREY
            cell.fill.solid()
            cell.fill.fore_color.rgb = GREEN if r == 0 else (LIGHT if r % 2 else WHITE)
    if col_w:
        for i, cw in enumerate(col_w):
            t.columns[i].width = Inches(cw)


# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK); count[0] += 1
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H); bg.fill.solid(); bg.fill.fore_color.rgb = DARK; bg.line.fill.background()
band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(5.2), W, Inches(.12)); band.fill.solid(); band.fill.fore_color.rgb = GREEN; band.line.fill.background()
text(s, Inches(.8), Inches(1.7), Inches(11.5), Inches(2.2), "Smart Irrigation using Support Vector Machine (SVM) and Electrical Optimization", 44, True, WHITE)
text(s, Inches(.8), Inches(4.1), Inches(11), Inches(.8), "Final-year project presentation", 22, False, RGBColor(0xBB, 0xF7, 0xD0))
text(s, Inches(.8), Inches(5.6), Inches(11), Inches(1.2), ["[Student names]  |  [Register numbers]", "Guide: [Guide name]  |  Department of [Department], [College]"], 18, False, WHITE)
s.notes_slide.notes_text_frame.text = ("Good morning. Today we present our final-year project, Smart Irrigation using a Support Vector Machine and "
    "Electrical Optimization. In the next 15 to 20 minutes we will explain the problem, how we built and compared the models, "
    "what electrical saving the system achieves, and how it works as a web application. (Replace the placeholders with your names.)")

# ---------------------------------------------------------------- 2 agenda
s = new_slide("Agenda", "This is the roadmap of the talk. We start with the problem and objectives, then the data and the machine-learning work, "
              "then the electrical part, the web application, and we finish with conclusions and future work.")
bullets(s, Inches(.8), Inches(1.5), Inches(11), Inches(5), [
    "Problem and objectives", "Existing approaches and research gap", "System architecture", "Dataset, cleaning and EDA",
    "SVM and model comparison", "Electrical optimisation model and results", "Flask web application", "Conclusion, limitations, future scope"], 26)

# ---------------------------------------------------------------- 3 problem
s = new_slide("Problem: water and electricity wasted by timers", "Most farms irrigate on a fixed timer. The timer cannot see that it rained last night "
              "or that today is unusually hot. The result is wasted water, wasted pump electricity, and sometimes a thirsty crop. Our goal is to switch the pump only when the crop truly needs water.")
bullets(s, Inches(.7), Inches(1.5), Inches(7.2), Inches(5), [
    "Agriculture is the largest user of fresh water", "Pumps run on electricity: every wasted litre also wastes kWh",
    "Timer controllers ignore weather and soil condition", "Single-threshold controllers ignore heat, humidity, rain and crop type",
    "Need: a decision that learns the interaction of all factors"], 22)
card(s, Inches(8.4), Inches(1.7), Inches(4.2), Inches(1.6), "Timer", "fixed 2 h/day = 3.0 kWh", RGBColor(0xF9, 0x73, 0x16))
card(s, Inches(8.4), Inches(3.6), Inches(4.2), Inches(1.6), "Smart", f"SVM decides: {EN['smart_kwh_per_day']} kWh/day avg", GREEN)

# ---------------------------------------------------------------- 4 objectives
s = new_slide("Objectives", "These are the eight objectives. They cover the machine-learning pipeline, the comparison with other algorithms, the electrical module and the web deployment.")
bullets(s, Inches(.8), Inches(1.4), Inches(11.8), Inches(5.5), [
    "Build a dataset: temperature, humidity, soil moisture, rainfall, crop, irrigation label",
    "Clean data, handle missing values, scale features, explore with graphs",
    "Train and tune an SVM classifier",
    "Compare with Decision Tree, Random Forest, Logistic Regression",
    "Save the best model with Joblib",
    "Estimate pump status, electricity consumption and savings",
    "Deploy as a Flask + Bootstrap web application",
    "Document everything for reproducibility"], 22)

# ---------------------------------------------------------------- 5 literature
s = new_slide("Existing approaches and research gap", "Irrigation scheduling can be timer based, threshold based, model based using evapotranspiration equations such as FAO-56, or learning based. "
              "Many prototypes stop at classification accuracy. We add an explicit pump-energy model so the benefit is measured in kilowatt-hours. We also say clearly that our data is synthetic.")
table(s, Inches(.6), Inches(1.5), Inches(12.1), [
    ["Approach", "Inputs", "Adapts to weather?", "Weakness"],
    ["Timer / calendar", "Clock", "No", "Waters wet soil"],
    ["Threshold on-off", "Soil moisture", "Partly", "Ignores heat, rain, crop"],
    ["ET model (FAO-56)", "Weather + crop coeff.", "Yes", "Many parameters needed"],
    ["Machine learning (ours)", "Sensors + crop", "Yes", "Needs good data"]], [3.2, 3.3, 2.6, 3.0], 17)
text(s, Inches(.6), Inches(4.2), Inches(12), Inches(1.5), "Research gap: link the classifier's decision to pump run-time and kWh, and report both from the same test set.", 22, True, DARK)

# ---------------------------------------------------------------- 6 architecture
s = new_slide("System architecture", "Sensors give the four readings. They are cleaned and scaled, the SVM predicts the irrigation need, the electrical module converts the decision into litres, run-time and kWh, "
              "and the Flask server shows the result in the browser and could send the ON/OFF command to a relay.")
image(s, "20_system_architecture.png", Inches(.9), Inches(1.5), w=Inches(11.5))

# ---------------------------------------------------------------- 7 dataset
s = new_slide("Dataset (synthetic, rule-based)", "We could not find an open dataset with exactly these columns, so we generated 5,000 days from agronomic rules: each crop has a moisture threshold, heat and low humidity raise the need, rain lowers it with diminishing returns, and Gaussian noise imitates sensors. "
              "We are open about this: results show the method works, not that it will give the same accuracy in a real field.")
table(s, Inches(.6), Inches(1.5), Inches(7.4), [
    ["Attribute", "Unit", "Role"], ["temperature", "°C", "input"], ["humidity", "%", "input"], ["soil_moisture", "%", "input"],
    ["rainfall", "mm", "input"], ["crop_type", "5 crops", "input"], ["irrigation_needed", "0 / 1", "target"]], [3.2, 1.8, 2.4], 16)
bullets(s, Inches(8.4), Inches(1.5), Inches(4.6), Inches(5), [
    "5,000 cleaned rows", f"Classes: {EDA['class_counts']['0']} No / {EDA['class_counts']['1']} Yes (balanced)",
    "Non-linear label rule + noise", "Raw file intentionally 'dirty'"], 18)

# ---------------------------------------------------------------- 8 cleaning
cl = EDA["cleaning"]
s = new_slide("Data cleaning and preprocessing", "We injected realistic faults into the raw file and then fixed them: duplicates removed, impossible values turned into missing values, missing values filled with the crop-wise median, and incomplete rows dropped. "
              "Scaling and encoding sit inside the model pipeline so the test set never influences the scaler.")
image(s, "21_ml_pipeline.png", Inches(.4), Inches(1.4), w=Inches(12.5))
card(s, Inches(.8), Inches(3.6), Inches(3.5), Inches(1.6), str(cl["duplicates_removed"]), "duplicates removed")
card(s, Inches(4.9), Inches(3.6), Inches(3.5), Inches(1.6), str(cl["missing_before_fill"]), "missing/invalid values filled", RGBColor(0x0E, 0xA5, 0xE9))
card(s, Inches(9), Inches(3.6), Inches(3.5), Inches(1.6), str(cl["rows_after"]), "clean rows", DARK)
text(s, Inches(.8), Inches(5.5), Inches(12), Inches(1.2), "StandardScaler on 4 sensors + OneHotEncoder on crop, inside a Pipeline (no data leakage).  80/20 stratified split.", 18)

# ---------------------------------------------------------------- 9 EDA 1
s = new_slide("EDA 1: distributions", "Soil moisture separates the two classes best: irrigation days sit at low moisture. Temperature shifts the needed class toward hotter days, and rainfall is almost always zero on irrigation days.")
image(s, "03_feature_histograms.png", Inches(.5), Inches(1.4), h=Inches(5.4))
image(s, "02_class_balance.png", Inches(8.6), Inches(1.6), w=Inches(4.4))

# ---------------------------------------------------------------- 10 EDA 2
s = new_slide("EDA 2: relationships", "The heat-map shows soil moisture has the strongest relation with the target. The scatter plot shows the irrigation boundary is curved: the moisture level at which a crop needs water increases with temperature. "
              "A single fixed threshold cannot capture that, which is why a non-linear classifier is useful.")
image(s, "05_correlation_heatmap.png", Inches(.5), Inches(1.4), h=Inches(5.4))
image(s, "06_scatter_soil_temp.png", Inches(6.6), Inches(1.5), w=Inches(6.4))

# ---------------------------------------------------------------- 11 SVM
s = new_slide("Support Vector Machine in one slide", "An SVM finds the separating boundary with the widest margin between classes. The soft-margin parameter C allows a few mistakes for a wider margin. "
              "The RBF kernel lets the boundary bend, and gamma controls how much it bends. We choose C and gamma with grid search and cross-validation.")
image(s, "23_svm_concept.png", Inches(.5), Inches(1.4), h=Inches(4.6))
bullets(s, Inches(6.3), Inches(1.5), Inches(6.7), Inches(5), [
    "Maximise margin 2/||w||", "Soft margin: min ½||w||² + C·Σξ", "RBF kernel: K = exp(−γ‖x−x'‖²)",
    "Only support vectors define the boundary", f"Tuned: C = {S['Best params']['C']}, γ = {S['Best params']['gamma']}"], 21)

# ---------------------------------------------------------------- 12 models + tuning
s = new_slide("Four models, fair comparison", "To make the comparison fair, all four models get the same preprocessing, the same five-fold grid search scored on F1, and the same untouched test set of 1,000 days.")
table(s, Inches(.6), Inches(1.5), Inches(12.1), [
    ["Model", "Tuned hyper-parameters (grid)", "Selected"],
    ["SVM (RBF)", "C, gamma", str(S["Best params"])],
    ["Decision Tree", "max_depth, min_samples_leaf", str(MD["Decision Tree"]["Best params"])],
    ["Random Forest", "n_estimators, max_depth", str(MD["Random Forest"]["Best params"])],
    ["Logistic Regression", "C", str(MD["Logistic Regression"]["Best params"])]], [2.8, 4.0, 5.3], 16)
text(s, Inches(.6), Inches(4.3), Inches(12), Inches(1.5), "Same pipeline • 5-fold CV on train • score = F1 • test set used once", 22, True, DARK)

# ---------------------------------------------------------------- 13 results table
s = new_slide("Results: accuracy, precision, recall, F1", "SVM has the highest F1, recall and AUC. But the gaps to Logistic Regression and Random Forest are small, less than the fold-to-fold variation, "
              "so the honest conclusion is: the SVM is at least as good as the alternatives here, with a slight edge. The single decision tree is clearly weaker.")
rows = [["Model", "Accuracy", "Precision", "Recall", "F1", "AUC"]] + [[n, pc(m["Accuracy"]), pc(m["Precision"]), pc(m["Recall"]), pc(m["F1-score"]), f"{m['ROC-AUC']:.3f}"] for n, m in MD.items()]
table(s, Inches(.5), Inches(1.5), Inches(7.2), rows, [2.4, 1.0, 1.0, 0.9, 0.9, 1.0], 13)
image(s, "11_model_comparison.png", Inches(7.9), Inches(1.6), w=Inches(5.2))
text(s, Inches(.5), Inches(4.4), Inches(7.2), Inches(2), f"SVM: F1 {pc(S['F1-score'])}, AUC {S['ROC-AUC']:.3f}.  Differences between top three are small.", 18, True, DARK)

# ---------------------------------------------------------------- 14 confusion/ROC
cm = M["confusion_matrices"]["SVM"]
s = new_slide("Confusion matrices and ROC", f"For the SVM there were {cm[1][0]} false negatives, thirsty crops we did not water, and {cm[0][1]} false positives, unnecessary irrigations. "
              "For a farm, false negatives hurt yield, so we prefer high recall, and the SVM has the highest recall of the four.")
image(s, "09_confusion_matrices.png", Inches(.4), Inches(1.4), h=Inches(5.5))
image(s, "12_roc_curves.png", Inches(7.3), Inches(1.5), w=Inches(5.6))

# ---------------------------------------------------------------- 15 why SVM
s = new_slide("Why the SVM was selected", "We selected the SVM for five reasons, but we want to be fair: the numerical margin is small, so non-numerical reasons also count. The margin concept suits noisy sensors, the RBF kernel handles non-linear interactions, the model is compact, and it provides probabilities.")
bullets(s, Inches(.8), Inches(1.5), Inches(11.8), Inches(5), [
    f"Highest F1 ({pc(S['F1-score'])}), recall and ROC-AUC ({S['ROC-AUC']:.3f}) of the four models",
    "RBF kernel captures heat × humidity × rain interactions",
    "Soft margin (C) tolerates sensor noise", "Compact: only support vectors stored → fast on a small controller",
    "Probability output (Platt scaling) → confidence shown to user",
    "Honest note: margin over Logistic Regression is small"], 24)

# ---------------------------------------------------------------- 16 electrical model
s = new_slide("Electrical optimisation model", "After the classifier says irrigation is needed, we compute how much water to deliver, from the moisture deficit, crop demand, heat and rain. Dividing by the pump flow gives the run time, multiplying by the motor power gives kilowatt-hours. "
              "The baseline is a timer running two hours a day at 1.5 kilowatts, which is 3 kilowatt-hours. All constants are assumptions in config.py.")
bullets(s, Inches(.7), Inches(1.5), Inches(8), Inches(5), [
    "Water V = deficit × 300 L/% × crop factor × heat factor − 100 L/mm × rain",
    "Run-time t = V / 3000 L·h⁻¹", "Energy E = 1.5 kW × t",
    "Timer baseline = 2 h × 1.5 kW = 3.0 kWh/day", "Saved = max(3.0 − E, 0);  SVM says NO → pump OFF, E = 0"], 20)
card(s, Inches(9), Inches(1.7), Inches(3.6), Inches(1.6), "1.5 kW", "pump motor (assumed)")
card(s, Inches(9), Inches(3.6), Inches(3.6), Inches(1.6), "3000 L/h", "pump flow (assumed)", RGBColor(0x0E, 0xA5, 0xE9))

# ---------------------------------------------------------------- 17 energy results
s = new_slide("Energy results on 1,000 test days", f"On average the smart controller used {EN['smart_kwh_per_day']} kilowatt-hours per day versus 3.0 for the timer, a {EN['saving_percent']} percent saving, and the same percentage of water. "
              f"Importantly, on {EN['days_smart_costlier_percent']} percent of days it used more than the timer, because those days were hot and dry and the crop truly needed more. So the system re-allocates energy to when it is needed. These numbers depend on our assumed pump and timer.")
card(s, Inches(.6), Inches(1.5), Inches(3.8), Inches(1.6), f"{EN['saving_percent']}%", "average energy saving")
card(s, Inches(.6), Inches(3.3), Inches(3.8), Inches(1.6), f"{EN['smart_kwh_per_day']} kWh", "smart avg/day vs 3.0 timer", RGBColor(0x0E, 0xA5, 0xE9))
card(s, Inches(.6), Inches(5.1), Inches(3.8), Inches(1.6), f"{EN['pump_on_days_percent']}%", "days the pump runs", DARK)
image(s, "15_energy_distribution.png", Inches(4.8), Inches(1.5), w=Inches(8.2))

# ---------------------------------------------------------------- 18 web app
shot = os.path.join(config.FIG_DIR, "30_webapp_screenshot.png")
s = new_slide("Flask web application", "The user enters temperature, humidity, soil moisture, rainfall and crop. The page returns Irrigation Required or Not Required, pump ON or OFF, estimated electricity consumption and savings, litres and run-time. "
              "There is also a JSON endpoint that an ESP32 or Raspberry Pi could call to automate the pump. The interface is built with HTML, CSS and Bootstrap 5.")
if os.path.exists(shot):
    s.shapes.add_picture(shot, Inches(.4), Inches(1.4), height=Inches(5.5))
bullets(s, Inches(7.6), Inches(1.5), Inches(5.4), Inches(5), [
    "Responsive Bootstrap UI", "Input validation (browser + server)", "Pump status + confidence", "kWh used and saved",
    "POST /api/predict (JSON)", "Model results page with graphs"], 20)

# ---------------------------------------------------------------- 19 conclusion
s = new_slide("Conclusion and limitations", "In conclusion, we built a complete pipeline from data to a web application. The SVM gave the best F1, though only slightly, and the electrical model shows about a quarter to a third lower pump energy under our assumptions. "
              "The main limitation is that the data and pump parameters are synthetic or assumed; validation on field data is the next step.")
bullets(s, Inches(.7), Inches(1.4), Inches(6), Inches(5.5), [
    "End-to-end pipeline delivered", f"SVM: acc {pc(S['Accuracy'])}, F1 {pc(S['F1-score'])}", f"≈{EN['saving_percent']}% pump-energy saving (simulated)",
    "Model saved with Joblib, served via Flask"], 21)
text(s, Inches(7), Inches(1.4), Inches(6), Inches(.5), "Limitations", 24, True, DARK)
bullets(s, Inches(7), Inches(2.0), Inches(6), Inches(4.5), [
    "Synthetic data", "Assumed pump & timer values", "Single-day decision, no forecast", "No hardware connected yet"], 19)

# ---------------------------------------------------------------- 20 future
s = new_slide("Future scope and thank you", "Future work: collect real sensor data, connect an ESP32 with a relay and a power meter, use weather forecasts, replace the volume formula with a regression model, and schedule pumping with solar generation or cheaper tariffs. Thank you; we are happy to take questions.")
bullets(s, Inches(.8), Inches(1.4), Inches(11.5), Inches(4.3), [
    "Real field data from several seasons and soils", "ESP32 / Raspberry Pi + relay + flow and power meter",
    "Weather-forecast aware scheduling", "Support Vector Regression for water volume",
    "Solar-aware and tariff-aware pumping", "Explainability (SHAP) and model monitoring"], 22)
text(s, Inches(.8), Inches(5.6), Inches(11.5), Inches(1), "Thank you  -  Questions?", 36, True, GREEN)

out = os.path.join(config.ROOT, "docs", "Project_Presentation.pptx")
prs.save(out)
print("Saved", out, "slides:", len(prs.slides))
