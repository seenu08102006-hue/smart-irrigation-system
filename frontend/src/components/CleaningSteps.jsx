import { motion } from "framer-motion";
import {
  AlertTriangle, BarChart3, BrainCircuit, CheckCircle2, Copy, Eraser, FileSpreadsheet, Gauge, Loader2,
  Scale, Table2, Target, Wand2, Zap, CircleDashed,
} from "lucide-react";

const ICONS = {
  load: FileSpreadsheet, types: Wand2, duplicates: Copy, invalid: Eraser, missing: CircleDashed, outliers: AlertTriangle,
  target: Target, normalize: Scale, eda: Table2, charts: BarChart3, svm: BrainCircuit, findings: Zap,
};

/** Visual list of every cleaning / analysis step: running spinner, green tick, or amber warning. */
export default function CleaningSteps({ steps, compact = false }) {
  return (
    <ol className="space-y-3">
      {steps.map((s, i) => {
        const Icon = ICONS[s.id] || Gauge;
        const running = s.status === "running";
        const warn = s.status === "warning";
        const m = s.metrics || {};
        return (
          <motion.li key={s.id} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: compact ? 0 : i * 0.05 }}
                     className={`glass flex gap-4 p-4 ${warn ? "!border-amber-400/60" : ""}`}>
            <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white shadow ${
              running ? "bg-sky-500" : warn ? "bg-amber-500" : "bg-gradient-to-br from-leaf-600 to-emerald-400"}`}>
              {running ? <Loader2 className="h-5 w-5 animate-spin" /> : <Icon className="h-5 w-5" />}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="font-bold">{s.title}</h4>
                {running ? <span className="text-xs font-semibold text-sky-500">running…</span>
                  : warn ? <span className="flex items-center gap-1 text-xs font-semibold text-amber-500"><AlertTriangle className="h-3.5 w-3.5" />check</span>
                  : <CheckCircle2 className="h-4 w-4 text-leaf-500" />}
              </div>
              {s.detail && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{s.detail}</p>}
              {!compact && m.before !== undefined && m.after !== undefined && (
                <div className="mt-3">
                  <div className="flex justify-between text-[11px] text-slate-500"><span>before {m.before.toLocaleString()}</span><span>after {m.after.toLocaleString()}</span></div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                    <motion.div className="h-full rounded-full bg-gradient-to-r from-leaf-500 to-emerald-400" initial={{ width: 0 }}
                                animate={{ width: `${(100 * m.after) / Math.max(m.before, 1)}%` }} transition={{ duration: 0.8 }} />
                  </div>
                </div>
              )}
            </div>
          </motion.li>
        );
      })}
    </ol>
  );
}
