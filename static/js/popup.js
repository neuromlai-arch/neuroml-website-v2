/* Lead popup trigger logic: delay / scroll / exit-intent / delay-or-exit for
   the *first* show, then a session-scoped re-show schedule after that:

     dismissal 1 -> wait 3 minutes -> show again
     dismissal 2 -> wait 3 minutes -> show again
     dismissal 3+ -> wait 5 minutes -> show again (repeats for the rest of
                     the session)

   Dismissal count and the "when did we last dismiss" timestamp live in
   sessionStorage, so they reset when the tab closes but survive ordinary
   page navigation within the same tab (each page load re-derives the
   remaining wait from the stored timestamp rather than restarting a timer
   at delaySeconds/3min/5min from scratch).

   Two cookies carry state *across* sessions/tabs, since sessionStorage
   can't:
     - popup_dismissed: set on every dismissal, expires after frequencyDays.
       A fresh session (no session-active marker yet) checks this cookie
       before arming anything — if it's still set, the visitor dismissed in
       a previous session and hasn't waited out frequencyDays yet.
     - popup_submitted: set on successful submission, expires after
       hideAfterSubmitDays. Its presence blocks the popup unconditionally.

   Registered via Alpine.data() on the alpine:init event rather than as a
   bare global function: Alpine's CDN build calls Alpine.start() as soon as
   its own <script> tag finishes executing, which happens *before* this
   file's deferred <script> tag runs. A plain `function leadPopup(){}`
   loses that race — Alpine evaluates `x-data="leadPopup(...)"` while the
   function doesn't exist yet, throws, and (since x-cloak has already been
   stripped by then) the popup renders permanently visible on every page
   load instead of staying hidden until its trigger fires. Alpine.data()
   registration happens on alpine:init, which Alpine fires immediately
   before it scans the DOM, so it's always ready in time regardless of
   script order. */
document.addEventListener("alpine:init", () => {
  const SESSION_ACTIVE_KEY = "popup_session_active";
  const DISMISS_COUNT_KEY = "popup_dismiss_count";
  const LAST_DISMISSED_AT_KEY = "popup_last_dismissed_at";
  const SHORT_INTERVAL_SECONDS = 3 * 60;
  const LONG_INTERVAL_SECONDS = 5 * 60;
  const SHORT_INTERVAL_DISMISSAL_LIMIT = 2;

  Alpine.data("leadPopup", (config) => ({
    open: false,
    config,
    init() {
      if (!this.config.enabled) return;
      // Skip the JS timer entirely on mobile when disabled there — this is
      // not just a CSS hide, the popup never arms and never shows.
      if (!this.config.showOnMobile && window.innerWidth < 768) return;
      if (this.config.excludePaths.includes(window.location.pathname)) return;
      if (this.getCookie("popup_submitted")) return;

      const sessionActive = sessionStorage.getItem(SESSION_ACTIVE_KEY) === "1";
      if (!sessionActive) {
        // First init in this tab session: the between-session frequency
        // gate applies. If the visitor dismissed in an earlier session and
        // frequencyDays hasn't elapsed, the cookie is still set — bail out
        // entirely rather than arming anything.
        if (this.getCookie("popup_dismissed")) return;
        sessionStorage.setItem(SESSION_ACTIVE_KEY, "1");
      }

      const dismissCount = parseInt(sessionStorage.getItem(DISMISS_COUNT_KEY) || "0", 10);
      if (dismissCount === 0) {
        this.armInitialTrigger();
      } else {
        const lastDismissedAt = parseInt(sessionStorage.getItem(LAST_DISMISSED_AT_KEY) || "0", 10);
        const intervalMs = this.intervalSecondsForCount(dismissCount) * 1000;
        this.scheduleShowAfter(lastDismissedAt + intervalMs - Date.now());
      }

      window.addEventListener("popup:submitted", () => {
        this.setCookie("popup_submitted", "1", this.config.hideAfterSubmitDays);
        setTimeout(() => this.close(false), 1500);
      });
    },
    armInitialTrigger() {
      if (this.config.trigger === "delay" || this.config.trigger === "delay_or_exit") {
        this.scheduleShowAfter(this.config.delaySeconds * 1000);
      }
      if (this.config.trigger === "scroll") {
        const onScroll = () => {
          const scrollable = document.body.scrollHeight - window.innerHeight;
          const pct = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
          if (pct >= this.config.scrollPercent) {
            this.show();
            window.removeEventListener("scroll", onScroll);
          }
        };
        window.addEventListener("scroll", onScroll, { passive: true });
      }
      if (this.config.trigger === "exit" || this.config.trigger === "delay_or_exit") {
        const onExit = (e) => {
          if (!e.relatedTarget && e.clientY <= 0) {
            this.show();
            document.removeEventListener("mouseout", onExit);
          }
        };
        document.addEventListener("mouseout", onExit);
      }
    },
    intervalSecondsForCount(count) {
      return count <= SHORT_INTERVAL_DISMISSAL_LIMIT ? SHORT_INTERVAL_SECONDS : LONG_INTERVAL_SECONDS;
    },
    scheduleShowAfter(ms) {
      setTimeout(() => this.show(), Math.max(0, ms));
    },
    show() {
      if (!this.open) this.open = true;
    },
    close(remember = true) {
      this.open = false;
      if (!remember) return;

      const count = parseInt(sessionStorage.getItem(DISMISS_COUNT_KEY) || "0", 10) + 1;
      sessionStorage.setItem(DISMISS_COUNT_KEY, String(count));
      sessionStorage.setItem(LAST_DISMISSED_AT_KEY, String(Date.now()));
      this.setCookie("popup_dismissed", "1", this.config.frequencyDays);
      this.scheduleShowAfter(this.intervalSecondsForCount(count) * 1000);
    },
    getCookie(name) {
      return document.cookie.split("; ").find((row) => row.startsWith(name + "="));
    },
    setCookie(name, value, days) {
      const expires = new Date(Date.now() + days * 864e5).toUTCString();
      document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
    },
  }));
});
