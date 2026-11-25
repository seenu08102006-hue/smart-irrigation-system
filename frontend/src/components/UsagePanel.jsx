import { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import { BatteryCharging, Coins, Droplets, Info, Power, Save, Timer } from "lucide-react";
import "../charts";
import { PALETTE, baseOptions } from "../charts";
import { api } from "../api";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import ChartCard from "./ChartCard";
import { fmt } from "../utils/active";

const FIELDS = [
  ["area_m2", "Field area (m²)", true], ["root_depth_mm", "Root-zone depth (mm)", true], ["pump_kw", "Pump power (kW)", true],
  ["flow_lph", "Pump flow (litres per hour)", true], ["baseline_hours", "Hours the pump runs per day today (optional)", false],
  ["tariff", "Electricity price per kWh (optional)", false],
];

function Kpi({ icon: Icon, label, value, sub, tone = "from-leaf-500 to-emerald-400" }) {
  return (
    <div className="glass p-4">
      <span className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow ${tone}`}><Icon className="h-5 w-5" /></span>
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-extrabold">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

/** Water and electricity of the pump. The field and pump values are typed in by the user: a weather file cannot contain them. */
export default function UsagePanel({ datasetId }) {
  const { dark } = useTheme();
  const toast = useToast();
  const [state, setState] = useState(null);
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.usage(datasetId).then((d) => { setState(d); setForm(d.params || {}); }).catch((e) => toast.error(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const d = await api.saveSystem(datasetId, form);
      setState((s) => ({ ...s, ...d }));
      toast.success("Field and pump data saved. Water and electricity updated.");
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  if (!state) return null;
  const us = state.usage, b = us?.baseline;
  const labels = us?.monthly.labels || [];
  const mk = (key, color, baseKey, baseColor, unit) => ({
    labels,
    datasets: [
      { label: `With SVM + PDE control (${unit})`, data: us.monthly[key], backgroundColor: color, borderRadius: 6 },
      ...(b ? [{ label: `Current practice (${unit})`, data: b[baseKey], backgroundColor: baseColor, borderRadius: 6 }] : []),
    ],
  });

  return (
    <div className="space-y-6">
      <form onSubmit={save} className="glass p-5">
        <h3 className="flex items-center gap-2 font-bold"><Power className="h-5 w-5 text-leaf-600" />Your field and pump</h3>
        <p className="mt-1 flex gap-2 text-sm text-slate-500"><Info className="mt-0.5 h-4 w-4 shrink-0" />
          Weather and soil readings cannot tell the litres or kWh of your pump, so enter your own values. Nothing is assumed: until you do, no water or electricity is shown.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FIELDS.map(([k, label, req]) => (
            <div key={k}>
              <label className="label" htmlFor={`sys-${k}`}>{label}</label>
              <input id={`sys-${k}`} type="number" step="any" min="0" required={req} className="input" value={form[k] ?? ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            </div>
          ))}
        </div>
        <button className="btn-primary mt-5" disabled={busy}><Save className="h-4 w-4" />{busy ? "Saving…" : "Save and calculate"}</button>
        <p className="mt-3 text-xs text-slate-500">Water (L) = moisture deficit ÷ 100 × root depth (mm) × area (m²), on the days the SVM switches the pump ON. The deficit is the gap between the upper operating
          level ({fmt(state.levels?.target, 1) || "75th percentile of your soil moisture"}) and the PDE's moisture for the next day. Electricity (kWh) = litres ÷ flow × power.</p>
      </form>

      {!us ? (
        <div className="glass p-8 text-center text-slate-500">Enter the field and pump values above to see water usage and electricity optimisation.</div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi icon={Timer} label="Pump ON" value={`${us.pump_on_days} days`} sub={`${us.pump_on_percent}% of ${us.days} days · ${us.pump_hours} h`} tone="from-amber-500 to-yellow-400" />
            <Kpi icon={Droplets} label="Water used" value={`${fmt(us.water_litres)} L`} sub="over the uploaded period" tone="from-sky-500 to-cyan-400" />
            <Kpi icon={BatteryCharging} label="Electricity used" value={`${fmt(us.electricity_kwh, 1)} kWh`} sub="pump energy" />
            {b ? <Kpi icon={BatteryCharging} label="Electricity saved" value={`${fmt(b.saved_kwh, 1)} kWh`} sub={b.saved_percent !== null ? `${b.saved_percent}% vs ${b.hours_per_day} h/day` : ""} tone="from-violet-500 to-fuchsia-400" />
              : <Kpi icon={Coins} label="Cost" value={us.cost !== null ? fmt(us.cost, 2) : "-"} sub="needs the price per kWh" tone="from-slate-500 to-slate-400" />}
          </div>
          {b && <p className="glass p-4 text-sm">Compared with running the pump <b>{b.hours_per_day} h every day</b> (your figure): {fmt(b.electricity_kwh, 1)} kWh and {fmt(b.water_litres)} L; saving <b>{fmt(b.saved_kwh, 1)} kWh</b>{b.saved_percent !== null && ` (${b.saved_percent}%)`} and <b>{fmt(b.saved_litres)} L</b>.
            {us.cost !== null && <> Electricity cost {fmt(us.cost, 2)}.</>}</p>}
          <div className="grid gap-5 lg:grid-cols-2">
            <ChartCard title="Water usage per month" subtitle="Litres" height="h-72"><Bar data={mk("water", PALETTE.blue, "monthly_baseline_water", "#cbd5e1", "L")} options={baseOptions(dark)} /></ChartCard>
            <ChartCard title="Electricity per month" subtitle="kWh" height="h-72"><Bar data={mk("electricity", PALETTE.amber, "monthly_baseline_electricity", "#cbd5e1", "kWh")} options={baseOptions(dark)} /></ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
