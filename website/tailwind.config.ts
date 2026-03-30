import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#0b1a2f", soft: "#485b77", faint: "#6e7f97" },
        night: { DEFAULT: "#0f2440", 2: "#142e51" },
        paper: { DEFAULT: "#f5efe4", 2: "#fbf7ef" },
        blue: { DEFAULT: "#196cff" },
        mint: { DEFAULT: "#34c7a0" },
        coral: { DEFAULT: "#ff8357" },
        amber: { DEFAULT: "#f3b13f" },
        sky: { DEFAULT: "#9bd5ff" },
      },
      fontFamily: {
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      borderRadius: {
        xl: "34px",
        lg: "22px",
        md: "16px",
        sm: "12px",
      },
      boxShadow: {
        lg: "0 30px 80px rgba(17, 31, 54, 0.14)",
        md: "0 18px 42px rgba(17, 31, 54, 0.12)",
      },
      maxWidth: {
        container: "1200px",
        "container-wide": "1280px",
      },
    },
  },
  plugins: [],
};

export default config;
