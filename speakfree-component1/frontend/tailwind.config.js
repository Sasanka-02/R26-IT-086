/** @type {import('tailwindcss').Config} */
// Palette taken from the SpeakFree design mock-up:
//   navy sidebar/brand · royal-blue actions · lavender/violet accents · amber logo accent
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F5F6FB", // page background
        line: "#E6E8F2", // card borders / dividers
        ink: { DEFAULT: "#1B2559", soft: "#4A5578", muted: "#7A8299" }, // headings · body · secondary text
        navy: { DEFAULT: "#1E3A8A", deep: "#162C6B" }, // active nav, logo tile
        brand: { DEFAULT: "#1D4ED8", hover: "#1E40AF", soft: "#E8EEFF" }, // primary buttons, links
        lav: { 50: "#F7F5FF", 100: "#EFEBFF", 200: "#DED6FF", 400: "#A596F2", 500: "#7C6CF0", 600: "#6553D6" }, // lavender/violet
        sun: { DEFAULT: "#F59E0B", soft: "#FFF4DE" }, // "Free" + notification dot
        ok: { DEFAULT: "#16A34A", soft: "#E8F7EE" },
        warn: { DEFAULT: "#D97706", soft: "#FFF4E0" },
        bad: { DEFAULT: "#DC2626", soft: "#FDECEC" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(27, 37, 89, 0.04), 0 4px 16px rgba(27, 37, 89, 0.06)",
        lift: "0 8px 28px rgba(27, 37, 89, 0.12)",
        nav: "0 4px 12px rgba(30, 58, 138, 0.25)",
      },
    },
  },
  plugins: [],
};
