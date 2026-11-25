import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle, BrainCircuit, Lightbulb, Rows3, Columns3, SearchX, Copy, HardDrive, ShieldCheck, Sigma, Sparkles, Zap,
} from "lucide-react";
import { api } from "../api";
import Loader from "../components/Loader";
import ChartCard from "../components/ChartCard";
import CleaningSteps from "../components/CleaningSteps";
import Heatmap from "../components/Heatmap";
import BoxPlots from "../components/BoxPlots";
import ReportButtons from "../components/ReportButtons";
import {
  BarGraph, CombinedChart, ConfusionMatrix, HistogramChart, PieGraph, RocChart, ScatterPlot, TrendChart, COLORS,
} from "../components/DatasetCharts";
import { useToast } from "../context/ToastContext";
import { fmt, setActiveDataset } from "../utils/active";

const TABS = [["overview", "Overview"], ["cleaning", "Data cleaning"], ["stats", "Statistics"], ["graphs", "Graphs"], ["model", "AI model"], ["advice", "Findings"]];
const TREND_ORDER = ["soil_moisture", "rainfall", "temperature", "humidity"];
const TREND_TITLE = { soil_moisture: "Soil Moisture History", rainfall: "Rainfall History", temperature: "Temperature History", humidity: "Humidity History" };

function Kpi({ icon: Icon, label, value, sub, tone = "leaf", i = 0 }) {
  const tones = { leaf: "from-leaf-500 to-emerald-400", sky: "from-sky-500 to-cyan-400", amber: "from-amber-500 to-yellow-400", violet: "from-violet-500 to-fuchsia-400", slate: "from-slate-500 to-slate-400" };
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="glass glass-hover p-4">
      <span className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow ${tones[tone]}`}><Icon className="h-5 w-5" /></span>
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-extrabold">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </motion.div>
  );
}

function Meter({ label, value, color }) {
  return (
    <div className="glass p-4">
      <div className="flex items-baseline justify-between"><p className="text-sm font-semibold">{label}</p><p className="text-2xl font-extrabold" style={{ color }}>{(value * 100).toFixed(1)}%</p></div>
      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <motion.div className="h-full rounded-full" style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${value * 100}%` }} transition={{ duration: 1 }} />
      </div>
    </div>
  );
}

