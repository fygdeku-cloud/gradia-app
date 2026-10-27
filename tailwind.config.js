/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./gradia/templates/**/*.html",
    "./gradia/static/js/**/*.js",
    "./node_modules/flowbite/**/*.js",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Plus Jakarta Sans",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
      },
      spacing: {
        18: "4.5rem",
      },
      colors: {
        night: {
          500: "#33456e",
          600: "#27375a",
          700: "#1c2a45",
          750: "#182338",
          800: "#131d31",
          850: "#0f1728",
          900: "#0b1220",
          925: "#0a101d",
          950: "#070b14",
        },
        brand: {
          50: "#fdfaef",
          100: "#f8f0d3",
          200: "#f0dfa3",
          300: "#e9cc70",
          400: "#e0b851",
          500: "#d2a23c",
          600: "#b9862f",
          700: "#946827",
          800: "#795224",
          900: "#65431f",
          950: "#3a240d",
        },
        ink: {
          DEFAULT: "#eef1f7",
          secondary: "#a6b4cb",
          muted: "#7c8aa3",
        },
      },
      borderRadius: {
        sm: "0.375rem",
        md: "0.625rem",
        lg: "0.875rem",
        xl: "1.125rem",
        "2xl": "1.5rem",
      },
    },
  },
  safelist: ["opacity-0", "transition-opacity", "duration-300", "shadow-sm", "hidden"],
  plugins: [require("flowbite/plugin")],
};
