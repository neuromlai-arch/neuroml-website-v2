/* Rotating hero card stack: cycles every 5s, pauses on hover/focus, and
   never rotates at all when prefers-reduced-motion is set (still shows the
   first card, just static). Registered via Alpine.data() on alpine:init —
   see popup.js for why that matters for script ordering.

   Only the active card and its two flanking neighbours are visually
   distinct (sharp/centred vs scaled+faded); the rest sit fully
   transparent behind them so the stack never grows past three visible
   layers regardless of card count. */
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
        return "z-20 scale-100 opacity-100 translate-x-0 rotate-0";
      }
      if (diff === 1 || diff === -1) {
        const side = diff === 1 ? "translate-x-24 rotate-6" : "-translate-x-24 -rotate-6";
        return `z-10 scale-[0.6] opacity-40 ${side}`;
      }
      return "z-0 scale-50 opacity-0 pointer-events-none";
    },
  }));
});
