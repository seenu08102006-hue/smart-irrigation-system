import { Bar, Line, Scatter } from "react-chartjs-2";
import { ArrowRight, Boxes, Clock, Layers, Percent, Sigma, TrendingDown, TrendingUp } from "lucide-react";
import "../charts";
import { PALETTE, baseOptions } from "../charts";
import { useTheme } from "../context/ThemeContext";
import ChartCard from "./ChartCard";
import { fmt } from "../utils/active";

const METRICS = [["accuracy", "Accuracy"], ["precision", "Precision"], ["recall", "Recall"], ["f1", "F1 score"]];

function Card({ icon: Icon, label, value, sub, tone = "from-leaf-500 to-emerald-400" }) {
  return (
    <div className="glass p-4">
      <span className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow ${tone}`}><Icon className="h-5 w-5" /></span>
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-extrabold">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

const Delta = ({ v, unit = "points", good = "up" }) => {
  const up = v > 0, flat = Math.abs(v) < 1e-9;
  const ok = flat ? null : (good === "up" ? up : !up);
  return <span className={`font-bold ${ok === null ? "text-slate-500" : ok ? "text-leaf-600" : "text-red-500"}`}>{up ? "+" : ""}{v.toFixed(1)} {unit}</span>;
};

/** Loadings (V^T): how strongly each original feature contributes to each kept component. -1 = red, +1 = green. */
function Loadings({ svd }) {
  const col = (v) => (v >= 0 ? `rgba(22,163,74,${0.1 + Math.min(1, v) * 0.85})` : `rgba(239,68,68,${0.1 + Math.min(1, -v) * 0.85})`);
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[420px] gap-1" style={{ gridTemplateColumns: `auto repeat(${svd.features.length}, minmax(0, 1fr))` }}>
        <div />
        {svd.features.map((f) => <div key={f} className="truncate px-1 pb-1 text-center text-[11px] font-semibold text-slate-500" title={f}>{f}</div>)}
        {svd.loadings.map((row, i) => (
          <div key={i} className="contents">
            <div className="flex items-center pr-2 text-[11px] font-semibold text-slate-500">PC{i + 1} ({(svd.explained_variance_ratio[i] * 100).toFixed(0)}%)</div>
            {row.map((v, j) => (
              <div key={j} title={`PC${i + 1} / ${svd.features[j]}: ${v}`} className="flex h-10 items-center justify-center rounded-lg text-xs font-bold text-slate-900 dark:text-white" style={{ background: col(v) }}>{v.toFixed(2)}</div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SvdPanel({ r }) {
  const { dark } = useTheme();
  const svd = r.svd, cmp = svd.comparison, p = svd.n_features, k = svd.n_components;
  const pcs = svd.singular_values.map((_, i) => `PC${i + 1}`);
  const thr = svd.threshold;
  const base = baseOptions(dark);

  const scree = { labels: pcs, datasets: [{ label: "Singular value σ", data: svd.singular_values, borderColor: PALETTE.green, backgroundColor: PALETTE.greenSoft, pointRadius: 5, tension: 0.2, fill: true }] };
  const explained = {
    labels: pcs,
    datasets: [
      { type: "bar", label: "Explained variance (%)", data: svd.explained_variance_ratio.map((v) => +(v * 100).toFixed(2)), backgroundColor: svd.explained_variance_ratio.map((_, i) => (i < k ? PALETTE.blue : "#cbd5e1")), borderRadius: 6 },
      { type: "line", label: "Cumulative (%)", data: svd.cumulative_variance.map((v) => +(v * 100).toFixed(2)), borderColor: PALETTE.amber, pointRadius: 4, tension: 0.2 },
      { type: "line", label: `${thr * 100}% target`, data: pcs.map(() => thr * 100), borderColor: PALETTE.slate, borderDash: [5, 4], pointRadius: 0, borderWidth: 1 },
    ],
  };
  const dist = { labels: svd.features.map((f) => f), datasets: [{ label: "Share of the kept components (%)", data: svd.feature_contribution.map((v) => +(v * 100).toFixed(1)), backgroundColor: PALETTE.green, borderRadius: 6 }] };
  const sigmaShare = { labels: pcs, datasets: [{ label: "Singular value share (σ / Σσ, %)", data: svd.singular_values.map((v) => +((100 * v) / svd.singular_values.reduce((a, b) => a + b, 0)).toFixed(1)), backgroundColor: PALETTE.amber, borderRadius: 6 }] };
  const reduction = {
    labels: ["Features", "Variance kept (%)"],
    datasets: [{ label: "Before SVD", data: [p, 100], backgroundColor: "#94a3b8", borderRadius: 6 }, { label: "After SVD", data: [k, +(svd.variance_preserved * 100).toFixed(1)], backgroundColor: PALETTE.green, borderRadius: 6 }],
  };
  const perf = {
    labels: METRICS.map(([, l]) => l),
    datasets: [{ label: "Before SVD", data: METRICS.map(([m]) => +(cmp.before.metrics[m] * 100).toFixed(2)), backgroundColor: "#94a3b8", borderRadius: 6 },
               { label: "After SVD", data: METRICS.map(([m]) => +(cmp.after.metrics[m] * 100).toFixed(2)), backgroundColor: PALETTE.green, borderRadius: 6 }],
  };
  const lo = Math.min(...METRICS.map(([m]) => Math.min(cmp.before.metrics[m], cmp.after.metrics[m]))) * 100;
  const perfOpts = { ...base, scales: { ...base.scales, y: { ...base.scales.y, beginAtZero: false, min: Math.max(0, Math.floor(lo - 10)), max: 100 } } };
  const time = { labels: ["Before SVD", "After SVD"], datasets: [{ label: "Training time (s)", data: [cmp.before.train_seconds, cmp.after.train_seconds], backgroundColor: ["#94a3b8", PALETTE.green], borderRadius: 6 }] };
  const sc = svd.pc_scatter;
  const scatter = sc.c ? { datasets: [0, 1].map((c) => ({ label: c ? "Irrigation needed" : "Not needed", backgroundColor: c ? PALETTE.blue : PALETTE.green, pointRadius: 3,
    data: sc.x.map((x, i) => ({ x, y: sc.y[i], c: sc.c[i] })).filter((d) => d.c === c) })) } : null;
  const noLegend = { ...base, plugins: { ...base.plugins, legend: { display: false } } };

  return (
    <div className="space-y-6">
      <div className="glass p-5">
        <h3 className="flex items-center gap-2 font-bold"><Sigma className="h-5 w-5 text-leaf-600" />Singular Value Decomposition: X = U · Σ · Vᵀ</h3>
        <ul className="mt-2 grid gap-1 text-sm text-slate-600 sm:grid-cols-3 dark:text-slate-300">
          <li>• <b>U</b> ({svd.shapes.U.join(" × ")}): every record in the new component space</li>
          <li>• <b>Σ</b>: the singular values, i.e. how much each component matters</li>
          <li>• <b>Vᵀ</b> ({svd.shapes.Vt.join(" × ")}): how each original feature contributes to each component</li>
        </ul>
        <p className="mt-2 text-xs text-slate-500">All numeric features of your file are standardised first, then decomposed with SciPy. The first {k} component(s) that keep at least {thr * 100}% of the variance
          become SVM inputs together with the PDE features. SVD removes redundant features, filters noise in the weak components, shortens training and gives the SVM compact, uncorrelated inputs. The PDE keeps using the original soil moisture, rainfall, temperature and irrigation values.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card icon={Boxes} label="Before SVD" value={`${p} features`} sub={svd.features.join(", ")} tone="from-slate-500 to-slate-400" />
        <Card icon={Layers} label="After SVD" value={`${k} component${k > 1 ? "s" : ""}`} sub={svd.reduced ? `${p - k} fewer inputs` : "no component could be dropped"} />
        <Card icon={Percent} label="Variance preserved" value={`${(svd.variance_preserved * 100).toFixed(1)}%`} sub={`reconstruction error ${(svd.reconstruction_error_reduced * 100).toFixed(1)}%`} tone="from-sky-500 to-cyan-400" />
        <Card icon={Sigma} label="Singular values" value={svd.singular_values.slice(0, 3).map((v) => v.toFixed(1)).join(" · ")} sub={svd.condition_number ? `condition number ${svd.condition_number.toFixed(1)}` : ""} tone="from-amber-500 to-yellow-400" />
      </div>
      {!svd.reduced && (
        <div className="glass !border-amber-400/60 p-4 text-sm">With only {p} numeric feature(s) that are not strongly correlated, every component is needed to keep {thr * 100}% of the variance, so SVD cannot reduce the feature count for this file.
          It becomes useful when the file has many sensors, some of them redundant (for example two temperature sensors).</div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Scree plot" subtitle="Singular values in decreasing order; the elbow shows where components stop adding information" height="h-72"><Line data={scree} options={noLegend} /></ChartCard>
        <ChartCard title="Explained variance" subtitle={`Blue = kept components, grey = dropped; the orange line is the cumulative total`} height="h-72"><Bar data={explained} options={{ ...base, scales: { ...base.scales, y: { ...base.scales.y, max: 100 } } }} /></ChartCard>
        <ChartCard title="Singular value distribution" subtitle="Share of each singular value in the total" height="h-72"><Bar data={sigmaShare} options={noLegend} /></ChartCard>
        <ChartCard title="Feature reduction comparison" subtitle="Number of features and variance kept, before and after SVD" height="h-72"><Bar data={reduction} options={base} /></ChartCard>
        <ChartCard title="Feature contribution" subtitle="How much each original feature shapes the kept components (Vᵀ, weighted by variance)" height="h-72"><Bar data={dist} options={noLegend} /></ChartCard>
        {scatter && <ChartCard title="First two components" subtitle="Records projected on PC1 and PC2 (U · Σ), coloured by irrigation need" height="h-72"><Scatter data={scatter} options={{ ...base, interaction: { mode: "nearest" } }} /></ChartCard>}
      </div>

      <ChartCard title="Loadings (Vᵀ)" subtitle="Contribution of each feature to each kept component; green = positive, red = negative" height="h-auto"><Loadings svd={svd} /></ChartCard>

      <div className="glass p-5">
        <h3 className="flex items-center gap-2 font-bold"><ArrowRight className="h-5 w-5 text-leaf-600" />SVM performance: before vs after SVD</h3>
        <p className="mt-1 text-sm text-slate-500">Same train/test split, same grid search. Both models also receive {cmp.extra_inputs.join(", ")}. The model used for predictions is the SVD one.</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full">
            <thead><tr>{["", "Accuracy", "Precision", "Recall", "F1 score", "Training time", "SVM inputs"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody>
              {[["Before SVD", cmp.before], ["After SVD", cmp.after]].map(([name, m]) => (
                <tr key={name} className="border-t border-slate-100 dark:border-slate-800"><td className="td font-semibold">{name}</td>
                  {METRICS.map(([key]) => <td key={key} className="td">{(m.metrics[key] * 100).toFixed(1)}%</td>)}<td className="td">{m.train_seconds} s</td><td className="td">{m.n_inputs}</td></tr>
              ))}
              <tr className="border-t-2 border-slate-200 dark:border-slate-700"><td className="td font-semibold">Change</td>
                {METRICS.map(([key]) => <td key={key} className="td"><Delta v={cmp.change[key] * 100} /></td>)}
                <td className="td">{cmp.time_ratio !== null && <Delta v={(cmp.time_ratio - 1) * 100} unit="%" good="down" />}</td>
                <td className="td">{cmp.after.n_inputs - cmp.before.n_inputs}</td></tr>
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          {cmp.change.accuracy > 0 ? <TrendingUp className="h-4 w-4 text-leaf-600" /> : <TrendingDown className="h-4 w-4 text-red-500" />}
          <span>Accuracy {Math.abs(cmp.change.accuracy) < 0.0005 ? "stayed the same" : cmp.change.accuracy > 0 ? "improved by" : "decreased by"} {Math.abs(cmp.change.accuracy) >= 0.0005 && <Delta v={cmp.change.accuracy * 100} />} and training time changed by {cmp.time_ratio !== null ? <Delta v={(cmp.time_ratio - 1) * 100} unit="%" good="down" /> : "-"}. These are measured on your data: SVD helps most when many features are redundant, and may not change the result when there are few.</span>
        </div>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Accuracy, precision, recall and F1" subtitle="Before vs after SVD (%)" height="h-72"><Bar data={perf} options={perfOpts} /></ChartCard>
        <ChartCard title="Training time" subtitle="Grid search + final fit, in seconds" height="h-72"><Bar data={time} options={noLegend} /></ChartCard>
      </div>
    </div>
  );
}
