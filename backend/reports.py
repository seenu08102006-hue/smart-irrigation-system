"""
reports.py - downloadable reports for an analysed dataset.

    build_pdf(r, preds)   -> bytes   PDF with dataset summary, cleaning log, statistics, graphs, SVM results, recommendations
    build_xlsx(r, preds)  -> bytes   Excel workbook (several sheets + native Excel charts)
    build_csv(r, preds)   -> str     CSV with the dataset summary, statistics, model results and recommendations

`r` is the results dictionary produced by dataset_service.run_analysis(); `preds` is a list of prediction rows.
"""
import csv
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN, DARK = "#16a34a", "#14532d"
COLORS = {"temperature": "#f97316", "humidity": "#0ea5e9", "soil_moisture": "#a16207", "rainfall": "#6366f1"}
LABELS = {"temperature": "Temperature (°C)", "humidity": "Humidity (%)", "soil_moisture": "Soil moisture (%)", "rainfall": "Rainfall (mm)"}
STAT_KEYS = [("count", "Count"), ("mean", "Mean"), ("median", "Median"), ("mode", "Mode"), ("std", "Std dev"), ("min", "Min"), ("max", "Max")]


def _f(v, d=2):
    return "-" if v is None else (f"{v:,.{d}f}" if isinstance(v, (int, float)) else str(v))


# ------------------------------------------------------------------------ matplotlib images for the PDF
def _png(fig):
    """Render a figure to PNG; returns (bytes buffer, height/width ratio) so the PDF can size it."""
    w, h = fig.get_size_inches()
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf, h / w