export default function Analysis() {
  const { id } = useParams();
  const toast = useToast();
  const [ds, setDs] = useState(null);
  const [params, setParams] = useSearchParams();
  const tab = TABS.some(([k]) => k === params.get("tab")) ? params.get("tab") : "overview";   // ?tab=graphs deep link
  const setTab = (k) => setParams({ tab: k }, { replace: true });

  useEffect(() => {
    api.dataset(id).then((d) => { setDs(d); if (d.status === "done") setActiveDataset(Number(id)); }).catch((e) => toast.error(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!ds) return <Loader text="Loading analysis…" />;
  if (ds.status !== "done") {
    return (
      <div className="mx-auto max-w-xl px-4 py-24 text-center">
        <AlertTriangle className="mx-auto h-12 w-12 text-amber-500" />
        <h1 className="mt-4 text-2xl font-bold">{ds.status === "error" ? "This analysis failed" : "This dataset is not analysed yet"}</h1>
        {ds.error && <p className="mt-2 text-slate-500">{ds.error}</p>}
        <Link to="/analyze" className="btn-primary mt-6">Upload a dataset</Link>
      </div>
    );
  }

  const r = ds.results;
  const info = r.info, m = r.model.metrics;
  const feats = TREND_ORDER.filter((k) => r.features.includes(k));

  return (
    <div className="page-bg min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        {/* ---------------------------------------------- header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-leaf-600">Analysis #{ds.id} · {ds.uploaded_at}</p>
            <h1 className="text-3xl font-extrabold break-all">{ds.name}</h1>
            <p className="mt-1 text-slate-500 dark:text-slate-400">{info.rows.toLocaleString()} rows → {r.cleaning.rows_after.toLocaleString()} after cleaning · SVM accuracy {(m.accuracy * 100).toFixed(1)}%</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/predict" className="btn-primary !py-2"><BrainCircuit className="h-4 w-4" />Predict with this model</Link>
            <Link to="/analyze" className="btn-outline !py-2">Upload another dataset</Link>
          </div>
        </div>
        <ReportButtons datasetId={ds.id} className="mt-4" />

        {r.target_derived && (
          <div className="glass mt-5 flex gap-3 !border-amber-400/60 p-4 text-sm">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><p>{r.target_note}</p>
          </div>
        )}

        {/* ---------------------------------------------- tabs */}
        <div className="mt-6 flex gap-2 overflow-x-auto pb-1">
          {TABS.map(([k, label]) => <button key={k} onClick={() => setTab(k)} className={`tab ${tab === k ? "tab-active" : ""}`}>{label}</button>)}
        </div>

        <div className="mt-6">
          {/* =========================================== OVERVIEW */}
          {tab === "overview" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <Kpi i={0} icon={Rows3} label="Rows" value={fmt(info.rows)} />
                <Kpi i={1} icon={Columns3} label="Columns" value={fmt(info.columns)} tone="sky" />
                <Kpi i={2} icon={SearchX} label="Missing values" value={fmt(info.missing_cells)} sub={`${info.missing_percent}% of cells`} tone="amber" />
                <Kpi i={3} icon={Copy} label="Duplicates" value={fmt(info.duplicates)} tone="violet" />
                <Kpi i={4} icon={HardDrive} label="File size" value={info.size_human} tone="slate" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Kpi i={5} icon={BrainCircuit} label="SVM accuracy" value={`${(m.accuracy * 100).toFixed(1)}%`} sub={`on ${r.model.test_rows.toLocaleString()} unseen rows`} />
                <Kpi i={6} icon={Zap} label="F1 score" value={`${(m.f1 * 100).toFixed(1)}%`} sub={`precision ${(m.precision * 100).toFixed(0)}% · recall ${(m.recall * 100).toFixed(0)}%`} tone="amber" />
                <Kpi i={7} icon={Sparkles} label="Usable rows" value={fmt(r.cleaning.rows_after)} sub={`of ${fmt(info.rows)} uploaded`} tone="sky" />
                <Kpi i={8} icon={ShieldCheck} label="Outliers found" value={fmt(Object.values(r.cleaning.outliers).reduce((a, o) => a + o.count, 0))} sub="kept unchanged" tone="violet" />
              </div>
              <div className="glass p-5">
                <h3 className="flex items-center gap-2 font-bold"><ShieldCheck className="h-5 w-5 text-leaf-600" />Data quality report</h3>
                <div className="mt-3 overflow-x-auto"><table className="w-full">
                  <thead><tr>{["Variable", "Missing (original file)", "Outliers (IQR)", "Normal range (IQR limits)"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                  <tbody>{r.features.map((k) => (
                    <tr key={k} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="td font-semibold">{r.labels[k]}</td><td className="td">{fmt(r.cleaning.missing_before[k])}</td>
                      <td className="td">{fmt(r.cleaning.outliers[k].count)}</td><td className="td">{fmt(r.cleaning.outliers[k].lower, 1)} to {fmt(r.cleaning.outliers[k].upper, 1)} {r.units[k]}</td>
                    </tr>))}</tbody>
                </table></div>
                <p className="mt-3 text-sm text-slate-500">{info.duplicates} duplicate row(s) in the file; rows with a missing value are removed rather than filled with invented numbers.</p>
              </div>
              <div className="glass p-5">
                <h3 className="font-bold">Detected columns</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(r.mapping).filter(([, v]) => v).map(([role, col]) => (
                    <span key={role} className="rounded-full bg-leaf-100 px-3 py-1 text-sm font-medium text-leaf-800 dark:bg-leaf-900/40 dark:text-leaf-200">{role.replace("_", " ")} → <b>{col}</b></span>
                  ))}
                </div>
              </div>
              <div className="glass overflow-hidden">
                <div className="border-b border-white/40 px-5 py-3 font-bold dark:border-white/10">Dataset preview</div>
                <div className="max-h-72 overflow-auto"><table className="w-full">
                  <thead className="sticky top-0 bg-leaf-50 dark:bg-slate-800"><tr>{info.column_info.map((c) => <th key={c.name} className="th">{c.name}</th>)}</tr></thead>
                  <tbody>{info.preview.map((row, i) => <tr key={i} className="border-t border-slate-100 dark:border-slate-800">{info.column_info.map((c) => <td key={c.name} className="td">{row[c.name] === null ? <span className="text-amber-500">missing</span> : String(row[c.name])}</td>)}</tr>)}</tbody>
                </table></div>
              </div>
            </div>
          )}

          {/* =========================================== CLEANING */}
          {tab === "cleaning" && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <Kpi icon={Rows3} label="Rows before" value={fmt(r.cleaning.rows_before)} tone="slate" />
                <Kpi icon={Sparkles} label="Rows after cleaning" value={fmt(r.cleaning.rows_after)} />
                <Kpi icon={SearchX} label="Missing values found" value={fmt(Object.values(r.cleaning.missing_before).reduce((a, b) => a + b, 0))} tone="amber" />
              </div>
              <CleaningSteps steps={r.cleaning.steps} />
            </div>
          )}

          {/* =========================================== STATISTICS */}
          {tab === "stats" && (
            <div className="space-y-6">
              <div className="grid gap-5 lg:grid-cols-2">
                {r.features.map((k) => {
                  const s = r.stats[k];
                  return (
                    <div key={k} className="glass p-5">
                      <div className="flex items-center gap-3"><span className="h-3 w-3 rounded-full" style={{ background: COLORS[k] }} /><h3 className="font-bold">{r.labels[k]} <span className="font-normal text-slate-500">({r.units[k]})</span></h3></div>
                      <div className="mt-4 grid grid-cols-3 gap-3">
                        {[["Mean", s.mean], ["Median", s.median], ["Mode", s.mode], ["Std dev", s.std], ["Minimum", s.min], ["Maximum", s.max]].map(([l, v]) => (
                          <div key={l} className="rounded-xl bg-white/60 p-3 text-center dark:bg-slate-800/60">
                            <p className="text-xs text-slate-500">{l}</p><p className="text-lg font-extrabold">{fmt(v, 2)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="glass overflow-x-auto p-5">
                <h3 className="mb-3 flex items-center gap-2 font-bold"><Sigma className="h-5 w-5 text-leaf-600" />Summary table</h3>
                <table className="w-full"><thead><tr>{["Variable", "Count", "Mean", "Median", "Mode", "Std dev", "Min", "Max", "Skew"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                  <tbody>{r.features.map((k) => { const s = r.stats[k]; return (
                    <tr key={k} className="border-t border-slate-100 dark:border-slate-800"><td className="td font-semibold">{r.labels[k]}</td><td className="td">{fmt(s.count)}</td>
                      {[s.mean, s.median, s.mode, s.std, s.min, s.max, s.skew].map((v, i) => <td key={i} className="td">{fmt(v, 2)}</td>)}</tr>); })}</tbody></table>
              </div>
              <ChartCard title="Correlation matrix" subtitle="Pearson correlation between all variables and the irrigation label" height="h-auto"><Heatmap labels={r.correlation.labels} matrix={r.correlation.matrix} /></ChartCard>
            </div>
          )}

          {/* =========================================== GRAPHS */}
          {tab === "graphs" && (
            <div className="space-y-6">
              <div className="grid gap-5 lg:grid-cols-2">
                {feats.map((k) => (
                  <ChartCard key={k} title={TREND_TITLE[k]} subtitle={`${r.charts.timeseries.has_date ? (k === "rainfall" ? "Daily total" : "Daily average") : "By record number"} (${r.units[k]})`}>
                    <TrendChart r={r} k={k} />
                  </ChartCard>
                ))}
              </div>
              <ChartCard title="Combined weather history" subtitle="Temperature, humidity and soil moisture (left axis) with rainfall (right axis)" height="h-80"><CombinedChart r={r} /></ChartCard>
              <ChartCard title="Correlation heatmap" subtitle="Green = move together, red = move opposite" height="h-auto"><Heatmap labels={r.correlation.labels} matrix={r.correlation.matrix} /></ChartCard>
              <div className="grid gap-5 lg:grid-cols-2">
                {r.features.map((k) => <ChartCard key={k} title={`Histogram - ${r.labels[k]}`} subtitle="How the values are distributed"><HistogramChart r={r} k={k} /></ChartCard>)}
              </div>
              <ChartCard title="Box plots" subtitle="Median, quartiles, whiskers and outliers (each plot has its own scale)" height="h-auto"><BoxPlots boxplots={r.charts.boxplots} labels={r.labels} units={r.units} /></ChartCard>
              <div className="grid gap-5 lg:grid-cols-2">
                <ChartCard title="Scatter plot" subtitle={`${r.labels[r.charts.scatter.x_key]} vs ${r.labels[r.charts.scatter.y_key]}, coloured by irrigation need`} height="h-72"><ScatterPlot r={r} /></ChartCard>
                <ChartCard title="Bar chart" subtitle={r.charts.bar.title} height="h-72"><BarGraph r={r} /></ChartCard>
                {Object.entries(r.charts.pies).map(([key, pie]) => <ChartCard key={key} title={`Pie chart - ${pie.title}`} height="h-72"><PieGraph pie={pie} /></ChartCard>)}
              </div>
            </div>
          )}

          {/* =========================================== AI MODEL */}
          {tab === "model" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <Meter label="Accuracy" value={m.accuracy} color="#16a34a" />
                <Meter label="Precision" value={m.precision} color="#0ea5e9" />
                <Meter label="Recall" value={m.recall} color="#f59e0b" />
                <Meter label="F1 score" value={m.f1} color="#8b5cf6" />
                <Meter label="ROC-AUC" value={m.roc_auc} color="#ec4899" />
              </div>
              <div className="grid gap-5 lg:grid-cols-2">
                <ChartCard title="Confusion matrix" subtitle="Evaluated on rows the model never saw during training" height="h-auto"><ConfusionMatrix cm={r.model.confusion} /></ChartCard>
                <ChartCard title="ROC curve" subtitle="Closer to the top-left corner is better" height="h-72"><RocChart model={r.model} /></ChartCard>
              </div>
              <div className="glass p-5 text-sm">
                <h3 className="mb-2 font-bold">How the SVM was trained</h3>
                <ul className="grid gap-2 sm:grid-cols-2">
                  <li>• Algorithm: Support Vector Machine, <b>RBF kernel</b></li>
                  <li>• Best settings: C = <b>{r.model.best_params.C}</b>, gamma = <b>{String(r.model.best_params.gamma)}</b> (grid search, 3-fold CV, F1)</li>
                  <li>• Train / test split: <b>{r.model.train_rows.toLocaleString()}</b> / <b>{r.model.test_rows.toLocaleString()}</b> rows (80 / 20, stratified)</li>
                  <li>• Features: <b>{r.model.features.join(", ")}</b></li>
                  <li>• Scaling: standardisation (fitted on training rows only)</li>
                  <li>• Cross-validated F1: <b>{(r.model.cv_f1 * 100).toFixed(1)}%</b></li>
                </ul>
              </div>
            </div>
          )}

          {/* =========================================== RECOMMENDATIONS */}
          {tab === "advice" && (
            <div className="space-y-4">
              {r.recommendations.map((t, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }} className="glass flex gap-4 p-5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30"><Lightbulb className="h-5 w-5" /></span>
                  <p className="text-slate-700 dark:text-slate-200">{t}</p>
                </motion.div>
              ))}
              <div className="glass p-5">
                <h3 className="font-bold">Download the full report</h3>
                <p className="text-sm text-slate-500">Includes the dataset summary, cleaning log, statistics, graphs, AI results and these findings.</p>
                <ReportButtons datasetId={ds.id} className="mt-3" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
