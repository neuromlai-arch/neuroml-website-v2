/* Lead popup trigger logic: delay / scroll / exit-intent / delay-or-exit,
   a frequency-cap cookie on dismissal, and a longer-lived cookie once the
   form is submitted (both set from server-driven day counts). */
function leadPopup(config) {
  return {
    open: false,
    config,
    init() {
      if (!this.config.enabled) return;
      if (!this.config.showOnMobile && window.innerWidth < 768) return;
      if (this.config.excludePaths.includes(window.location.pathname)) return;
      if (this.getCookie("popup_dismissed") || this.getCookie("popup_submitted")) return;

      if (this.config.trigger === "delay" || this.config.trigger === "delay_or_exit") {
        setTimeout(() => this.show(), this.config.delaySeconds * 1000);
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

      window.addEventListener("popup:submitted", () => {
        this.setCookie("popup_submitted", "1", this.config.hideAfterSubmitDays);
        setTimeout(() => this.close(false), 1500);
      });
    },
    show() {
      if (!this.open) this.open = true;
    },
    close(remember = true) {
      this.open = false;
      if (remember) this.setCookie("popup_dismissed", "1", this.config.frequencyDays);
    },
    getCookie(name) {
      return document.cookie.split("; ").find((row) => row.startsWith(name + "="));
    },
    setCookie(name, value, days) {
      const expires = new Date(Date.now() + days * 864e5).toUTCString();
      document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
    },
  };
}
