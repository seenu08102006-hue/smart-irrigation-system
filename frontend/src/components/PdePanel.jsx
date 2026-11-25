import { useState } from "react";
import { Line } from "react-chartjs-2";
import { Activity, Droplets, Gauge, Layers, Sigma } from "lucide-react";
import "../charts";
import { PALETTE, baseOptions } from "../charts";
import { useTheme } from "../context/ThemeContext";
import ChartCard from "./ChartCard";
import { fmt } from "../utils/active";

const lineOpts = (dark, extra = {}) => ({
  ...baseOptions(dark, { plugins: { legend: { labels: { color: dark ? "#cbd5e1" : "#475569", usePointStyle: true } } }, ...extra }),
});
const noZero = (o) => ({ ...o, scales: { ...o.scales, y: { ...o.scales.y, beginAtZero: false, title: { display: true, text: "Soil moisture (%)" } },
  x: { ...o.scales.x, ticks: { ...o.scales.x.ticks, maxTicksLimit: 8 } } } });

function Stat({ icon: Icon, label, value, sub }) {
  return (
    <div className="glass p-4">
      <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-leaf-100 text-leaf-600 dark:bg-leaf-900/40"><Icon className="h-5 w-5" /></span>
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-extrabold">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

/** Soil moisture as a colour grid: x = day, y = depth (0 = surface, 1 = bottom). Plain SVG. */
function Distribution({ heat }) {
  const v = heat.values, days = v.length, cells = heat.depth_cells;
  const flat = v.flat();
  const lo = Math.min(...flat), hi = Math.max(...flat);
  const col = (x) => {
    const t = hi === lo ? 0.5 : (x - lo) / (hi - lo);
    return `hsl(${48 + 170 * t}, ${55 + 25 * t}%, ${88 - 48 * t}%)`;            // dry = pale yellow, wet = deep blue
  };
  const W = 800, H = 240, cw = W / days, ch = H / cells;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-lg" preserveAspectRatio="none" role="img" aria-label="Soil moisture by depth and day">
        {v.map((column, i) => column.map((x, j) => (
          <rect key={`${i}-${j}`} x={i * cw} y={j * ch} width={cw + 0.3} height={ch + 0.3} fill={col(x)}>
            <title>{`${heat.dates[i]}, depth ${(j / cells).toFixed(2)}: ${x}%`}</title>
          </rect>
        )))}
      </svg>
      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
        <span>{heat.dates[0]}</span><span>top = surface, bottom = deep layer</span><span>{heat.dates[days - 1]}</span>
      </div>
      <div className="mt-2 flex items-center justify-center gap-2 text-[11px] text-slate-500">
        <span>{lo.toFixed(1)}%</span>
        <span className="h-2 w-40 rounded-full" style={{ background: `linear-gradient(90deg, ${col(lo)}, ${col((lo + hi) / 2)}, ${col(hi)})` }} />
        <span>{hi.toFixed(1)}%</span>
      </div>
    </div>
  );
}

export default function PdePanel({ r }) {
  const { dark } = useTheme();
  const pde = r.pde, p = pde.params, m = pde.metrics, fc = pde.forecast;
  const [scen, setScen] = useState("No rain");

  const fit = {
    labels: pde.fit.dates,
    datasets: [
      { label: "Observed (uploaded)", data: pde.fit.observed, borderColor: "#a16207", pointRadius: 0, borderWidth: 2, tension: 0.2 },
      { label: "PDE one-day-ahead", data: pde.fit.pde, borderColor: PALETTE.green, pointRadius: 0, borderWidth: 2, tension: 0.2 },
    ],
  };
  const ctxN = fc.context.dates.length;
  const labels = [...fc.context.dates, ...fc.dates];
  const pad = (arr, startAt) => [...Array(startAt).fill(null), ...arr];
  const forecast = {
    labels,
    datasets: [
      { label: "Observed", data: [...fc.context.observed, ...Array(fc.dates.length).fill(null)], borderColor: "#a16207", pointRadius: 0, borderWidth: 2 },
      ...["No rain", "Average rain"].map((name, i) => ({
        label: `PDE forecast - ${name}`, data: pad([fc.context.observed[ctxN - 1], ...fc.scenarios[name].mean], ctxN - 1),
        borderColor: i ? PALETTE.blue : PALETTE.red, borderDash: [6, 4], pointRadius: 3, borderWidth: 2, spanGaps: true })),
      { label: `Dry level (${fmt(fc.dry_level, 1)}%)`, data: labels.map(() => fc.dry_level), borderColor: PALETTE.slate, borderDash: [2, 4], pointRadius: 0, borderWidth: 1 },
    ],
  };
  const S = fc.scenarios[scen];
  const shades = ["#a16207", "#16a34a", "#0ea5e9", "#6366f1"];
  const profDays = ["0", "1", "3", "7"].filter((d) => S.profiles[d]);
  const nz = pde.nz;
  const profile = {
    labels: Array.from({ length: nz }, (_, i) => ((i + 0.5) / nz).toFixed(2)),
    datasets: profDays.map((d, i) => ({ label: d === "0" ? "Today (start)" : `Day +${d}`, data: S.profiles[d], borderColor: shades[i], pointRadius: 0, borderWidth: 2, tension: 0.3 })),
  };
  const profOpts = noZero(lineOpts(dark));
  profOpts.scales.x = { ...profOpts.scales.x, title: { display: true, text: "Depth (0 = surface, 1 = bottom)" } };

  return (
    <div className="space-y-6">
      <div className="glass p-5">
        <h3 className="flex items-center gap-2 font-bold"><Sigma className="h-5 w-5 text-leaf-600" />The soil-moisture PDE</h3>
        <p className="mt-2 font-mono text-sm">∂θ/∂t = D · ∂²θ/∂z²</p>
        <ul className="mt-2 grid gap-1 text-sm text-slate-600 sm:grid-cols-2 dark:text-slate-300">
          <li>• Surface inflow: <b>α · Rainfall</b>{pde.uses_irrigation && <> + <b>β · Irrigation</b></>}</li>
          <li>• Surface loss (evaporation): <b>k<sub>e</sub> · T · (1 − Humidity/100) · θ</b></li>
          <li>• Bottom loss (drainage): <b>k<sub>d</sub> · θ</b></li>
          <li>• Solved by finite volumes ({pde.nz} cells) + implicit Euler ({pde.substeps} steps/day)</li>
        </ul>
        <p className="mt-2 text-xs text-slate-500">θ is soil moisture (%). Your soil-moisture reading is treated as the root-zone average. D, α, k<sub>e</sub>, k<sub>d</sub>{pde.uses_irrigation && " and β"} were fitted
          with least squares so that the PDE reproduces your own readings one day ahead ({m.pairs.toLocaleString()} consecutive days).{!pde.uses_irrigation && " The file has no irrigation column, so irrigation is not part of the fit."}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[["D", "Diffusion", p.D], ["α", "Rain gain (% per mm)", p.alpha], ["kₑ", "Evaporation", p.k_e], ["k_d", "Drainage", p.k_d], ["β", "Irrigation gain (%)", pde.uses_irrigation ? p.beta : null]].map(([sym, name, v]) => (
          <div key={sym} className="glass p-4"><p className="text-xs text-slate-500">{name}</p><p className="text-2xl font-extrabold">{sym} = {v === null ? "n/a" : Number(v).toPrecision(3)}</p></div>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Gauge} label="PDE error (RMSE)" value={`${m.rmse.toFixed(2)} %`} sub="one day ahead, vs your readings" />
        <Stat icon={Activity} label="'Tomorrow = today' error" value={`${m.persistence_rmse.toFixed(2)} %`} sub="the simple guess to beat" />
        <Stat icon={Droplets} label="Skill vs simple guess" value={`${(m.skill_vs_persistence * 100).toFixed(0)} %`} sub="above 0 = PDE is better" />
        <Stat icon={Layers} label="R² of daily change" value={m.r2_change.toFixed(2)} sub="how much of the daily change it explains" />
      </div>

      <ChartCard title="Moisture trend: PDE versus your readings" subtitle="Each green point is the PDE's estimate for that day, computed from the day before" height="h-72">
        <Line data={fit} options={noZero(lineOpts(dark))} />
      </ChartCard>

      <ChartCard title="Soil-moisture distribution over time" subtitle={`Depth profile from the PDE for the last ${r.pde.heatmap.dates.length} days (profile carried by the PDE, average matched to your reading each day)`} height="h-auto">
        <Distribution heat={pde.heatmap} />
      </ChartCard>

      <ChartCard title={`Soil-moisture forecast for the next ${fc.horizon} days`} height="h-80"
                 subtitle={`Future weather uses only your data: ${fc.assumptions.temperature} °C and ${fc.assumptions.humidity}% humidity (last 7 days); rain 0 mm or your average of ${fc.assumptions.average_rain_mm} mm/day`}>
        <Line data={forecast} options={noZero(lineOpts(dark))} />
      </ChartCard>

      <div className="grid gap-4 sm:grid-cols-2">
        {["No rain", "Average rain"].map((n) => (
          <div key={n} className="glass p-4 text-sm">
            <p className="font-bold">{n}</p>
            <p className="mt-1">Moisture on day +{fc.horizon}: <b>{fmt(fc.scenarios[n].mean[fc.horizon - 1], 1)}%</b></p>
            <p>{fc.scenarios[n].dry_in_days ? <>Reaches the dry level in about <b>{fc.scenarios[n].dry_in_days} day(s)</b>.</> : <>Stays above the dry level ({fmt(fc.dry_level, 1)}%).</>}</p>
          </div>
        ))}
      </div>

      <ChartCard title="Forecast depth profiles" height="h-72" subtitle="How moisture is distributed over depth as the forecast evolves"
                 action={<select aria-label="Scenario" className="input !w-auto !py-1.5 text-sm" value={scen} onChange={(e) => setScen(e.target.value)}>{Object.keys(fc.scenarios).map((k) => <option key={k}>{k}</option>)}</select>}>
        <Line data={profile} options={profOpts} />
      </ChartCard>
    </div>
  );
}
