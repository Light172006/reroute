import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        page: "var(--bg)",
        surface: {
          DEFAULT: "var(--surface)",
          alt: "var(--surface-alt)",
          raised: "var(--surface-raised)",
          hover: "var(--bg-card-hover)",
        },
        card: {
          DEFAULT: "var(--surface)",
          alt: "var(--surface-alt)",
          raised: "var(--surface-raised)",
          hover: "var(--bg-card-hover)",
        },
        border: {
          DEFAULT: "var(--border)",
          strong: "var(--border-strong)",
          subtle: "var(--border)",
          muted: "var(--border-muted)",
        },
        text: {
          DEFAULT: "var(--text)",
          primary: "var(--text)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        chart: {
          line: "var(--chart-line)",
          grid: "var(--chart-grid)",
          series1: "var(--chart-series-1)",
          series2: "var(--chart-series-2)",
          series3: "var(--chart-series-3)",
          series4: "var(--chart-series-4)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--on-primary)",
          hover: "var(--primary-hover)",
          active: "var(--primary-active)",
          tint: "var(--primary-tint)",
          50: "var(--primary-50)",
          100: "var(--primary-100)",
          200: "var(--primary-200)",
          300: "var(--primary-300)",
          400: "var(--primary-400)",
          500: "var(--primary-500)",
          600: "var(--primary-600)",
          700: "var(--primary-700)",
          800: "var(--primary-800)",
          900: "var(--primary-900)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          bg: "var(--accent-bg)",
          border: "var(--accent-border)",
          text: "var(--accent-text)",
          50: "var(--accent-50)",
          100: "var(--accent-100)",
          200: "var(--accent-200)",
          400: "var(--accent-400)",
          500: "var(--accent-500)",
          600: "var(--accent-600)",
        },
        success: {
          DEFAULT: "var(--success)",
          bg: "var(--success-bg)",
          border: "var(--success-border)",
          text: "var(--success-text)",
        },
        danger: {
          DEFAULT: "var(--danger)",
          bg: "var(--danger-bg)",
          border: "var(--danger-border)",
          text: "var(--danger-text)",
        },
        cat: {
          sightseeing: {
            bg: "var(--cat-sightseeing-bg)",
            fg: "var(--cat-sightseeing-fg)",
          },
          food: {
            bg: "var(--cat-food-bg)",
            fg: "var(--cat-food-fg)",
          },
          culture: {
            bg: "var(--cat-culture-bg)",
            fg: "var(--cat-culture-fg)",
          },
          nature: {
            bg: "var(--cat-nature-bg)",
            fg: "var(--cat-nature-fg)",
          },
          nightlife: {
            bg: "var(--cat-nightlife-bg)",
            fg: "var(--cat-nightlife-fg)",
          },
          shopping: {
            bg: "var(--cat-shopping-bg)",
            fg: "var(--cat-shopping-fg)",
          },
          adventure: {
            bg: "var(--cat-adventure-bg)",
            fg: "var(--cat-adventure-fg)",
          },
          transport: {
            bg: "var(--cat-transport-bg)",
            fg: "var(--cat-transport-fg)",
          },
        },
        slate: {
          950: "#070D18",
        },
      },
      borderRadius: {
        card: "16px",
        input: "8px",
        pill: "9999px",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "JetBrains Mono", "monospace"],
      },
      spacing: {
        "4px": "4px",
        "8px": "8px",
        "12px": "12px",
        "16px": "16px",
        "20px": "20px",
        "24px": "24px",
        "32px": "32px",
        "48px": "48px",
        "64px": "64px",
      },
    },
  },
  plugins: [],
};

export default config;
