import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { CloudUpload, Sprout } from "lucide-react";

/** Step 1 of the workflow: one button. Nothing is analysed before a dataset is uploaded. */
export default function Home() {
  return (
    <div className="page-bg flex min-h-[calc(100vh-4rem-5rem)] items-center justify-center px-4 py-16">
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="glass mx-auto max-w-xl p-10 text-center sm:p-14">
        <motion.span animate={{ y: [0, -6, 0] }} transition={{ repeat: Infinity, duration: 2.4 }}
                     className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-leaf-600 to-emerald-400 text-white shadow-xl">
          <Sprout className="h-10 w-10" />
        </motion.span>
        <h1 className="mt-6 text-3xl font-extrabold sm:text-4xl">Smart <span className="gradient-text">Irrigation</span> Data Analysis</h1>
        <p className="mt-3 text-slate-600 dark:text-slate-300">Please upload a real-life CSV or Excel dataset to begin analysis.</p>
        <Link to="/analyze" className="btn-primary mt-8 !px-8 !py-4 text-lg"><CloudUpload className="h-6 w-6" />Upload Dataset</Link>
      </motion.div>
    </div>
  );
}