def chart_images(r):
    c, feats = r["charts"], r["features"]
    ts = c["timeseries"]
    xs = np.arange(len(ts["labels"]))
    ticks = np.linspace(0, len(xs) - 1, min(8, len(xs))).astype(int)
    imgs = []

    def style(ax, title):
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xticks(ticks)
        ax.set_xticklabels([ts["labels"][i] for i in ticks], rotation=30, ha="right", fontsize=7)

    for k in feats:
        fig, ax = plt.subplots(figsize=(7, 2.6))
        ax.plot(xs, ts["series"][k], color=COLORS[k], lw=1.4)
        ax.set_ylabel(LABELS[k], fontsize=8)
        style(ax, f"{LABELS[k].split(' (')[0]} history")
        imgs.append((f"{LABELS[k].split(' (')[0]} History", _png(fig)))

    fig, ax = plt.subplots(figsize=(7, 3.2))
    for k in feats:
        if k != "rainfall":
            ax.plot(xs, ts["series"][k], color=COLORS[k], lw=1.2, label=LABELS[k])
    ax.set_ylabel("%, °C")
    if "rainfall" in feats:
        ax2 = ax.twinx()
        ax2.bar(xs, ts["series"]["rainfall"], color=COLORS["rainfall"], alpha=.45, label=LABELS["rainfall"], width=1.0)
        ax2.set_ylabel("Rainfall (mm)")
        h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left", ncol=4)
    else:
        ax.legend(fontsize=7, ncol=3)
    style(ax, "Combined weather history")
    imgs.append(("Combined Weather History", _png(fig)))

    corr = np.array(r["correlation"]["matrix"]); lab = r["correlation"]["labels"]
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_xticks(range(len(lab)), lab, rotation=35, ha="right", fontsize=7)
    ax.set_yticks(range(len(lab)), lab, fontsize=7)
    for i in range(len(lab)):
        for j in range(len(lab)):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, shrink=.8); ax.set_title("Correlation heatmap", fontsize=10, fontweight="bold")
    imgs.append(("Correlation Heatmap", _png(fig)))

    fig, axes = plt.subplots(1, len(feats), figsize=(7.5, 2.6))
    for ax, k in zip(np.atleast_1d(axes), feats):
        h = c["histograms"][k]; mids = [(a + b) / 2 for a, b in zip(h["edges"][:-1], h["edges"][1:])]
        ax.bar(mids, h["counts"], width=(h["edges"][1] - h["edges"][0]) * .9, color=COLORS[k])
        ax.set_title(LABELS[k].split(" (")[0], fontsize=8); ax.tick_params(labelsize=6)
    imgs.append(("Histograms", _png(fig)))

    fig, axes = plt.subplots(1, len(feats), figsize=(7.5, 2.6))
    for ax, k in zip(np.atleast_1d(axes), feats):
        b = c["boxplots"][k]
        ax.bxp([{"med": b["median"], "q1": b["q1"], "q3": b["q3"], "whislo": b["whisker_low"], "whishi": b["whisker_high"], "fliers": []}],
               showfliers=False, patch_artist=True, boxprops=dict(facecolor=COLORS[k], alpha=.7))
        ax.set_title(LABELS[k].split(" (")[0], fontsize=8); ax.set_xticks([]); ax.tick_params(labelsize=6)
    imgs.append(("Box Plots", _png(fig)))

    sc = c["scatter"]
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    for cls, col, name in [(0, GREEN, "Not needed"), (1, "#0ea5e9", "Irrigation needed")]:
        pts = [p for p in sc["points"] if p["c"] == cls]
        ax.scatter([p["x"] for p in pts], [p["y"] for p in pts], s=9, color=col, label=name, alpha=.7)
    ax.set_xlabel(LABELS.get(sc["x_key"], sc["x_key"])); ax.set_ylabel(LABELS.get(sc["y_key"], sc["y_key"]))
    ax.legend(fontsize=7); ax.set_title("Scatter plot", fontsize=10, fontweight="bold")
    imgs.append(("Scatter Plot", _png(fig)))

    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.0))
    axes[0].bar(c["bar"]["labels"], c["bar"]["values"], color=GREEN); axes[0].set_title(c["bar"]["title"], fontsize=8)
    axes[0].tick_params(labelsize=7, axis="x", rotation=30)
    pie = c["pies"]["irrigation"]
    axes[1].pie(pie["values"], labels=pie["labels"], colors=[GREEN, "#0ea5e9"], autopct="%1.0f%%", textprops={"fontsize": 8})
    axes[1].set_title("Irrigation needed", fontsize=8)
    imgs.append(("Bar and Pie Charts", _png(fig)))

    m = r["model"]
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.2))
    cm = np.array(m["confusion"]); axes[0].imshow(cm, cmap="Greens")
    axes[0].set_xticks([0, 1], ["No", "Yes"]); axes[0].set_yticks([0, 1], ["No", "Yes"])
    axes[0].set_xlabel("Predicted"); axes[0].set_ylabel("Actual"); axes[0].set_title("Confusion matrix", fontsize=9)
    for i in range(2):
        for j in range(2):
            axes[0].text(j, i, cm[i, j], ha="center", va="center", fontsize=13, color="white" if cm[i, j] > cm.max() / 2 else "black")
    axes[1].plot(m["roc"]["fpr"], m["roc"]["tpr"], color=GREEN, lw=2, label=f"AUC {m['metrics']['roc_auc']:.3f}")
    axes[1].plot([0, 1], [0, 1], "k--", lw=.7); axes[1].set_xlabel("False positive rate"); axes[1].set_ylabel("True positive rate")
    axes[1].legend(fontsize=8); axes[1].set_title("ROC curve", fontsize=9)
    imgs.append(("SVM Confusion Matrix and ROC Curve", _png(fig)))

    sv = r["svd"]
    fig, axes = plt.subplots(1, 3, figsize=(7.8, 2.8))
    x = np.arange(1, len(sv["singular_values"]) + 1)
    axes[0].plot(x, sv["singular_values"], "o-", color=GREEN); axes[0].set_title("Scree plot (singular values)", fontsize=8)
    axes[1].bar(x, np.array(sv["explained_variance_ratio"]) * 100, color="#0ea5e9")
    axes[1].plot(x, np.array(sv["cumulative_variance"]) * 100, "o-", color="#f59e0b")
    axes[1].axhline(sv["threshold"] * 100, color="grey", ls=":", lw=.8); axes[1].set_title("Explained variance %", fontsize=8)
    cm_ = sv["comparison"]; names = ["accuracy", "precision", "recall", "f1"]
    w = .38; xi = np.arange(len(names))
    axes[2].bar(xi - w / 2, [cm_["before"]["metrics"][k] * 100 for k in names], w, label="Before SVD", color="#94a3b8")
    axes[2].bar(xi + w / 2, [cm_["after"]["metrics"][k] * 100 for k in names], w, label="After SVD", color=GREEN)
    axes[2].set_xticks(xi); axes[2].set_xticklabels(["Acc", "Prec", "Rec", "F1"], fontsize=7); axes[2].legend(fontsize=6); axes[2].set_title("SVM before / after SVD %", fontsize=8)
    for ax in axes:
        ax.tick_params(labelsize=6); ax.spines[["top", "right"]].set_visible(False)
    imgs.append(("SVD analysis", _png(fig)))

    pde = r["pde"]
    fit = pde["fit"]
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ax.plot(fit["observed"], color="#a16207", lw=1.3, label="Observed (uploaded)")
    ax.plot(fit["pde"], color=GREEN, lw=1.1, label="PDE one-day-ahead")
    tk = np.linspace(0, len(fit["dates"]) - 1, min(6, len(fit["dates"]))).astype(int)
    ax.set_xticks(tk); ax.set_xticklabels([fit["dates"][i] for i in tk], rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("Soil moisture (%)", fontsize=8); ax.legend(fontsize=7); ax.spines[["top", "right"]].set_visible(False)
    imgs.append(("PDE soil-moisture model versus the uploaded readings", _png(fig)))

    fc = pde["forecast"]
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ctx = fc["context"]
    ax.plot(range(len(ctx["observed"])), ctx["observed"], color="#a16207", lw=1.5, label="Observed")
    x0 = len(ctx["observed"]) - 1
    for name, col in (("No rain", "#ef4444"), ("Average rain", "#0ea5e9")):
        ax.plot([x0] + [x0 + j + 1 for j in range(fc["horizon"])], [ctx["observed"][-1]] + fc["scenarios"][name]["mean"], "--o", ms=3, color=col, label=name)
    ax.axhline(fc["dry_level"], color="grey", lw=.8, ls=":", label="Dry level")
    ax.set_ylabel("Soil moisture (%)", fontsize=8); ax.legend(fontsize=7); ax.spines[["top", "right"]].set_visible(False)
    imgs.append((f"PDE forecast for the next {fc['horizon']} days", _png(fig)))

    hm = np.array(pde["heatmap"]["values"]).T
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    im = ax.imshow(hm, aspect="auto", cmap="YlGnBu", extent=[0, hm.shape[1], 1, 0])
    ax.set_xlabel("Day (last %d days of the file)" % hm.shape[1], fontsize=8); ax.set_ylabel("Depth (0 = surface, 1 = bottom)", fontsize=8)
    fig.colorbar(im, ax=ax, label="Soil moisture %")
    imgs.append(("Soil-moisture distribution over depth and time", _png(fig)))
    return imgs


# ------------------------------------------------------------------------ PDF
def build_pdf(r, preds):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title="Smart Irrigation Analysis Report")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=colors.HexColor(DARK), fontSize=20)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor(GREEN), fontSize=13, spaceBefore=12)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.grey)

    def table(data, widths=None, header=True):
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        style = [("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#cbd5e1")),
                 ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdf4")]),
                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(GREEN)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                      ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
        t.setStyle(TableStyle(style))
        return t

    info, m, mt = r["info"], r["model"], r["model"]["metrics"]
    S = [Paragraph("Smart Irrigation - Dataset Analysis Report", h1),
         Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M} &nbsp;|&nbsp; File: <b>{info['filename']}</b>", small), Spacer(1, 8)]

    S.append(Paragraph("1. Dataset summary", h2))
    S.append(table([["Rows", "Columns", "Missing cells", "Duplicates", "File size"],
                    [f"{info['rows']:,}", info["columns"], f"{info['missing_cells']:,} ({info['missing_percent']}%)", info["duplicates"], info["size_human"]]]))
    S.append(Spacer(1, 4))
    S.append(Paragraph("Detected columns: " + ", ".join(f"{k.replace('_', ' ')} = '{v}'" for k, v in r["mapping"].items() if v), body))

    S.append(Paragraph("2. Data cleaning steps", h2))
    rows = [["Step", "Result"]] + [[Paragraph(s["title"], body), Paragraph(s["detail"] or "-", body)] for s in r["cleaning"]["steps"]]
    S.append(table(rows, [5 * cm, 12.2 * cm]))
    S.append(Paragraph(f"Rows before cleaning: {r['cleaning']['rows_before']:,}; after: {r['cleaning']['rows_after']:,}.", small))

    S.append(Paragraph("3. Statistics", h2))
    rows = [["Variable"] + [lbl for _, lbl in STAT_KEYS]]
    for k in r["features"]:
        rows.append([LABELS[k]] + [_f(r["stats"][k][key], 0 if key == "count" else 2) for key, _ in STAT_KEYS])
    S.append(table(rows))
    lab, mat = r["correlation"]["labels"], r["correlation"]["matrix"]
    S.append(Spacer(1, 6))
    S.append(table([[""] + lab] + [[lab[i]] + [f"{v:.2f}" for v in mat[i]] for i in range(len(lab))]))

    S.append(PageBreak())
    S.append(Paragraph("4. Graphs", h2))
    for title, (img, ratio) in chart_images(r):
        S.append(KeepTogether([Paragraph(title, body), Image(img, width=15.5 * cm, height=15.5 * cm * ratio), Spacer(1, 6)]))

    S.append(Paragraph("5. SVM model results", h2))
    S.append(table([["Accuracy", "Precision", "Recall", "F1-score", "ROC-AUC"],
                    [f"{mt['accuracy'] * 100:.1f}%", f"{mt['precision'] * 100:.1f}%", f"{mt['recall'] * 100:.1f}%",
                     f"{mt['f1'] * 100:.1f}%", f"{mt['roc_auc']:.3f}"]]))
    S.append(Paragraph(f"RBF kernel, C = {m['best_params']['C']}, gamma = {m['best_params']['gamma']}; trained on {m['train_rows']:,} rows and tested on "
                       f"{m['test_rows']:,} unseen rows. Confusion matrix [[TN, FP], [FN, TP]] = {m['confusion']}.", body))

    sv, cmp_ = r["svd"], r["svd"]["comparison"]
    S.append(Paragraph("6. SVD feature reduction", h2))
    S.append(Paragraph("Features are standardised and decomposed as X = U Sigma V^T. The first components that keep at least "
                       f"{sv['threshold'] * 100:.0f}% of the variance feed the SVM (together with the PDE features). Features: {', '.join(sv['features'])}.", body))
    S.append(table([["Original features", "Components kept", "Variance preserved", "Singular values (first 5)"],
                    [sv["n_features"], sv["n_components"], f"{sv['variance_preserved'] * 100:.1f}%", ", ".join(f"{v:.2f}" for v in sv["singular_values"][:5])]]))
    S.append(Spacer(1, 4))
    rows = [["", "Accuracy", "Precision", "Recall", "F1", "Training time (s)", "SVM inputs"]]
    for key, name in (("before", "Before SVD"), ("after", "After SVD")):
        m_ = cmp_[key]
        rows.append([name] + [f"{m_['metrics'][k] * 100:.1f}%" for k in ("accuracy", "precision", "recall", "f1")] + [m_["train_seconds"], m_["n_inputs"]])
    rows.append(["Change (points)"] + [f"{cmp_['change'][k] * 100:+.1f}" for k in ("accuracy", "precision", "recall", "f1")] + [f"x{cmp_['time_ratio']}", ""])
    S.append(table(rows))
    pde, pp, pm = r["pde"], r["pde"]["params"], r["pde"]["metrics"]
    S.append(Paragraph("7. PDE soil-moisture model", h2))
    S.append(Paragraph("d(theta)/dt = D d2(theta)/dz2 with rainfall and irrigation entering at the surface, evaporation (rising with temperature, "
                       "falling with humidity) leaving at the surface and drainage at the bottom. Solved with finite volumes and implicit Euler; "
                       "the constants were fitted to the uploaded readings.", body))
    S.append(table([["D", "alpha (rain)", "k_e (evaporation)", "k_d (drainage)", "beta (irrigation)", "RMSE %", "Persistence RMSE %", "Skill"],
                    [pp["D"], pp["alpha"], pp["k_e"], pp["k_d"], pp["beta"] if pde["uses_irrigation"] else "n/a", f"{pm['rmse']:.2f}",
                     f"{pm['persistence_rmse']:.2f}", f"{pm['skill_vs_persistence']:.2f}"]]))
    fc = pde["forecast"]
    S.append(Spacer(1, 4))
    S.append(table([["Day"] + [d for d in fc["dates"]], ["No rain (%)"] + fc["scenarios"]["No rain"]["mean"],
                    ["Average rain (%)"] + fc["scenarios"]["Average rain"]["mean"]]))
    S.append(Paragraph(f"Forecast weather comes only from the uploaded data: temperature {fc['assumptions']['temperature']} C and humidity "
                       f"{fc['assumptions']['humidity']} % (last 7 days), rain 0 mm or the file's average of {fc['assumptions']['average_rain_mm']} mm/day.", small))
    us = r.get("usage")
    S.append(Paragraph("8. Water and electricity", h2))
    if us:
        sp = r["system_params"]
        S.append(table([["Pump ON days", "Water (L)", "Electricity (kWh)", "Pump hours", "Cost"],
                        [f"{us['pump_on_days']} ({us['pump_on_percent']}%)", f"{us['water_litres']:,}", f"{us['electricity_kwh']:,}", us["pump_hours"],
                         _f(us["cost"]) if us["cost"] is not None else "-"]]))
        if us["baseline"]:
            b = us["baseline"]
            S.append(Paragraph(f"Compared with running the pump {b['hours_per_day']:g} h every day (your figure): {b['electricity_kwh']:,} kWh and "
                               f"{b['water_litres']:,} L; saving {b['saved_kwh']:,} kWh ({_f(b['saved_percent'], 1)}%) and {b['saved_litres']:,} L.", body))
        S.append(Paragraph(f"Entered by the user: area {sp['area_m2']:g} m2, root depth {sp['root_depth_mm']:g} mm, pump {sp['pump_kw']:g} kW, "
                           f"flow {sp['flow_lph']:g} L/h.", small))
    else:
        S.append(Paragraph("Field and pump parameters were not entered, so water and electricity were not calculated.", body))
    S.append(Paragraph("9. Findings", h2))
    for t in r["recommendations"]:
        S.append(Paragraph("&bull; " + t, body))

    if preds:
        S.append(Paragraph("10. Predictions made with this model", h2))
        rows = [["Date/time", "Crop", "Temp", "Humidity", "Soil", "Rain", "Prediction", "Pump", "Conf. %", "PDE next %", "Water L", "kWh"]]
        for p in preds[:15]:
            rows.append([p["created_at"], p["crop_type"] or "-", p["temperature"], p["humidity"], p["soil_moisture"], p["rainfall"],
                         Paragraph(p["prediction"], small), p["pump_status"], p["confidence"], p["pde_next"], _f(p["water_litres"], 0), _f(p["electricity_kwh"])])
        S.append(table(rows))
    doc.build(S)
    return buf.getvalue()


