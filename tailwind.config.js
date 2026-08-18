/** Every colour, font size, radius, and shadow used on the site lives here.
 *  Restyling the whole site is a matter of editing this one file.
 *
 *  Monochrome, editorial, engineering-led. Black and white only — hierarchy
 *  comes from scale, weight, and whitespace, not colour. `error` and
 *  `success` are the one exception, reserved for form validation states;
 *  never use them in a CTA, link, badge, or as decoration. */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0B0B0B",
        "ink-body": "#1A1A1A",
        "ink-secondary": "#6B6B6B",
        "ink-muted": "#9B9B9B",
        hairline: "#E5E5E5",
        band: "#0B0B0B",
        grid: "#F4F4F4",
        error: "#C1121F",
        success: "#1B7F4C",
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
        serif: [
          "'Instrument Serif'",
          "ui-serif",
          "Georgia",
          "Cambria",
          "Times New Roman",
          "serif",
        ],
      },
      fontSize: {
        hero: ["clamp(3rem, 7vw, 6rem)", { lineHeight: "0.95", fontWeight: "400" }],
      },
      letterSpacing: {
        eyebrow: "0.14em",
      },
      borderRadius: {
        card: "16px",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(to right, #F4F4F4 1px, transparent 1px), linear-gradient(to bottom, #F4F4F4 1px, transparent 1px)",
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
