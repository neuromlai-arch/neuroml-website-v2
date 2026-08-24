/* Minimal, owned cookie consent — no third-party CMP. One cookie
   ("cookie_consent" = "accepted" | "rejected") gates two things that set
   third-party cookies unconditionally otherwise: GTM (see the
   window.GTM_CONTAINER_ID script in base.html's <head>, which only stores
   the id — it never loads GTM itself) and the Calendly embed (popup opener
   below, plus calendlyInlineGate for the demo page's inline widget).

   Registered via Alpine.data() on alpine:init, same reason as popup.js:
   Alpine.start() runs as soon as its own deferred <script> executes, which
   is before this file's deferred <script> — a plain global would lose that
   race and x-cloak would already be stripped by the time it's defined. */
document.addEventListener("alpine:init", () => {
  Alpine.data("cookieConsent", () => ({
    visible: false,
    init() {
      this.visible = !this.getCookie("cookie_consent");
      if (this.getCookie("cookie_consent") === "accepted") this.loadGTM();
      window.addEventListener("cookie-consent:open", () => { this.visible = true; });
    },
    accept() {
      this.setCookie("cookie_consent", "accepted", 180);
      this.visible = false;
      this.loadGTM();
      window.dispatchEvent(new CustomEvent("cookie-consent:accept"));
    },
    reject() {
      this.setCookie("cookie_consent", "rejected", 180);
      this.visible = false;
    },
    dismiss() {
      // Escape closes it for this visit without recording a choice — the
      // banner returns on the next page load rather than trapping keyboard
      // users with no way to get past it except picking accept/reject.
      this.visible = false;
    },
    loadGTM() {
      const id = window.GTM_CONTAINER_ID;
      if (!id || window.__gtmLoaded) return;
      window.__gtmLoaded = true;
      (function (w, d, s, l, i) {
        w[l] = w[l] || [];
        w[l].push({ "gtm.start": new Date().getTime(), event: "gtm.js" });
        var f = d.getElementsByTagName(s)[0], j = d.createElement(s),
          dl = l != "dataLayer" ? "&l=" + l : "";
        j.async = true;
        j.src = "https://www.googletagmanager.com/gtm.js?id=" + i + dl;
        f.parentNode.insertBefore(j, f);
      })(window, document, "script", "dataLayer", id);
    },
    getCookie(name) {
      const row = document.cookie.split("; ").find((r) => r.startsWith(name + "="));
      return row ? row.split("=")[1] : null;
    },
    setCookie(name, value, days) {
      const expires = new Date(Date.now() + days * 864e5).toUTCString();
      document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
    },
  }));
});
