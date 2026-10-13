/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        navy: { 950: "#07142A", 900: "#0B1F3A", 800: "#12294B", 700: "#1B3A66", 600: "#2A4D80" },
        heat: { orange: "#EA580C", red: "#C53030", amber: "#D69E2E", green: "#2F855A" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"] },
    },
  },
  plugins: [],
};
