import { Droplets } from "lucide-react";

/** Animated water-drop loader. `fullscreen` shows it as an overlay. */
export default function Loader({ text = "Loading…", fullscreen = false }) {
  const body = (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex h-20 w-20 items-center justify-center">
        <span className="absolute inset-0 animate-pulseRing rounded-full bg-leaf-400/40" />
        <span className="absolute inset-0 animate-pulseRing rounded-full bg-leaf-400/40 [animation-delay:.9s]" />
        <div className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-leaf-500 to-emerald-400 text-white shadow-lg">
          <Droplets className="h-7 w-7 animate-float" />
        </div>
      </div>
      <p className="text-sm font-medium text-leaf-800 dark:text-leaf-200">{text}</p>
    </div>
  );
  if (!fullscreen) return <div className="flex justify-center py-16">{body}</div>;
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-white/80 backdrop-blur-sm dark:bg-slate-950/80">
      {body}
    </div>
  );
}
