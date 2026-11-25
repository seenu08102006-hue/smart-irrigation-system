import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { BrainCircuit, CheckCircle2, CloudUpload, Database, Loader2, Trash2, XCircle } from "lucide-react";
import { api } from "../api";
import Loader from "../components/Loader";
import { useToast } from "../context/ToastContext";
import { fmt, useActiveDataset } from "../utils/active";

const BADGE = {
  done: ["bg-leaf-100 text-leaf-700 dark:bg-leaf-900/40 dark:text-leaf-300", CheckCircle2, "Analysed"],
  analyzing: ["bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300", Loader2, "Analysing"],
  error: ["bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300", XCircle, "Failed"],
  uploaded: ["bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300", Database, "Uploaded"],
};

export default function Datasets() {
  const toast = useToast();
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);
  const [active, setActive] = useActiveDataset();

  const load = () => api.datasets().then((d) => setRows(d.datasets)).catch((e) => toast.error(e.message));
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const remove = async (id) => {
    if (!window.confirm("Delete this dataset, its trained model and report data?")) return;
    try { await api.deleteDataset(id); if (active === id) setActive(null); toast.success("Dataset deleted."); load(); }
    catch (e) { toast.error(e.message); }
  };
  const use = (id) => { setActive(id); toast.success("This dataset's SVM is now used for predictions and the dashboard."); };

  if (!rows) return <Loader text="Loading datasets…" />;

  return (
    <div className="page-bg min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold">My <span className="gradient-text">Datasets</span></h1>
            <p className="mt-1 text-slate-500 dark:text-slate-400">Every dataset you uploaded, with its trained SVM model.</p>
          </div>
          <Link to="/analyze" className="btn-primary"><CloudUpload className="h-5 w-5" />Start Analysis</Link>
        </div>

        {rows.length === 0 ? (
          <div className="glass p-12 text-center">
            <Database className="mx-auto h-12 w-12 text-leaf-500" />
            <p className="mt-3 text-lg font-bold">No datasets yet</p>
            <p className="text-slate-500">Upload a CSV or Excel file to analyse it and train an SVM.</p>
            <Link to="/analyze" className="btn-primary mt-5">Upload dataset</Link>
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {rows.map((d, i) => {
              const [cls, Icon, label] = BADGE[d.status] || BADGE.uploaded;
              const isActive = active === d.id;
              return (
                <motion.div key={d.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                            className={`glass glass-hover p-5 ${isActive ? "!border-leaf-500 ring-2 ring-leaf-500/40" : ""}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0"><h3 className="truncate font-bold" title={d.name}>{d.name}</h3><p className="text-xs text-slate-500">{d.uploaded_at}</p></div>
                    <span className={`flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${cls}`}><Icon className={`h-3.5 w-3.5 ${d.status === "analyzing" ? "animate-spin" : ""}`} />{label}</span>
                  </div>
                  <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                    {[["Rows", fmt(d.n_rows)], ["Cols", d.n_cols], ["Accuracy", d.accuracy != null ? `${(d.accuracy * 100).toFixed(1)}%` : "-"], ["Predictions", d.predictions]].map(([l, v]) => (
                      <div key={l} className="rounded-lg bg-white/60 p-2 dark:bg-slate-800/60"><p className="text-[10px] uppercase text-slate-500">{l}</p><p className="font-extrabold">{v}</p></div>
                    ))}
                  </div>
                  {d.error && <p className="mt-3 text-xs text-red-500">{d.error}</p>}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {d.status === "done" && (
                      <>
                        <button className="btn-outline !px-3 !py-1.5 text-sm" onClick={() => navigate(`/analysis/${d.id}`)}>View analysis</button>
                        <button className={`${isActive ? "btn-primary" : "btn-ghost"} !px-3 !py-1.5 text-sm`} onClick={() => use(d.id)}><BrainCircuit className="h-4 w-4" />{isActive ? "In use" : "Use model"}</button>
                      </>
                    )}
                    <button className="btn-ghost !px-3 !py-1.5 text-sm text-red-500" onClick={() => remove(d.id)} aria-label="Delete dataset"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
