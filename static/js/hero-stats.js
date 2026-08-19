/* Count-up for the stats band, fired once when it scrolls into view.
   Each .stat-value carries data-target (the leading integer to count up
   to) and its full display text as textContent already (e.g. "40+",
   "6 platforms") — we animate the digits and leave any prefix/suffix
   text alone by re-rendering the same string with the digits swapped in,
   so this works for a plain count ("30") and a decorated one ("30+")
   without separate markup per case. */
document.addEventListener("DOMContentLoaded", () => {
  const values = document.querySelectorAll(".stat-value[data-target]");
  if (values.length === 0) return;

  const animate = (el) => {
    const target = parseInt(el.dataset.target, 10);
    const full = el.textContent;
    if (Number.isNaN(target)) {
      el.classList.add("is-counted");
      return;
    }
    const duration = 900;
    const start = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const current = Math.round(target * (1 - Math.pow(1 - progress, 3)));
      el.textContent = full.replace(String(target), String(current));
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = full;
        el.classList.add("is-counted");
      }
    };
    requestAnimationFrame(tick);
  };

  if (!("IntersectionObserver" in window)) {
    values.forEach((el) => {
      el.classList.add("is-counted");
    });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animate(entry.target);
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.4 }
  );
  values.forEach((el) => observer.observe(el));
});
