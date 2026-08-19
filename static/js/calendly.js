/* Lazy-loads Calendly's own embed script (~100KB of JS plus its CSS) only
   on first use, per the performance pass — this file itself never fetches
   anything from assets.calendly.com until openCalendlyPopup() is actually
   called by a click, so it's cheap to include on every page. See DEPLOY.md
   for the cookie-consent note this depends on before EU launch. */
(function () {
  var loading = null;

  function loadCalendlyAssets() {
    if (window.Calendly) return Promise.resolve();
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      var link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://assets.calendly.com/assets/external/widget.css";
      document.head.appendChild(link);

      var script = document.createElement("script");
      script.src = "https://assets.calendly.com/assets/external/widget.js";
      script.async = true;
      script.onload = function () { resolve(); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return loading;
  }

  /* Keyboard-closable and returns focus on close, matching the lead
     popup's x-trap behaviour — Calendly's own overlay doesn't do either
     by default. Escape calls Calendly's documented closePopupWidget();
     focus returns to whatever was focused before the button was clicked,
     detected by polling for the overlay's removal since Calendly doesn't
     emit a documented "closed" event. */
  window.openCalendlyPopup = function (url) {
    if (!url) return;
    var lastFocused = document.activeElement;

    loadCalendlyAssets().then(function () {
      Calendly.initPopupWidget({ url: url });

      var onKeydown = function (e) {
        if (e.key === "Escape") Calendly.closePopupWidget();
      };
      document.addEventListener("keydown", onKeydown);

      var poll = setInterval(function () {
        if (document.querySelector(".calendly-overlay")) return;
        clearInterval(poll);
        document.removeEventListener("keydown", onKeydown);
        if (lastFocused && typeof lastFocused.focus === "function") {
          lastFocused.focus();
        }
      }, 200);
    });
  };
})();
