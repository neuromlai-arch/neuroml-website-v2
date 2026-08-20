/* Featured case study carousel: CSS scroll-snap does the actual scrolling
   (native trackpad/touch/momentum), Alpine only tracks position for the
   dot indicators and the prev/next disabled state, and drives focus so
   arrow-key navigation moves between cards rather than just the viewport.

   No autoplay — these are case studies, not a promotion. Registered via
   Alpine.data() on alpine:init, same reason as hero-stack.js. */
document.addEventListener("alpine:init", () => {
  Alpine.data("caseStudyCarousel", (count) => ({
    count,
    active: 0,
    atStart: true,
    atEnd: count <= 1,
    reducedMotion: false,

    init() {
      this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      this.$nextTick(() => this.updateEdges());
    },

    cardStep() {
      const track = this.$refs.track;
      const first = track.children[0];
      if (!first) return 0;
      const gap = parseFloat(getComputedStyle(track).columnGap || 0);
      return first.getBoundingClientRect().width + gap;
    },

    next() {
      if (this.atEnd) return;
      this.goTo(Math.min(this.active + 1, this.count - 1));
    },

    prev() {
      if (this.atStart) return;
      this.goTo(Math.max(this.active - 1, 0));
    },

    goTo(i) {
      this.active = i;
      this.$refs.track.scrollTo({
        left: this.cardStep() * i,
        behavior: this.reducedMotion ? "auto" : "smooth",
      });
      const card = this.$refs.track.children[i];
      if (card) card.focus({ preventScroll: true });
      this.$nextTick(() => this.updateEdges());
    },

    onScroll() {
      if (this._raf) cancelAnimationFrame(this._raf);
      this._raf = requestAnimationFrame(() => {
        const step = this.cardStep();
        if (step > 0) this.active = Math.round(this.$refs.track.scrollLeft / step);
        this.updateEdges();
      });
    },

    updateEdges() {
      const track = this.$refs.track;
      this.atStart = track.scrollLeft <= 2;
      this.atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
    },
  }));
});
