import {
  ArcElement, BarController, BarElement, CategoryScale, LineController, Chart as ChartJS, Filler, Legend, LinearScale,
  LineElement, PointElement, Tooltip,
} from "chart.js";

// Register only the Chart.js pieces we use (smaller bundle)
ChartJS.register(ArcElement, BarController, BarElement, LineController, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip);

export const PALETTE = {
  green: "#16a34a", greenSoft: "rgba(22,163,74,0.18)",
  blue: "#0ea5e9", blueSoft: "rgba(14,165,233,0.18)",
  amber: "#f59e0b", amberSoft: "rgba(245,158,11,0.18)",
  red: "#ef4444", slate: "#64748b",
};

/** Shared chart options that adapt to dark/light mode. */
export function baseOptions(dark, extra = {}) {
  const text = dark ? "#cbd5e1" : "#475569";
  const grid = dark ? "rgba(148,163,184,.15)" : "rgba(148,163,184,.25)";
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { labels: { color: text, usePointStyle: true } }, tooltip: { padding: 10, cornerRadius: 8 } },
    scales: {
      x: { ticks: { color: text, maxRotation: 0, autoSkip: true }, grid: { display: false } },
      y: { ticks: { color: text }, grid: { color: grid }, beginAtZero: true },
    },
    animation: { duration: 900, easing: "easeOutQuart" },
    ...extra,
  };
}
