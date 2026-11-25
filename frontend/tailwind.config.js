/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        leaf: {
          50: "#f0fdf4", 100: "#dcfce7", 200: "#bbf7d0", 300: "#86efac",
          400: "#4ade80", 500: "#22c55e", 600: "#16a34a", 700: "#15803d",
          800: "#166534", 900: "#14532d", 950: "#052e16",
        },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      keyframes: {
        float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-12px)" } },
        drift: { "0%": { transform: "translateX(-10%)" }, "100%": { transform: "translateX(110vw)" } },
        sway: { "0%,100%": { transform: "rotate(-2deg)" }, "50%": { transform: "rotate(2deg)" } },
        pulseRing: { "0%": { transform: "scale(.8)", opacity: ".8" }, "100%": { transform: "scale(1.8)", opacity: "0" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        float: "float 5s ease-in-out infinite",
        drift: "drift 60s linear infinite",
        sway: "sway 4s ease-in-out infinite",
        pulseRing: "pulseRing 1.8s ease-out infinite",
      },
    },
  },
  plugins: [],
};
