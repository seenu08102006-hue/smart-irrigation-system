import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BrainCircuit } from "lucide-react";
import { api } from "../api";
import { fmt } from "../utils/active";

/** Predictions made with the SVM of this dataset. */
export default function HistoryPanel({ datasetId }) {
  const [rows, setRows] = useState(null);
  useEffect(() => { api.predictions(datasetId).then((d) => setRows(d.predictions)).catch(() => setRows([])); }, [datasetId]);
  if (!rows) return null;
  if (!rows.length) {
    return (
      <div className="glass p-10 text-center">
        <BrainCircuit className="mx-auto h-10 w-10 text-leaf-500" />
        <p className="mt-3 font-bold">No predictions yet</p>
        <p className="text-sm text-slate-500">Enter current field conditions on the Predict page; every prediction is saved here.</p>
        <Link to="/predict" className="btn-primary mt-4">Make a prediction</Link>
      </div>
    );
  }
  return (
    <div className="glass overflow-x-auto">
      <table className="w-full">
        <thead><tr>{["Date & time", "Crop", "Temp °C", "Humidity %", "Soil %", "Rain mm", "Prediction", "Pump", "Confidence", "PDE tomorrow %", "Water L", "kWh"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
        <tbody>{rows.map((p) => (
          <tr key={p.id} className="border-t border-slate-100 dark:border-slate-800">
            <td className="td">{p.created_at}</td><td className="td">{p.crop_type || "-"}</td><td className="td">{p.temperature}</td><td className="td">{p.humidity}</td>
            <td className="td">{p.soil_moisture}</td><td className="td">{p.rainfall}</td>
            <td className="td font-semibold">{p.prediction}</td>
            <td className="td"><span className={`rounded-full px-2 py-0.5 text-xs font-bold ${p.pump_status === "ON" ? "bg-red-100 text-red-600" : "bg-leaf-100 text-leaf-700"}`}>{p.pump_status}</span></td>
            <td className="td">{p.confidence}%</td><td className="td">{fmt(p.pde_next, 1)}</td><td className="td">{p.water_litres === null ? "-" : fmt(p.water_litres)}</td><td className="td">{p.electricity_kwh === null ? "-" : fmt(p.electricity_kwh, 2)}</td>
          </tr>))}</tbody>
      </table>
    </div>
  );
}
