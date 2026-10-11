/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm ivory instead of pure white — easier on the eyes.
        white: "#FFFDF8",
        ink: {
          DEFAULT: "#1B2622",
          soft: "#5F6C66",
        },
        // Deep emerald.
        teal: {
          50: "#EEF4F0",
          100: "#DDE9E3",
          200: "#BFD6CC",
          400: "#5E9B8D",
          500: "#2E7A6B",
          600: "#1E5E53",
          700: "#164A42",
          800: "#103A33",
        },
        // Champagne gold.
        gold: {
          400: "#DCC08A",
          500: "#C7A15A",
          600: "#9A7535",
        },
        paper: "#F3EEE4",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
