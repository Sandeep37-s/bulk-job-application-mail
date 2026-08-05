import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0E1013",
          50: "#F5F5F4",
          100: "#E7E5E1",
          200: "#C9C7C2",
          300: "#8B8F9B",
          400: "#5B5F6B",
          500: "#33363E",
          600: "#22242A",
          700: "#171A21",
          800: "#12141A",
          900: "#0E1013",
        },
        seal: {
          DEFAULT: "#E8A94C",
          light: "#F2C784",
          dark: "#B9822F",
        },
        wax: {
          DEFAULT: "#C1543A",
        },
        ok: "#6FAE8C",
        err: "#D9695F",
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      backgroundImage: {
        grain: "url('/grain.svg')",
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        stamp: {
          "0%": { transform: "scale(1.4) rotate(-8deg)", opacity: "0" },
          "60%": { transform: "scale(0.95) rotate(-8deg)", opacity: "1" },
          "100%": { transform: "scale(1) rotate(-8deg)", opacity: "1" },
        },
      },
      animation: {
        stamp: "stamp 260ms ease-out forwards",
      },
    },
  },
  plugins: [],
};
export default config;
