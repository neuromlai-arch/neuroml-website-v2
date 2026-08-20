/* Grounded chat widget: streams Server-Sent Events over a POST fetch
   (EventSource is GET-only, so this parses SSE frames by hand from the
   response body's ReadableStream). Registered via Alpine.data() on
   alpine:init — see popup.js for why that matters for script ordering.

   Focus handling relies on the @alpinejs/focus plugin's x-trap.noscroll —
   same pattern the lead popup and mobile nav already use in this project —
   which traps focus inside the panel while open and restores it to
   whichever element opened the trap when it closes; close() also does it
   explicitly so Escape and the close button both land back on the launcher. */
document.addEventListener("alpine:init", () => {
  Alpine.data("chatWidget", () => ({
    open: false,
    messages: [],
    draft: "",
    email: "",
    streaming: false,
    degraded: false,
    degradeReason: "",
    escalate: false,
    calendlyUrl: null,
    messageCapReached: false,
    sourceUrl: "",

    init() {
      this.sourceUrl = window.location.href;
    },

    toggle() {
      if (this.open) {
        this.close();
      } else {
        this.open = true;
        this.$nextTick(() => this.$refs.input && this.$refs.input.focus());
      }
    },

    close() {
      this.open = false;
      this.$nextTick(() => this.$refs.launcher && this.$refs.launcher.focus());
    },

    scrollToEnd() {
      this.$nextTick(() => {
        if (this.$refs.log) this.$refs.log.scrollTop = this.$refs.log.scrollHeight;
      });
    },

    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/);
      return match ? match[1] : "";
    },

    async send() {
      const text = this.draft.trim();
      if (!text || this.streaming || this.messageCapReached) return;
      this.draft = "";
      this.messages.push({ role: "user", text, sources: [] });
      this.scrollToEnd();
      await this.stream({ message: text });
    },

    async sendEmail() {
      const address = this.email.trim();
      if (!address) return;
      this.email = "";
      await this.stream({ message: "(shared their email)", email: address }, { silent: true });
    },

    async stream(body, { silent = false } = {}) {
      this.streaming = true;
      let assistantIndex = null;
      const ensureAssistantMessage = () => {
        if (assistantIndex === null) {
          assistantIndex = this.messages.length;
          this.messages.push({ role: "assistant", text: "", sources: [] });
        }
        return assistantIndex;
      };

      try {
        const resp = await fetch("/forms/chat/message/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": this.csrfToken() },
          body: JSON.stringify({ ...body, source_url: this.sourceUrl }),
        });

        if (!resp.ok || !resp.body) {
          this.degrade("Something went wrong on our end — please use the contact form.");
          return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let sepIndex;
          while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, sepIndex);
            buffer = buffer.slice(sepIndex + 2);
            if (!this.handleFrame(frame, silent, ensureAssistantMessage)) return;
          }
        }
      } catch (err) {
        this.degrade("Something went wrong on our end — please use the contact form.");
      } finally {
        this.streaming = false;
        this.scrollToEnd();
      }
    },

    /* Returns false when the stream should stop being read further
       (a `degrade` frame is always terminal). */
    handleFrame(frame, silent, ensureAssistantMessage) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) return true;
      const payload = JSON.parse(data);

      switch (event) {
        case "degrade":
          this.degrade(payload.reason);
          return false;
        case "sources":
          if (!silent) this.messages[ensureAssistantMessage()].sources = payload;
          return true;
        case "text":
          if (!silent) {
            this.messages[ensureAssistantMessage()].text += payload;
            this.scrollToEnd();
          }
          return true;
        case "done":
          this.escalate = Boolean(payload.escalate);
          this.calendlyUrl = payload.calendly_url;
          if (this.messages.filter((m) => m.role === "user").length >= 10) {
            this.messageCapReached = true;
          }
          return true;
        default:
          return true;
      }
    },

    degrade(reason) {
      this.degraded = true;
      this.degradeReason = reason || "Something went wrong on our end — please use the contact form.";
    },
  }));
});
