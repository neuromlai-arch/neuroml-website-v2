/** Every colour, font size, radius, and shadow used on the site lives here.
 *  Restyling the whole site is a matter of editing this one file. */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#16181D",
        "ink-secondary": "#6B7280",
        "ink-muted": "#9CA3AF",
        accent: {
          DEFAULT: "#E0312A",
          dark: "#B8241F",
        },
        band: "#0D1117",
        grid: "#F2F2F2",
      },
      fontFamily: {
        sans: [
          "Manrope",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
      },
      fontSize: {
        hero: ["clamp(3rem, 7vw, 6rem)", { lineHeight: "0.95", fontWeight: "700" }],
      },
      letterSpacing: {
        eyebrow: "0.15em",
      },
      borderRadius: {
        card: "20px",
      },
      boxShadow: {
        card: "0 30px 80px -24px rgb(22 24 29 / 0.18)",
        "card-hover": "0 40px 100px -20px rgb(22 24 29 / 0.28)",
        "card-flank": "0 20px 50px -20px rgb(22 24 29 / 0.12)",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(to right, #F2F2F2 1px, transparent 1px), linear-gradient(to bottom, #F2F2F2 1px, transparent 1px)",
        "band-glow":
          "radial-gradient(circle at 85% 15%, rgb(224 49 42 / 0.35), transparent 60%)",
      },
      backgroundSize: {
        grid: "64px 64px",
      },
      transitionDuration: {
        DEFAULT: "300ms",
      },
    },
  },
  plugins: [],
};
