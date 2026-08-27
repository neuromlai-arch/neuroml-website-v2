/* Rotating hero card stack: cycles every 5s, pauses on hover/focus, and
   never rotates at all when prefers-reduced-motion is set (still shows the
   first card, just static). Registered via Alpine.data() on alpine:init —
   see popup.js for why that matters for script ordering.

   Only the active card is fully visible; its two flanking neighbours sit
   just off to each side (slide + fade), and the rest sit fully transparent
   behind them so the stack never grows past three visible layers regardless
   of card count. */
document.addEventListener("alpine:init", () => {
  Alpine.data("heroStack", (count) => ({
    active: 0,
    count,
    paused: false,
    reducedMotion: false,
    timer: null,
    init() {
      this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!this.reducedMotion) this.start();
    },
    start() {
      this.stop();
      this.timer = setInterval(() => {
        if (!this.paused) this.next();
      }, 5000);
    },
    stop() {
      if (this.timer) clearInterval(this.timer);
    },
    next() {
      this.active = (this.active + 1) % this.count;
    },
    goTo(i) {
      this.active = i;
    },
    pause() {
      this.paused = true;
    },
    resume() {
      this.paused = false;
    },
    offset(i) {
      const half = Math.floor(this.count / 2);
      let diff = i - this.active;
      if (diff > half) diff -= this.count;
      if (diff < -half) diff += this.count;
      return diff;
    },
    cardClass(i) {
      const diff = this.offset(i);
      if (diff === 0) {
        return "z-20 scale-100 opacity-100 translate-x-0";
      }
      if (diff === 1 || diff === -1) {
        // Outgoing/incoming neighbour: slides 30px and fades toward 0.
        const side = diff === 1 ? "translate-x-[30px]" : "-translate-x-[30px]";
        return `z-10 scale-100 opacity-0 pointer-events-none ${side}`;
      }
      return "z-0 scale-100 opacity-0 pointer-events-none translate-x-0";
    },
  }));
});