# ------------------------------------------------------------------------ Excel
def build_xlsx(r, preds):
    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="16A34A")

    def header(ws, row, values):
        for i, v in enumerate(values, 1):
            c = ws.cell(row=row, column=i, value=v)
            c.font, c.fill = Font(bold=True, color="FFFFFF"), head_fill

    def widths(ws, w):
        for i, x in enumerate(w, 1):
            ws.column_dimensions[chr(64 + i)].width = x

    info, m, mt = r["info"], r["model"], r["model"]["metrics"]
    ws = wb.active
    ws.title = "Summary"
    ws["A1"], ws["A1"].font = "Smart Irrigation - Dataset Analysis Report", Font(bold=True, size=16, color="14532D")
    rows = [("File", info["filename"]), ("Rows", info["rows"]), ("Columns", info["columns"]), ("Missing cells", info["missing_cells"]),
            ("Missing %", info["missing_percent"]), ("Duplicate rows", info["duplicates"]), ("File size", info["size_human"]),
            ("Rows after cleaning", r["cleaning"]["rows_after"]), ("", ""), ("SVM accuracy", mt["accuracy"]), ("SVM precision", mt["precision"]),
            ("SVM recall", mt["recall"]), ("SVM F1", mt["f1"]), ("ROC-AUC", mt["roc_auc"]),
            ("Best C", m["best_params"]["C"]), ("Best gamma", str(m["best_params"]["gamma"]))]
    for i, (a, b) in enumerate(rows, 3):
        ws.cell(row=i, column=1, value=a).font = Font(bold=True)
        ws.cell(row=i, column=2, value=b)
    widths(ws, [38, 40])

    ws = wb.create_sheet("Cleaning steps")
    header(ws, 1, ["Step", "Status", "Detail"])
    for i, s in enumerate(r["cleaning"]["steps"], 2):
        ws.append([s["title"], s["status"], s["detail"]])
    widths(ws, [44, 10, 120])

    ws = wb.create_sheet("Statistics")
    header(ws, 1, ["Variable"] + [lbl for _, lbl in STAT_KEYS] + ["Q1", "Q3", "Skew"])
    for k in r["features"]:
        s = r["stats"][k]
        ws.append([LABELS[k]] + [s[key] for key, _ in STAT_KEYS] + [s["q1"], s["q3"], s["skew"]])
    widths(ws, [22] + [11] * 10)

    ws = wb.create_sheet("Correlation")
    lab = r["correlation"]["labels"]
    header(ws, 1, [""] + lab)
    for i, row in enumerate(r["correlation"]["matrix"]):
        ws.append([lab[i]] + [round(v, 3) for v in row])
    widths(ws, [22] + [16] * len(lab))

    ts = r["charts"]["timeseries"]
    ws = wb.create_sheet("Daily trends")
    header(ws, 1, [ts["x_title"]] + [LABELS[k] for k in r["features"]])
    for i, lbl in enumerate(ts["labels"]):
        ws.append([lbl] + [ts["series"][k][i] for k in r["features"]])
    widths(ws, [14] + [20] * len(r["features"]))
    n = len(ts["labels"]) + 1
    for j, k in enumerate(r["features"]):
        ch = LineChart(); ch.title = f"{LABELS[k]} history"; ch.height, ch.width = 7, 18
        ch.add_data(Reference(ws, min_col=j + 2, min_row=1, max_row=n), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n))
        ws.add_chart(ch, f"{chr(70 + len(r['features']))}{2 + j * 16}")

    sv = r["svd"]
    ws = wb.create_sheet("SVD")
    header(ws, 1, ["Component", "Singular value", "Explained variance", "Cumulative variance"])
    for i, (a, b_, c_) in enumerate(zip(sv["singular_values"], sv["explained_variance_ratio"], sv["cumulative_variance"]), 1):
        ws.append([f"PC{i}", a, b_, c_])
    n_pc = len(sv["singular_values"]) + 1
    for col, title, anchor, cls in [(2, "Scree plot", "G2", LineChart), (3, "Explained variance", "G18", BarChart)]:
        ch = cls(); ch.title = title; ch.height, ch.width = 7, 14
        ch.add_data(Reference(ws, min_col=col, min_row=1, max_row=n_pc), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n_pc))
        ws.add_chart(ch, anchor)
    ws.append([])
    header(ws, ws.max_row + 1, ["Loadings (V^T)"] + sv["features"])
    for i, row in enumerate(sv["all_loadings"], 1):
        ws.append([f"PC{i}"] + row)
    ws.append([])
    cmp_ = sv["comparison"]
    header(ws, ws.max_row + 1, ["SVM", "Accuracy", "Precision", "Recall", "F1", "Training time (s)", "Inputs"])
    for key, name in (("before", "Before SVD"), ("after", "After SVD")):
        m_ = cmp_[key]
        ws.append([name] + [m_["metrics"][k] for k in ("accuracy", "precision", "recall", "f1")] + [m_["train_seconds"], m_["n_inputs"]])
    ws.append(["Change"] + [cmp_["change"][k] for k in ("accuracy", "precision", "recall", "f1")])
    widths(ws, [22, 16, 18, 20, 14, 18, 10])

    pde = r["pde"]
    ws = wb.create_sheet("PDE model")
    header(ws, 1, ["Parameter / metric", "Value"])
    for k, v in {**pde["params"], **pde["metrics"]}.items():
        ws.append([k, v])
    ws.append([])
    header(ws, ws.max_row + 1, ["Date", "Observed soil moisture %", "PDE one-day-ahead %"])
    first = ws.max_row + 1
    for d, o, m_ in zip(pde["fit"]["dates"], pde["fit"]["observed"], pde["fit"]["pde"]):
        ws.append([d, o, m_])
    last = ws.max_row
    ch = LineChart(); ch.title = "PDE versus observed soil moisture"; ch.height, ch.width = 8, 18
    ch.add_data(Reference(ws, min_col=2, max_col=3, min_row=first - 1, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=first, max_row=last))
    ws.add_chart(ch, "F2")
    fc = pde["forecast"]
    ws2 = wb.create_sheet("PDE forecast")
    header(ws2, 1, ["Date", "No rain %", "Average rain %"])
    for i, d in enumerate(fc["dates"]):
        ws2.append([d, fc["scenarios"]["No rain"]["mean"][i], fc["scenarios"]["Average rain"]["mean"][i]])
    ch = LineChart(); ch.title = "Soil-moisture forecast"; ch.height, ch.width = 7, 14
    ch.add_data(Reference(ws2, min_col=2, max_col=3, min_row=1, max_row=len(fc["dates"]) + 1), titles_from_data=True)
    ch.set_categories(Reference(ws2, min_col=1, min_row=2, max_row=len(fc["dates"]) + 1))
    ws2.add_chart(ch, "F2")
    widths(ws2, [14, 14, 16])
    widths(ws, [30, 26, 22])

    ws = wb.create_sheet("Water and electricity")
    us = r.get("usage")
    if us:
        header(ws, 1, ["Month", "Water (L)", "Electricity (kWh)"] + (["Baseline water (L)", "Baseline electricity (kWh)"] if us["baseline"] else []))
        for i, lbl in enumerate(us["monthly"]["labels"]):
            row = [lbl, us["monthly"]["water"][i], us["monthly"]["electricity"][i]]
            if us["baseline"]:
                row += [us["baseline"]["monthly_baseline_water"][i], us["baseline"]["monthly_baseline_electricity"][i]]
            ws.append(row)
        n = len(us["monthly"]["labels"]) + 1
        for col, title, anchor in [(2, "Water per month (L)", "H2"), (3, "Electricity per month (kWh)", "H18")]:
            ch = BarChart(); ch.title = title; ch.height, ch.width = 7, 16
            ch.add_data(Reference(ws, min_col=col, min_row=1, max_row=n), titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n))
            ws.add_chart(ch, anchor)
        widths(ws, [12, 14, 20, 20, 26])
    else:
        ws["A1"] = "Field and pump parameters were not entered, so water and electricity were not calculated."

    ws = wb.create_sheet("SVM results")
    header(ws, 1, ["Metric", "Value"])
    for k, v in mt.items():
        ws.append([k, v])
    ws.append([])
    header(ws, ws.max_row + 1, ["Confusion matrix", "Predicted No", "Predicted Yes"])
    ws.append(["Actual No"] + m["confusion"][0]); ws.append(["Actual Yes"] + m["confusion"][1])
    ws.append([]); header(ws, ws.max_row + 1, ["ROC: false positive rate", "true positive rate"])
    for a, b in zip(m["roc"]["fpr"], m["roc"]["tpr"]):
        ws.append([a, b])
    widths(ws, [28, 16, 16])

    ws = wb.create_sheet("Findings")
    header(ws, 1, ["#", "Finding"])
    for i, t in enumerate(r["recommendations"], 1):
        ws.append([i, t]); ws.cell(row=i + 1, column=2).alignment = Alignment(wrap_text=True)
    widths(ws, [5, 140])

    ws = wb.create_sheet("Predictions")
    header(ws, 1, ["Date/time", "Crop", "Temperature", "Humidity", "Soil moisture", "Rainfall", "Prediction", "Pump", "Confidence %", "PDE soil moisture tomorrow %", "Water (L)", "Electricity (kWh)"])
    for p in preds:
        ws.append([p["created_at"], p["crop_type"], p["temperature"], p["humidity"], p["soil_moisture"], p["rainfall"], p["prediction"],
                   p["pump_status"], p["confidence"], p["pde_next"], p["water_litres"], p["electricity_kwh"]])
    widths(ws, [20, 12, 12, 10, 14, 10, 22, 8, 12, 26, 12, 16])

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ------------------------------------------------------------------------ CSV
def build_csv(r, preds):
    out = io.StringIO()
    w = csv.writer(out)
    info, m, mt = r["info"], r["model"], r["model"]["metrics"]
    w.writerow(["SMART IRRIGATION - DATASET ANALYSIS REPORT"]); w.writerow(["File", info["filename"]])
    w.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")]); w.writerow([])
    w.writerow(["DATASET SUMMARY"])
    for k, v in [("Rows", info["rows"]), ("Columns", info["columns"]), ("Missing cells", info["missing_cells"]), ("Duplicates", info["duplicates"]),
                 ("File size", info["size_human"]), ("Rows after cleaning", r["cleaning"]["rows_after"])]:
        w.writerow([k, v])
    w.writerow([]); w.writerow(["CLEANING STEPS"]); w.writerow(["Step", "Status", "Detail"])
    for s in r["cleaning"]["steps"]:
        w.writerow([s["title"], s["status"], s["detail"]])
    w.writerow([]); w.writerow(["STATISTICS"]); w.writerow(["Variable"] + [lbl for _, lbl in STAT_KEYS])
    for k in r["features"]:
        w.writerow([LABELS[k]] + [round(r["stats"][k][key], 3) if r["stats"][k][key] is not None else "" for key, _ in STAT_KEYS])
    w.writerow([]); w.writerow(["CORRELATION MATRIX"]); lab = r["correlation"]["labels"]; w.writerow([""] + lab)
    for i, row in enumerate(r["correlation"]["matrix"]):
        w.writerow([lab[i]] + [round(v, 3) for v in row])
    w.writerow([]); w.writerow(["SVM RESULTS"])
    for k, v in mt.items():
        w.writerow([k, v])
    w.writerow(["best C", m["best_params"]["C"]]); w.writerow(["best gamma", m["best_params"]["gamma"]])
    w.writerow(["confusion matrix [[TN, FP], [FN, TP]]", str(m["confusion"])])
    sv = r["svd"]
    w.writerow([]); w.writerow(["SVD FEATURE REDUCTION"])
    w.writerow(["Original features", sv["n_features"], ", ".join(sv["features"])]); w.writerow(["Components kept", sv["n_components"]])
    w.writerow(["Variance preserved", round(sv["variance_preserved"], 4)])
    w.writerow(["Component", "Singular value", "Explained variance", "Cumulative"])
    for i, (a, b_, c_) in enumerate(zip(sv["singular_values"], sv["explained_variance_ratio"], sv["cumulative_variance"]), 1):
        w.writerow([f"PC{i}", a, b_, c_])
    w.writerow(["SVM", "Accuracy", "Precision", "Recall", "F1", "Training time (s)", "Inputs"])
    for key, name in (("before", "Before SVD"), ("after", "After SVD")):
        m_ = sv["comparison"][key]
        w.writerow([name] + [m_["metrics"][k] for k in ("accuracy", "precision", "recall", "f1")] + [m_["train_seconds"], m_["n_inputs"]])
    pde = r["pde"]
    w.writerow([]); w.writerow(["PDE SOIL-MOISTURE MODEL (fitted to the uploaded data)"])
    for k, v in {**pde["params"], **pde["metrics"]}.items():
        w.writerow([k, v])
    fc = pde["forecast"]
    w.writerow([]); w.writerow(["PDE FORECAST", "No rain %", "Average rain %"])
    for i, d in enumerate(fc["dates"]):
        w.writerow([d, fc["scenarios"]["No rain"]["mean"][i], fc["scenarios"]["Average rain"]["mean"][i]])
    us = r.get("usage")
    w.writerow([]); w.writerow(["WATER AND ELECTRICITY"])
    if us:
        w.writerow(["Pump ON days", us["pump_on_days"]]); w.writerow(["Water (L)", us["water_litres"]])
        w.writerow(["Electricity (kWh)", us["electricity_kwh"]]); w.writerow(["Pump hours", us["pump_hours"]])
        if us["baseline"]:
            w.writerow(["Baseline electricity (kWh)", us["baseline"]["electricity_kwh"]]); w.writerow(["Saved (kWh)", us["baseline"]["saved_kwh"]])
        w.writerow(["Month", "Water (L)", "Electricity (kWh)"])
        for i, lbl in enumerate(us["monthly"]["labels"]):
            w.writerow([lbl, us["monthly"]["water"][i], us["monthly"]["electricity"][i]])
    else:
        w.writerow(["Field and pump parameters were not entered, so water and electricity were not calculated."])
    w.writerow([]); w.writerow(["FINDINGS"])
    for t in r["recommendations"]:
        w.writerow([t])
    if preds:
        w.writerow([]); w.writerow(["PREDICTIONS MADE WITH THIS MODEL"])
        w.writerow(["Date/time", "Crop", "Temperature", "Humidity", "Soil moisture", "Rainfall", "Prediction", "Pump", "Confidence %", "PDE soil moisture tomorrow %", "Water (L)", "Electricity (kWh)"])
        for p in preds:
            w.writerow([p["created_at"], p["crop_type"], p["temperature"], p["humidity"], p["soil_moisture"], p["rainfall"], p["prediction"],
                        p["pump_status"], p["confidence"], p["pde_next"], p["water_litres"], p["electricity_kwh"]])
    return out.getvalue()
