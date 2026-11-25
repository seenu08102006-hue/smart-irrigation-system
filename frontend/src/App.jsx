import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Loader from "./components/Loader";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Datasets from "./pages/Datasets";
import Predict from "./pages/Predict";
import Dashboard from "./pages/Dashboard";

// The Chart.js page is lazy-loaded to keep the first page fast
const Analysis = lazy(() => import("./pages/Analysis"));

function NotFound() {
  return (
    <div className="py-32 text-center">
      <p className="text-6xl">🌾</p>
      <h1 className="mt-4 text-3xl font-bold">Page not found</h1>
    </div>
  );
}

export default function App() {
  const location = useLocation();
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Suspense fallback={<Loader text="Loading page…" />}>
          <AnimatePresence mode="wait">
            <motion.div key={location.pathname}
                        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
              <Routes location={location}>
                <Route path="/" element={<Home />} />
                <Route path="/analyze" element={<Upload />} />
                <Route path="/analysis/:id" element={<Analysis />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/datasets" element={<Datasets />} />
                <Route path="/predict" element={<Predict />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
