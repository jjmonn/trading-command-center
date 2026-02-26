/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Dark mode palette
        surface: {
          DEFAULT: "#0f1117",
          1: "#161b27",
          2: "#1e2435",
          3: "#252d42",
        },
        border: "#2e3650",
        profit: "#22c55e",   // green-500
        loss:   "#ef4444",   // red-500
        warn:   "#eab308",   // yellow-500
        info:   "#3b82f6",   // blue-500
        muted:  "#6b7280",   // gray-500
        bright: "#e2e8f0",   // slate-200
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
