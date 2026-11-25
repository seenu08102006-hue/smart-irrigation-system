/** Correlation heatmap drawn with plain CSS (Chart.js has no heatmap). -1 = red, 0 = pale, +1 = green. */
function colour(v) {
  const a = Math.min(1, Math.abs(v));
  return v >= 0 ? `rgba(22,163,74,${0.12 + a * 0.85})` : `rgba(239,68,68,${0.12 + a * 0.85})`;
}

export default function Heatmap({ labels, matrix }) {
  const n = labels.length;
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[420px] gap-1" style={{ gridTemplateColumns: `auto repeat(${n}, minmax(0, 1fr))` }}>
        <div />
        {labels.map((l) => (
          <div key={l} className="truncate px-1 pb-1 text-center text-[11px] font-semibold text-slate-500 dark:text-slate-400" title={l}>{l}</div>
        ))}
        {matrix.map((row, i) => (
          <div key={labels[i]} className="contents">
            <div className="flex items-center pr-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">{labels[i]}</div>
            {row.map((v, j) => (
              <div key={j} title={`${labels[i]} vs ${labels[j]}: ${v.toFixed(3)}`}
                   className="flex aspect-[1.4] items-center justify-center rounded-lg text-xs font-bold text-slate-900 transition hover:scale-105 dark:text-white"
                   style={{ background: colour(v) }}>
                {v.toFixed(2)}
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-center gap-2 text-[11px] text-slate-500">
        <span>-1</span>
        <span className="h-2 w-40 rounded-full" style={{ background: "linear-gradient(90deg, rgba(239,68,68,.9), rgba(241,245,249,.6), rgba(22,163,74,.9))" }} />
        <span>+1</span>
      </div>
    </div>
  );
}
