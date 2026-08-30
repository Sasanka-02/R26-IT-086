/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#1F2A24",
          soft: "#5B6A63",
        },
        teal: {
          50: "#EEF5F2",
          100: "#DCEBE5",
          400: "#5C9686",
          500: "#3D8271",
          600: "#2F6F62",
          700: "#255950",
        },
        gold: {
          400: "#E4B966",
          500: "#D9A441",
          600: "#BD8A2E",
        },
        paper: "#F5F9F7",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
