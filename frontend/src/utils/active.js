import { useEffect, useState } from "react";

// The "active dataset" is the uploaded dataset whose SVM model is used for predictions and shown on the dashboard.
const KEY = "activeDataset";
const EVENT = "active-dataset-changed";

export function getActiveDataset() {
  try { return Number(localStorage.getItem(KEY)) || null; } catch { return null; }
}

export function setActiveDataset(id) {
  try { id ? localStorage.setItem(KEY, String(id)) : localStorage.removeItem(KEY); } catch { /* storage blocked */ }
  window.dispatchEvent(new Event(EVENT));
}

export function useActiveDataset() {
  const [id, setId] = useState(getActiveDataset());
  useEffect(() => {
    const on = () => setId(getActiveDataset());
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);
  return [id, setActiveDataset];
}

export const fmt = (n, d = 0) =>
  n === null || n === undefined || Number.isNaN(n) ? "-" : Number(n).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: 0 });
