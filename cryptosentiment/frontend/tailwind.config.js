/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          base: "#070A12",
          raised: "#0C111E",
          panel: "#0F1523",
          overlay: "#141B2D",
          line: "#1C2540",
        },
        ink: {
          primary: "#E9EEF8",
          muted: "#8A94AC",
          dim: "#5B647C",
        },
        accent: {
          DEFAULT: "#38BDF8",
          dim: "#0E7490",
        },
        pos: "#34D399",
        neg: "#F87171",
        warn: "#FBBF24",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.03) inset, 0 8px 24px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};
