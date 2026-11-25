import { createContext, useCallback, useContext, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);

const STYLES = {
  success: { icon: CheckCircle2, cls: "border-leaf-500 text-leaf-700 dark:text-leaf-300" },
  error: { icon: AlertTriangle, cls: "border-red-500 text-red-700 dark:text-red-300" },
  info: { icon: Info, cls: "border-sky-500 text-sky-700 dark:text-sky-300" },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback((type, message) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, type, message }]);
    setTimeout(() => remove(id), 4500);
  }, [remove]);

  const api = {
    success: (m) => push("success", m),
    error: (m) => push("error", m),
    info: (m) => push("info", m),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed right-4 top-20 z-[100] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-3">
        <AnimatePresence>
          {toasts.map((t) => {
            const { icon: Icon, cls } = STYLES[t.type];
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, x: 60, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 60 }}
                role="status"
                className={`pointer-events-auto flex items-start gap-3 rounded-xl border-l-4 bg-white p-4 shadow-xl dark:bg-slate-800 ${cls}`}
              >
                <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                <p className="flex-1 text-sm font-medium text-slate-700 dark:text-slate-100">{t.message}</p>
                <button onClick={() => remove(t.id)} aria-label="Dismiss"><X className="h-4 w-4 text-slate-400" /></button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
