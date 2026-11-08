/** @type {import('tailwindcss').Config} */
// Every colour points at a --tl-* variable in src/styles/variables.css, so one token change
// (or the dark theme) updates the whole app. Opacity modifiers such as bg-ink/90 still work.
const v = (name) => `var(--tl-${name})`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // "Workroom" palette, refined in UI/UX proposal v2.
        ink: { DEFAULT: v("ink"), soft: v("ink-soft") },
        muslin: v("muslin"),
        paper: v("paper"),
        surface: v("surface"),
        brass: { DEFAULT: v("brass"), deep: v("brass-deep") },
        thread: v("thread"),
        line: { DEFAULT: v("line"), strong: v("line-strong") },
        indigo: { DEFAULT: v("indigo"), deep: v("indigo-deep"), wash: v("indigo-wash") },
        success: { DEFAULT: v("success"), wash: v("success-wash") },
        warning: { DEFAULT: v("warning"), wash: v("warning-wash") },
        danger: { DEFAULT: v("thread"), wash: v("danger-wash") },
        disabled: v("disabled"),
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Instrument Sans", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "Menlo", "monospace"],
      },
      borderRadius: {
        card: "12px",
        control: "10px",
      },
    },
  },
  plugins: [],
};
