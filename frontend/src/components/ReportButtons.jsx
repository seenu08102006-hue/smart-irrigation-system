import { useState } from "react";
import { FileSpreadsheet, FileText, FileType2, Loader2 } from "lucide-react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";

const FORMATS = [
  { fmt: "pdf", label: "PDF report", icon: FileText },
  { fmt: "xlsx", label: "Excel report", icon: FileSpreadsheet },
  { fmt: "csv", label: "CSV report", icon: FileType2 },
];

/** Three download buttons (PDF / Excel / CSV) for an analysed dataset. */
export default function ReportButtons({ datasetId, className = "" }) {
  const toast = useToast();
  const [busy, setBusy] = useState(null);

  const download = async (fmt) => {
    setBusy(fmt);
    try {
      await api.downloadReport(datasetId, fmt);
      toast.success(`${fmt.toUpperCase()} report downloaded.`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {FORMATS.map(({ fmt, label, icon: Icon }) => (
        <button key={fmt} onClick={() => download(fmt)} disabled={!!busy} className="btn-outline !py-2 text-sm">
          {busy === fmt ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}{label}
        </button>
      ))}
    </div>
  );
}
