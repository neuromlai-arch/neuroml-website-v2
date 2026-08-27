/* Scroll-triggered reveals. Elements are grouped by their nearest ancestor
   <section> (falling back to the element itself) so the 80ms stagger is
   computed within that group's own DOM order — not by whichever entries an
   IntersectionObserver batch happened to fire together, which is what the
   previous entries-index approach did and made the stagger coincidental
   rather than tied to layout order.

   One shared observer handles both the full page (on load) and any content
   HTMX swaps in later (e.g. the "Use cases" tab panel) — see the
   htmx:afterSwap listener at the bottom. */
(() => {
  const SELECTOR = ".reveal, .reveal-sm";
  const STAGGER_MS = 80;

  let observer = null;

  const groupAndObserve = (root) => {
    const targets = Array.from(root.querySelectorAll(SELECTOR));
    if (targets.length === 0) return;

    if (!("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("is-visible"));
      return;
    }

    if (!observer) {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          });
        },
        { threshold: 0.15 }
      );
    }

    const groups = new Map();
    targets.forEach((el) => {
      const group = el.closest("section") || el;
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(el);
    });

    groups.forEach((els) => {
      els.forEach((el, index) => {
        el.style.transitionDelay = `${index * STAGGER_MS}ms`;
        observer.observe(el);
      });
    });
  };

  document.addEventListener("DOMContentLoaded", () => groupAndObserve(document));

  // Freshly-swapped HTMX content (e.g. an industry tab panel) carries its
  // own .reveal cards, never seen by the initial page-load scan.
  document.addEventListener("htmx:afterSwap", (event) => groupAndObserve(event.target));

  // Hero scroll indicator: pulses gently until the visitor's first scroll,
  // then fades out for good.
  const indicator = document.querySelector(".scroll-indicator");
  if (indicator) {
    const hide = () => {
      indicator.classList.add("is-hidden");
      window.removeEventListener("scroll", hide);
    };
    window.addEventListener("scroll", hide, { passive: true, once: true });
  }
})();
