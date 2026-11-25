import { Sprout } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-leaf-100 bg-leaf-50 dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-slate-500 sm:flex-row sm:px-6 dark:text-slate-400">
        <div className="flex items-center gap-2 font-semibold text-leaf-800 dark:text-leaf-300">
          <Sprout className="h-5 w-5" /> Smart Irrigation Data Analysis System
        </div>
        <p>Every result is computed only from the dataset you upload.</p>
      </div>
    </footer>
  );
}
