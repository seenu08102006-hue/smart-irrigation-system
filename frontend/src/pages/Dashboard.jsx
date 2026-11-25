import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { CloudUpload, Database } from "lucide-react";
import { api } from "../api";
import Loader from "../components/Loader";
import { getActiveDataset } from "../utils/active";

/** The dashboard is the full analysis of the dataset in use. Without an upload there is nothing to show. */
export default function Dashboard() {
  const [target, setTarget] = useState(undefined);

  useEffect(() => {
    api.datasets().then((d) => {
      const done = d.datasets.filter((x) => x.status === "done");
      const active = getActiveDataset();
      setTarget((done.find((x) => x.id === active) || done[0])?.id ?? null);
    }).catch(() => setTarget(null));
  }, []);

  if (target === undefined) return <Loader text="Loading dashboard…" />;
  if (target) return <Navigate to={`/analysis/${target}`} replace />;
  return (
    <div className="page-bg flex min-h-[60vh] items-center justify-center px-4">
      <div className="glass max-w-lg p-10 text-center">
        <Database className="mx-auto h-12 w-12 text-leaf-500" />
        <p className="mt-4 text-lg font-bold">Please upload a real-life CSV or Excel dataset to begin analysis.</p>
        <Link to="/analyze" className="btn-primary mt-6"><CloudUpload className="h-5 w-5" />Upload Dataset</Link>
      </div>
    </div>
  );
}
