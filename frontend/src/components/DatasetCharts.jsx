import { Bar, Doughnut, Line, Pie, Scatter } from "react-chartjs-2";
import "../charts";
import { PALETTE, baseOptions } from "../charts";
import { useTheme } from "../context/ThemeContext";

export const COLORS = { temperature: "#f97316", humidity: "#0ea5e9", soil_moisture: "#a16207", rainfall: "#6366f1" };
const SOFT = { temperature: "rgba(249,115,22,.15)", humidity: "rgba(14,165,233,.15)", soil_moisture: "rgba(161,98,7,.15)", rainfall: "rgba(99,102,241,.25)" };

const xTicks = (opts, max = 8) => ({ ...opts, scales: { ...opts.scales, x: { ...opts.scales.x, ticks: { ...opts.scales.x.ticks, maxTicksLimit: max } } } });

/** Line chart of one variable over time (daily when the file has a date column). */
export function TrendChart({ r, k }) {
  const { dark } = useTheme();
  const ts = r.charts.timeseries;
  const data = {
    labels: ts.labels,
    datasets: [{ label: `${r.labels[k]} (${r.units[k]})`, data: ts.series[k], borderColor: COLORS[k], backgroundColor: SOFT[k],
                 fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 }],
  };
  const opts = xTicks(baseOptions(dark, { plugins: { legend: { display: false }, tooltip: { padding: 10 } } }));
  return <Line data={data} options={opts} />;
}

/** All variables on one chart: temperature / humidity / soil moisture on the left axis, rainfall bars on the right. */
export function CombinedChart({ r }) {
  const { dark } = useTheme();
  const ts = r.charts.timeseries;
  const base = baseOptions(dark);
  const line = (k) => ({ type: "line", label: `${r.labels[k]} (${r.units[k]})`, data: ts.series[k], borderColor: COLORS[k], backgroundColor: COLORS[k],
                         tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: "y" });
  const datasets = r.features.filter((k) => k !== "rainfall").map(line);
  if (r.features.includes("rainfall")) {
    datasets.push({ type: "bar", label: "Rainfall (mm)", data: ts.series.rainfall, backgroundColor: "rgba(99,102,241,.45)", yAxisID: "y1", order: 5 });
  }
  const opts = xTicks({
    ...base,
    scales: {
      ...base.scales,
      y: { ...base.scales.y, title: { display: true, text: "°C / %", color: dark ? "#cbd5e1" : "#475569" } },
      y1: { position: "right", beginAtZero: true, grid: { drawOnChartArea: false }, ticks: { color: dark ? "#cbd5e1" : "#475569" },
            title: { display: true, text: "Rainfall (mm)", color: dark ? "#cbd5e1" : "#475569" } },
    },
  });
  return <Line data={{ labels: ts.labels, datasets }} options={opts} />;
}

export function HistogramChart({ r, k }) {
  const { dark } = useTheme();
  const h = r.charts.histograms[k];
  const mids = h.edges.slice(0, -1).map((e, i) => ((e + h.edges[i + 1]) / 2).toFixed(1));
  const data = { labels: mids, datasets: [{ label: "records", data: h.counts, backgroundColor: COLORS[k], borderRadius: 4, categoryPercentage: 1, barPercentage: 0.92 }] };
  return <Bar data={data} options={xTicks(baseOptions(dark, { plugins: { legend: { display: false } } }), 6)} />;
}

export function ScatterPlot({ r }) {
  const { dark } = useTheme();
  const sc = r.charts.scatter;
  const mk = (c, label, color) => ({ label, data: sc.points.filter((p) => p.c === c).map(({ x, y }) => ({ x, y })), backgroundColor: color, pointRadius: 3.5 });
  const base = baseOptions(dark, { interaction: { mode: "nearest", intersect: true } });
  const title = (t) => ({ display: true, text: t, color: dark ? "#cbd5e1" : "#475569" });
  const opts = { ...base, scales: { x: { ...base.scales.x, title: title(`${r.labels[sc.x_key]} (${r.units[sc.x_key]})`), grid: { display: false } },
                                     y: { ...base.scales.y, beginAtZero: false, title: title(`${r.labels[sc.y_key]} (${r.units[sc.y_key]})`) } } };
  return <Scatter data={{ datasets: [mk(0, "Not needed", PALETTE.green), mk(1, "Irrigation needed", PALETTE.blue)] }} options={opts} />;
}

export function BarGraph({ r }) {
  const { dark } = useTheme();
  const b = r.charts.bar;
  return <Bar data={{ labels: b.labels, datasets: [{ label: "% needing irrigation", data: b.values, backgroundColor: PALETTE.green, borderRadius: 6 }] }}
              options={baseOptions(dark, { plugins: { legend: { display: false } } })} />;
}

export function PieGraph({ pie, doughnut = false }) {
  const { dark } = useTheme();
  const colors = [PALETTE.green, PALETTE.blue, PALETTE.amber, "#8b5cf6", "#ef4444", "#14b8a6", "#ec4899", "#64748b", "#84cc16", "#06b6d4", "#f97316", "#a855f7"];
  const Comp = doughnut ? Doughnut : Pie;
  return <Comp data={{ labels: pie.labels, datasets: [{ data: pie.values, backgroundColor: colors.slice(0, pie.labels.length), borderWidth: 0, hoverOffset: 8 }] }}
               options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: dark ? "#cbd5e1" : "#475569", usePointStyle: true } } } }} />;
}

export function RocChart({ model }) {
  const { dark } = useTheme();
  const pts = model.roc.fpr.map((x, i) => ({ x, y: model.roc.tpr[i] }));
  const base = baseOptions(dark, { interaction: { mode: "nearest", intersect: false } });
  const opts = { ...base, scales: { x: { ...base.scales.x, type: "linear", min: 0, max: 1, title: { display: true, text: "False positive rate", color: dark ? "#cbd5e1" : "#475569" } },
                                     y: { ...base.scales.y, min: 0, max: 1, title: { display: true, text: "True positive rate", color: dark ? "#cbd5e1" : "#475569" } } } };
  const data = { datasets: [
    { label: `SVM (AUC ${model.metrics.roc_auc.toFixed(3)})`, data: pts, borderColor: PALETTE.green, backgroundColor: "rgba(22,163,74,.15)", fill: true, showLine: true, pointRadius: 0, borderWidth: 3, tension: 0.1 },
    { label: "Random guess", data: [{ x: 0, y: 0 }, { x: 1, y: 1 }], borderColor: "#94a3b8", borderDash: [6, 6], showLine: true, pointRadius: 0, borderWidth: 1.5 },
  ] };
  return <Line data={data} options={opts} />;
}

export function ConfusionMatrix({ cm }) {
  const [[tn, fp], [fn, tp]] = cm;
  const cell = (v, label, good) => (
    <div className={`rounded-xl p-4 text-center ${good ? "bg-leaf-100 dark:bg-leaf-900/40" : "bg-red-50 dark:bg-red-900/20"}`}>
      <p className={`text-3xl font-extrabold ${good ? "text-leaf-700 dark:text-leaf-300" : "text-red-500"}`}>{v}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
  return (
    <div className="grid grid-cols-[auto_1fr_1fr] items-stretch gap-2 text-center text-sm">
      <span /><b className="text-slate-500">Predicted: No</b><b className="text-slate-500">Predicted: Yes</b>
      <b className="self-center text-slate-500">Actual: No</b>{cell(tn, "True negative", true)}{cell(fp, "False positive", false)}
      <b className="self-center text-slate-500">Actual: Yes</b>{cell(fn, "False negative", false)}{cell(tp, "True positive", true)}
    </div>
  );
}
