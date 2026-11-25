const COLORS = { temperature: "#f97316", humidity: "#0ea5e9", soil_moisture: "#a16207", rainfall: "#6366f1" };

/** One SVG box plot per variable (each has its own scale because the units differ). */
function Box({ stats, color, label, unit }) {
  const { min, max, q1, median, q3, whisker_low: wl, whisker_high: wh, outliers } = stats;
  const H = 150, top = 12, bottom = H - 12;
  const span = max - min || 1;
  const y = (v) => bottom - ((v - min) / span) * (bottom - top);
  const f = (v) => Number(v).toFixed(1);
  return (
    <div className="text-center">
      <svg viewBox="0 0 120 160" className="mx-auto h-44 w-full max-w-[150px]" role="img" aria-label={`${label} box plot`}>
        <line x1="60" x2="60" y1={y(wh)} y2={y(wl)} stroke={color} strokeWidth="2" />
        <line x1="45" x2="75" y1={y(wh)} y2={y(wh)} stroke={color} strokeWidth="2" />
        <line x1="45" x2="75" y1={y(wl)} y2={y(wl)} stroke={color} strokeWidth="2" />
        <rect x="35" width="50" y={y(q3)} height={Math.max(2, y(q1) - y(q3))} rx="5" fill={color} fillOpacity=".35" stroke={color} strokeWidth="2" />
        <line x1="35" x2="85" y1={y(median)} y2={y(median)} stroke={color} strokeWidth="3.5" />
        <text x="92" y={y(wh) + 3} fontSize="9" fill="currentColor" opacity=".7">{f(wh)}</text>
        <text x="92" y={y(median) + 3} fontSize="9" fill="currentColor" fontWeight="700">{f(median)}</text>
        <text x="92" y={y(wl) + 3} fontSize="9" fill="currentColor" opacity=".7">{f(wl)}</text>
      </svg>
      <p className="text-sm font-bold">{label}</p>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">Q1 {f(q1)} · Q3 {f(q3)} {unit}</p>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">{outliers} outlier{outliers === 1 ? "" : "s"}</p>
    </div>
  );
}

export default function BoxPlots({ boxplots, labels, units }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {Object.keys(boxplots).map((k) => (
        <Box key={k} stats={boxplots[k]} color={COLORS[k]} label={labels[k]} unit={units[k]} />
      ))}
    </div>
  );
}
