/** @type {import('tailwindcss').Config} */

// Every brand colour reads a CSS variable (RGB channels) defined in index.css,
// so the whole app shares one dark theme and opacity modifiers (bg-gold-400/10) work.
const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // "white" is the card surface; text-white on a mint button reads as dark ink.
        white: v("card"),
        paper: v("inset"),
        ink: {
          DEFAULT: v("ink"),
          soft: v("ink-soft"),
        },
        teal: {
          50: v("teal-50"),
          100: v("teal-100"),
          200: v("teal-200"),
          400: v("teal-400"),
          500: v("teal-500"),
          600: v("teal-600"),
          700: v("teal-700"),
          800: v("teal-800"),
          900: v("teal-900"),
        },
        gold: {
          400: v("gold-400"),
          500: v("gold-500"),
          600: v("gold-600"),
        },
        amber: {
          50: v("amber-50"),
          200: v("amber-200"),
          800: v("amber-800"),
          900: v("amber-900"),
        },
        red: {
          50: v("red-50"),
          200: v("red-200"),
          600: v("red-600"),
          700: v("red-700"),
        },
        // True white, for hairlines and hover washes on the dark surfaces.
        snow: "rgb(255 255 255 / <alpha-value>)",
        shell: v("shell"),
        panel: v("panel"),
      },
      fontFamily: {
        display: ["Poppins", "Inter", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
