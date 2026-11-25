import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CloudUpload, Copy, Database, FileSpreadsheet, HardDrive, RefreshCw, Rows3, Columns3, SearchX } from "lucide-react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";
import { setActiveDataset, fmt } from "../utils/active";
import CleaningSteps from "../components/CleaningSteps";

const ROLES = [
  ["date", "Date *"], ["temperature", "Temperature *"], ["humidity", "Humidity *"], ["soil_moisture", "Soil moisture *"], ["rainfall", "Rainfall *"],
  ["crop", "Crop type (optional)"], ["target", "Irrigation needed label (optional)"],
];

function InfoCard({ icon: Icon, label, value, sub, warn }) {
  return (
    <div className="glass glass-hover p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
        <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${warn ? "bg-amber-100 text-amber-600 dark:bg-amber-900/30" : "bg-leaf-100 text-leaf-600 dark:bg-leaf-900/40"}`}><Icon className="h-5 w-5" /></span>
      </div>
      <p className="mt-2 text-2xl font-extrabold">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export default function Upload() {
  const toast = useToast();
  const navigate = useNavigate();
  const fileInput = useRef(null);
  const timer = useRef(null);
  const [drag, setDrag] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | uploading | analyzing | error
  const [uploadPct, setUploadPct] = useState(0);
  const [up, setUp] = useState(null); // { id, info, mapping, columns }
  const [mapping, setMapping] = useState({});
  const [threshold, setThreshold] = useState("");
  const [prog, setProg] = useState({ percent: 0, step: "", steps: [] });
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");

  useEffect(() => () => clearInterval(timer.current), []);

  const poll = useCallback((id) => {
    clearInterval(timer.current);
    timer.current = setInterval(async () => {
      try {
        const s = await api.datasetStatus(id);
        if (s.status === "analyzing") setProg({ percent: s.percent, step: s.step, steps: s.steps });
        else if (s.status === "done") {
          clearInterval(timer.current);
          setProg((p) => ({ ...p, percent: 100, step: "Analysis complete" }));
          setActiveDataset(id);
          toast.success("Analysis complete. Opening your results…");
          setTimeout(() => navigate(`/analysis/${id}`), 900);
        } else if (s.status === "error") {
          clearInterval(timer.current);
          setError(s.error || "The analysis failed.");
          setPhase("error");
          toast.error("The analysis could not be completed.");
        }
      } catch (e) {
        clearInterval(timer.current);
        setError(e.message);
        setPhase("error");
      }
    }, 700);
  }, [navigate, toast]);

  const startAnalysis = async (id, body = {}) => {
    setPhase("analyzing");
    setError("");
    setProg({ percent: 1, step: "Starting…", steps: [] });
    try {
      await api.analyze(id, body);
      poll(id);
    } catch (e) {
      setError(e.message);
      setPhase("error");
    }
  };

  const handleFile = async (file) => {
    if (!file) return;
    const ext = file.name.toLowerCase().split(".").pop();
    if (!["csv", "xlsx"].includes(ext)) return toast.error("Please upload a .csv or .xlsx file.");
    setPhase("uploading");
    setUploadPct(0);
    setUp(null);
    setUploadError("");
    try {
      const d = await api.uploadDataset(file, setUploadPct);
      setUp(d);
      setMapping(d.mapping);
      if (!d.valid) {                       // validation failed: tell the user exactly which columns are missing, do not analyse
        setError(`Required column(s) missing: ${d.missing_required.join(", ")}. The dataset must contain Date, Temperature, Humidity, Soil Moisture and Rainfall.`);
        setPhase("error");
        toast.error("The dataset is missing required columns.");
        return;
      }
      toast.success(`${file.name} is valid - starting analysis.`);
      await startAnalysis(d.id);
    } catch (e) {
      setUploadError(e.message);            // wrong file type, empty, corrupted, too small ...
      toast.error(e.message);
      setPhase("idle");
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const info = up?.info;
  const busy = phase === "uploading" || phase === "analyzing";

  return (
    <div className="page-bg min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <h1 className="text-3xl font-extrabold">Start <span className="gradient-text">Analysis</span></h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400">Upload a real-life dataset. Only your file is analysed: it is validated, cleaned, explored and used to train an SVM.</p>
        {uploadError && (
          <div role="alert" className="glass mt-4 flex gap-3 !border-red-300 p-4">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" /><p>{uploadError}</p>
          </div>
        )}

        {/* ------------------------------------------------ drop zone */}
        {(phase === "idle" || phase === "uploading") && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                      onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
                      onClick={() => !busy && fileInput.current?.click()} role="button" tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && fileInput.current?.click()}
                      className={`glass mt-8 flex cursor-pointer flex-col items-center justify-center gap-4 border-2 border-dashed p-10 text-center sm:p-16 ${
                        drag ? "!border-leaf-500 !bg-leaf-100/70 scale-[1.01] dark:!bg-leaf-900/30" : "!border-leaf-300 dark:!border-slate-600"}`}>
            <input ref={fileInput} type="file" accept=".csv,.xlsx" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
            <motion.span animate={{ y: [0, -8, 0] }} transition={{ repeat: Infinity, duration: 2.2 }}
                         className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-leaf-600 to-emerald-400 text-white shadow-xl">
              <CloudUpload className="h-10 w-10" />
            </motion.span>
            {phase === "uploading" ? (
              <div className="w-full max-w-md">
                <p className="font-semibold">Uploading… {uploadPct}%</p>
                <div className="mt-3 h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                  <div className="h-full rounded-full bg-gradient-to-r from-leaf-500 to-emerald-400 transition-all" style={{ width: `${uploadPct}%` }} />
                </div>
              </div>
            ) : (
              <>
                <div>
                  <p className="text-xl font-bold">Drag &amp; drop your dataset here</p>
                  <p className="mt-1 text-slate-500 dark:text-slate-400">or click to browse · <b>.csv</b> or <b>.xlsx</b> · up to 25 MB</p>
                </div>
                <button type="button" className="btn-primary" onClick={(e) => { e.stopPropagation(); fileInput.current?.click(); }}>
                  <FileSpreadsheet className="h-5 w-5" /> Choose file
                </button>
              </>
            )}
          </motion.div>
        )}

        {(phase === "idle") && (
          <div className="mt-6 grid gap-4 text-sm text-slate-600 sm:grid-cols-3 dark:text-slate-300">
            {[["Required columns", "Date, Temperature, Humidity, Soil Moisture and Rainfall. Names like Temp, RH, Rain or Soil Moist are recognised automatically."],
              ["Validated first", "The file type, empty or corrupted files, missing columns, duplicate rows and missing values are checked before anything is analysed."],
              ["Optional columns", "Any other numeric sensor columns are picked up for the SVD feature reduction. A crop column and an irrigation-needed (Yes/No) column are used when present. Without the label, one is derived from your own soil-moisture values and marked as derived."]].map(([t, d]) => (
              <div key={t} className="glass p-4"><p className="font-bold text-leaf-700 dark:text-leaf-300">{t}</p><p className="mt-1">{d}</p></div>
            ))}
          </div>
        )}

        {/* ------------------------------------------------ file information */}
        <AnimatePresence>
          {info && (
            <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-8">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h2 className="flex items-center gap-2 text-xl font-bold"><Database className="h-5 w-5 text-leaf-600" />{info.filename}</h2>
                {phase === "error" && <button className="btn-ghost !py-2 text-sm" onClick={() => { setPhase("idle"); setUp(null); }}><RefreshCw className="h-4 w-4" />Upload a different file</button>}
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <InfoCard icon={Rows3} label="Rows" value={fmt(info.rows)} />
                <InfoCard icon={Columns3} label="Columns" value={fmt(info.columns)} />
                <InfoCard icon={SearchX} label="Missing values" value={fmt(info.missing_cells)} sub={`${info.missing_percent}% of cells`} warn={info.missing_cells > 0} />
                <InfoCard icon={Copy} label="Duplicate records" value={fmt(info.duplicates)} warn={info.duplicates > 0} />
                <InfoCard icon={HardDrive} label="Dataset size" value={info.size_human} />
              </div>

              <div className="glass mt-5 overflow-hidden">
                <div className="border-b border-white/40 px-5 py-3 font-bold dark:border-white/10">Dataset preview <span className="text-xs font-normal text-slate-500">(first 10 rows)</span></div>
                <div className="max-h-72 overflow-auto">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-leaf-50 dark:bg-slate-800"><tr>{info.column_info.map((c) => <th key={c.name} className="th">{c.name}<span className="ml-1 normal-case text-slate-400">({c.dtype})</span></th>)}</tr></thead>
                    <tbody>
                      {info.preview.map((row, i) => (
                        <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
                          {info.column_info.map((c) => <td key={c.name} className={`td ${row[c.name] === null ? "text-amber-500" : ""}`}>{row[c.name] === null ? "missing" : String(row[c.name])}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* ------------------------------------------------ live analysis */}
        {(phase === "analyzing") && (
          <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-8">
            <div className="glass p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Analysing your dataset…</h2>
                <span className="text-2xl font-extrabold text-leaf-600">{prog.percent}%</span>
              </div>
              <p className="mt-1 text-sm text-slate-500">{prog.step}</p>
              <div className="mt-4 h-4 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                <motion.div className="h-full rounded-full bg-gradient-to-r from-leaf-500 via-emerald-400 to-sky-400" animate={{ width: `${prog.percent}%` }} transition={{ duration: 0.5 }} />
              </div>
            </div>
            <div className="mt-4"><CleaningSteps steps={prog.steps} compact /></div>
          </motion.section>
        )}

        {/* ------------------------------------------------ error + column mapping */}
        {phase === "error" && up && (
          <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-8">
            <div className="glass !border-red-300 p-6">
              <div className="flex gap-3">
                <AlertTriangle className="mt-1 h-6 w-6 shrink-0 text-red-500" />
                <div><h2 className="text-lg font-bold">This dataset cannot be analysed yet</h2><p className="mt-1 text-slate-600 dark:text-slate-300">{error}</p></div>
              </div>
              <h3 className="mt-5 font-bold">Tell us which column is which</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {ROLES.map(([role, label]) => (
                  <div key={role}>
                    <label className="label" htmlFor={`map-${role}`}>{label}</label>
                    <select id={`map-${role}`} className="input" value={mapping[role] || ""} onChange={(e) => setMapping({ ...mapping, [role]: e.target.value || null })}>
                      <option value="">— none —</option>
                      {up.columns.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                ))}
              </div>
              {!mapping.target && (
                <div className="mt-4 max-w-sm">
                  <label className="label" htmlFor="thr">No label column: irrigation needed when the next soil moisture reading is below (%)</label>
                  <input id="thr" className="input" type="number" min="0" max="100" placeholder="auto (lowest third of your soil moisture values)" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
                </div>
              )}
              <button className="btn-primary mt-5" onClick={() => startAnalysis(up.id, { mapping, derive_threshold: threshold })}><RefreshCw className="h-4 w-4" />Analyse again</button>
            </div>
          </motion.section>
        )}
      </div>
    </div>
  );
}
