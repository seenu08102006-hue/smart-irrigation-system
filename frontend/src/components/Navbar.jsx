import { Link, NavLink } from "react-router-dom";
import { BarChart3, CloudUpload, Database, Moon, Sprout, Sun, Zap } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useActiveDataset } from "../utils/active";

const LINKS = [
  { to: "/analyze", label: "Upload", icon: CloudUpload },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { to: "/predict", label: "Predict", icon: Zap },
  { to: "/datasets", label: "Datasets", icon: Database },
];

export default function Navbar() {
  const { dark, toggle } = useTheme();
  const [active] = useActiveDataset();          // the menu only appears once the user has uploaded something

  const linkCls = ({ isActive }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive ? "bg-leaf-100 text-leaf-800 dark:bg-slate-800 dark:text-leaf-300"
               : "text-slate-600 hover:bg-leaf-50 dark:text-slate-300 dark:hover:bg-slate-800"}`;

  return (
    <header className="sticky top-0 z-50 border-b border-leaf-100 bg-white/80 backdrop-blur-lg dark:border-slate-800 dark:bg-slate-950/80">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-2 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 text-lg font-extrabold text-leaf-800 dark:text-white">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-leaf-600 to-emerald-400 text-white shadow">
            <Sprout className="h-5 w-5" />
          </span>
          <span className="hidden sm:inline">Smart<span className="gradient-text">Irrigation</span></span>
        </Link>

        <div className="flex items-center gap-1">
          {active && LINKS.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={linkCls} aria-label={label}><Icon className="h-4 w-4" /><span className="hidden md:inline">{label}</span></NavLink>
          ))}
          <button onClick={toggle} aria-label="Toggle dark mode"
                  className="rounded-xl p-2.5 text-slate-600 transition hover:bg-leaf-50 dark:text-slate-300 dark:hover:bg-slate-800">
            {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </nav>
    </header>
  );
}
