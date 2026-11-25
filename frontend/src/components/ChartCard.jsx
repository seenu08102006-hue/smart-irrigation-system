import { motion } from "framer-motion";

/** Glass card that holds a chart (or any visual) with a title and subtitle. */
export default function ChartCard({ title, subtitle, children, className = "", height = "h-64", action }) {
  return (
    <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.5 }} className={`glass p-5 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-bold">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className={`mt-4 ${height}`}>{children}</div>
    </motion.div>
  );
}
