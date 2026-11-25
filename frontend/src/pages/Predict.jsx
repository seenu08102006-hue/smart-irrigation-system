import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { BrainCircuit, CheckCircle2, CloudRain, CloudUpload, Database, Droplet, Gauge, Thermometer, Waves, Wheat, XCircle } from "lucide-react";
import { api } from "../api";
import Loader from "../components/Loader";
import { useToast } from "../context/ToastContext";
import { fmt, useActiveDataset } from "../utils/active";

const FIELDS = [
  { key: "temperature", label: "Temperature", unit: "°C", icon: Thermometer, color: "text-orange-500 bg-orange-100 dark:bg-orange-900/30" },
  { key: "humidity", label: "Humidity", unit: "%", icon: Droplet, color: "text-sky-500 bg-sky-100 dark:bg-sky-900/30" },
  { key: "soil_moisture", label: "Soil Moisture", unit: "%", icon: Waves, color: "text-amber-700 bg-amber-100 dark:bg-amber-900/30" },
  { key: "rainfall", label: "Rainfall", unit: "mm", icon: CloudRain, color: "text-indigo-500 bg-indigo-100 dark:bg-indigo-900/30" },
];

function NoData() {
  return (
    <div className="page-bg flex min-h-[60vh] items-center justify-center px-4">
      <div className="glass max-w-lg p-10 text-center">
        <Database className="mx-auto h-12 w-12 text-leaf-500" />
        <p className="mt-4 text-lg font-bold">Please upload a real-life CSV or Excel dataset to begin analysis.</p>
        <p className="mt-1 text-sm text-slate-500">Predictions use the SVM trained on your own uploaded data.</p>
        <Link to="/analyze" className="btn-primary mt-6"><CloudUpload className="h-5 w-5" />Upload Dataset</Link>
      </div>
    </div>
  );
}

export default function Predict() {
  const toast = useToast();
  const [active, setActive] = useActiveDataset();
  const [datasets, setDatasets] = useState(null);
  const [meta, setMeta] = useState(null);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.datasets().then((d) => {
      const done = d.datasets.filter((x) => x.status === "done");
      setDatasets(done);
      if (done.length && !done.some((x) => x.id === active)) setActive(done[0].id);
    }).catch((e) => { toast.error(e.message); setDatasets([]); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!active || !datasets?.some((x) => x.id === active)) return;
    setMeta(null);
    setResult(null);
    api.model(active).then((m) => {
      setMeta(m);
      // start every field at the middle of the range seen in YOUR data (no made-up defaults)
      const f = { crop_type: m.crops[0] || "" };
      m.features.forEach((k) => { f[k] = ((m.observed[k][0] + m.observed[k][1]) / 2).toFixed(1); });
      setForm(f);
    }).catch((e) => toast.error(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, datasets]);

  if (!datasets) return <Loader text="Loading…" />;
  if (!datasets.length) return <NoData />;

  const submit = async (e) => {
    e.preventDefault();
    const body = { crop_type: form.crop_type };
    for (const f of FIELDS) {
      if (form[f.key] === "" || Number.isNaN(Number(form[f.key]))) return toast.error(`${f.label} must be a number.`);
      body[f.key] = Number(form[f.key]);
    }
    setLoading(true);
    setResult(null);
    try {
      const [res] = await Promise.all([api.predict(active, body), new Promise((r) => setTimeout(r, 700))]);
      setResult(res);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const yes = result?.irrigation_required;

  return (
    <div className="page-bg min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        {loading && <Loader fullscreen text="Running your SVM model…" />}
        <h1 className="text-3xl font-extrabold">Irrigation <span className="gradient-text">Prediction</span></h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400">Enter current field conditions. The answer comes from the SVM trained only on your uploaded dataset.</p>

        <div className="glass mt-6 flex flex-wrap items-center gap-4 p-4">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-leaf-600 to-emerald-400 text-white shadow"><BrainCircuit className="h-5 w-5" /></span>
          <div className="min-w-0 flex-1">
            <label className="label" htmlFor="ds">Model trained on</label>
            <select id="ds" className="input" value={active || ""} onChange={(e) => setActive(Number(e.target.value))}>
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name} - accuracy {(d.accuracy * 100).toFixed(1)}%</option>)}
            </select>
          </div>
        </div>

        {!meta ? <Loader text="Loading model…" /> : (
          <form onSubmit={submit} className="glass mt-6 p-6">
            <div className="grid gap-5 sm:grid-cols-2">
              {FIELDS.map(({ key, label, unit, icon: Icon, color }) => (
                <div key={key}>
                  <label className="label flex items-center gap-2" htmlFor={key}>
                    <span className={`flex h-7 w-7 items-center justify-center rounded-lg ${color}`}><Icon className="h-4 w-4" /></span>{label} ({unit})
                  </label>
                  <input id={key} type="number" step="0.1" className="input" value={form[key] ?? ""} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
                  <p className="mt-1 text-xs text-slate-500">Seen in your data: {fmt(meta.observed[key][0], 1)} to {fmt(meta.observed[key][1], 1)} {unit}</p>
                </div>
              ))}
              {meta.crops.length > 0 && (
                <div>
                  <label className="label flex items-center gap-2" htmlFor="crop"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-leaf-100 text-leaf-600 dark:bg-leaf-900/40"><Wheat className="h-4 w-4" /></span>Crop type</label>
                  <select id="crop" className="input" value={form.crop_type || ""} onChange={(e) => setForm({ ...form, crop_type: e.target.value })}>
                    {meta.crops.map((c) => <option key={c}>{c}</option>)}
                  </select>
                </div>
              )}
            </div>
            <button className="btn-primary mt-6 w-full sm:w-auto" disabled={loading}><BrainCircuit className="h-5 w-5" />Predict</button>
          </form>
        )}

        {result && (
          <motion.section initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="mt-8">
            <h2 className="mb-3 text-xl font-bold">Prediction Result</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className={`glass p-5 ${yes ? "!border-red-400" : "!border-leaf-500"}`}>
                <span className={`mb-3 flex h-11 w-11 items-center justify-center rounded-xl text-white shadow ${yes ? "bg-red-500" : "bg-leaf-500"}`}>{yes ? <XCircle className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}</span>
                <p className="text-sm text-slate-500">Irrigation Required</p>
                <p className="text-2xl font-extrabold">{yes ? "Yes" : "No"}</p>
              </div>
              <div className="glass p-5">
                <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500 text-white shadow"><Gauge className="h-5 w-5" /></span>
                <p className="text-sm text-slate-500">Confidence Score</p>
                <p className="text-2xl font-extrabold">{result.confidence}%</p>
              </div>
              <div className="glass p-5">
                <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500 text-white shadow"><BrainCircuit className="h-5 w-5" /></span>
                <p className="text-sm text-slate-500">Probability irrigation is needed</p>
                <p className="text-2xl font-extrabold">{result.probability_yes}%</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500">Model: SVM trained on {result.model_name}. {meta?.metrics && `Its test accuracy was ${(meta.metrics.accuracy * 100).toFixed(1)}%.`}</p>
          </motion.section>
        )}
      </div>
    </div>
  );
}
