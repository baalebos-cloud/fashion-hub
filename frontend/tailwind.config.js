/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // "Workroom" palette — a tailoring vocabulary instead of generic
        // SaaS blues. Shared by the AI assistant and the wider app shell
        // so the assistant doesn't look like a bolted-on third party.
        ink: {
          DEFAULT: "#1c2230",
          soft: "#565a66",
        },
        muslin: "#ece7db",
        paper: "#faf9f5",
        brass: {
          DEFAULT: "#ab8a52",
          deep: "#8d7040",
        },
        thread: "#8a3a2b",
        line: "#d9d2c1",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        card: "16px",
      },
    },
  },
  plugins: [],
};
