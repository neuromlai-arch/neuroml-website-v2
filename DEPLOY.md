# Deploy checklist

This is a launch-readiness reference, not a deploy trigger — nothing in this
repo has been deployed. Read this before the first real deploy.

Scripted deploy to a single AWS EC2 instance lives in `deploy/` — see
"Deploying to EC2" near the end of this file for the full walkthrough
(`setup.sh`, `docker-compose.prod.yml`, `nginx.conf`, `deploy.sh`), plus SSL,
DNS, the cutover checklist, and monitoring.

## Environment variables

Everything is read via `django-environ` from a real `.env` file or the
process environment — see `.env.example` for local dev, `.env.prod.example`
for a real deploy (a smaller, prod-only list — no `DJANGO_DEBUG`, no dev
superuser default, etc). `Required` below means "Django raises
`ImproperlyConfigured` and refuses to start without it"; `Optional` means
there's a working default.

| Variable | Required? | Read in | What breaks without it |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Required (no default in `manage.py`/WSGI) | everywhere | Django can't boot at all. Must be `config.settings.prod` for any real deploy — `config.settings.dev` is local-only (`DEBUG=True`, console email, filesystem media). |
| `DJANGO_SECRET_KEY` | Required | `base.py` | Django refuses to start. Never reuse the dev value in prod — sessions, password resets, and the signed preview/download/newsletter-confirm tokens all derive from it. |
| `DJANGO_DEBUG` | Optional (default `False`) | `base.py` | Leaving this unset is the safe default. Setting it `True` in prod is a real security hole (stack traces with source and env vars leak to any visitor) — `check --deploy` warns (W018) if it's ever `True` outside dev. |
| `DJANGO_ALLOWED_HOSTS` | Optional (default `[]`) | `base.py` | With `DEBUG=False` (i.e. in prod) an empty list means **every request 400s** — `CommonMiddleware` can't validate `Host`. Must be set to the real domain(s) before prod ever serves traffic. |
| `DATABASE_URL` | Required | `base.py` | No database connection — nothing works. Format: `postgres://user:pass@host:port/dbname`. |
| `DJANGO_DEFAULT_FROM_EMAIL` | Optional (default `no-reply@example.com`) | `base.py` | Every queued notification/confirmation email goes out from the placeholder address instead of a real one — not a crash, just wrong sender. |
| `EMAIL_HOST` | **Required in prod** (no default) | `prod.py` | `config.settings.prod` fails to import at all — this blocks `collectstatic`, migrations, `runserver`, everything, not just email. The Dockerfile's build-time `collectstatic` step supplies a `build` placeholder for exactly this reason; the real deploy environment needs the actual SMTP relay hostname. |
| `EMAIL_PORT` | Optional (default `587`) | `prod.py` | Wrong port for your relay → SMTP connection failures, so queued emails (contact/demo/popup notifications, handbook-gate, job applications, newsletter confirmation) silently pile up as failed `django_q` tasks instead of sending. |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Optional (default `""`) | `prod.py` | Most relays require auth — leaving these blank means every send attempt fails at the SMTP `AUTH` step. |
| `EMAIL_USE_TLS` | Optional (default `True`) | `prod.py` | Only turn this off if your relay genuinely doesn't support it; most do. |
| `AWS_STORAGE_BUCKET_NAME` | **Required in prod** (no default) | `prod.py` | `config.settings.prod` fails to import — same "nothing works" failure mode as `EMAIL_HOST` above. |
| `AWS_S3_ENDPOINT_URL` | Optional (default `None`) | `prod.py` | Only needed for an S3-*compatible* provider that isn't AWS itself (R2, Spaces, MinIO, ...) — django-storages derives the real AWS endpoint from `AWS_S3_REGION_NAME` on its own, so a real AWS S3 bucket needs this left unset, not filled in with the regional endpoint by hand. |
| `AWS_S3_REGION_NAME` | **Required in prod** | `prod.py` | Same — import-time failure. |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | **Required in prod** | `prod.py` | Same — import-time failure. Without valid credentials specifically (as opposed to just being unset), every media upload/read in the admin and every image render on the public site fails once the app *does* start. |
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | Optional — only read by `manage.py bootstrap_superuser` | `bootstrap_superuser.py` | That one management command errors out (`CommandError`) if any are missing when you run it. Nothing else depends on them; there's no other way to get the first admin login without running this command or `createsuperuser` manually. |
| `ANTHROPIC_API_KEY` | Optional (default `""`) | `base.py` | Not a hard requirement — the grounded chat widget (`chat` app) degrades on purpose: with this unset, `core.context_processors.chat_enabled` returns `False` and the launcher doesn't render anywhere on the site (checked in `chat/tests.py::WidgetVisibilityTests`). Set it to actually enable the widget. |
| `CHAT_DAILY_TOKEN_BUDGET` | Optional (default `200000`) | `base.py` | Total input+output tokens allowed across all `ChatMessage` rows per rolling 24h — `chat/views.py` sums `tokens_used` on every request and degrades the widget to a "use the contact form" pointer once it's exceeded, rather than erroring or overspending. At Haiku 4.5 pricing ($1/$5 per 1M input/output tokens) the 200000 default is roughly $0.30–$0.60/day worst case — tune to your actual traffic and budget. |

Nothing else in the codebase reads an environment variable — `GTM
container ID` and `reCAPTCHA site key` are **not** env vars, see the gap
called out below.

## Admin access and brute-force protection

The Django admin moved from `/admin/` to `/manage/` (`config/urls.py`) —
`/admin/` on the live site should 404, not redirect; there's nothing there to
redirect from. This wasn't a rename for its own sake: `/admin/` is the first
path every credential-stuffing bot tries against a Django site, and moving it
off the well-known default removes that class of automated attempt entirely
without changing anything a real editor does (bookmarks need updating once,
`{% url %}`/`reverse("admin:...")` everywhere else in the codebase resolve
through the `admin` URL *namespace*, which is unaffected by which path it's
mounted at).

**django-axes** (`config/settings/base.py`) locks out further login attempts
after 5 failures within a 30-minute window (`AXES_FAILURE_LIMIT`,
`AXES_COOLOFF_TIME`), keyed on the username+IP combination
(`AXES_LOCKOUT_PARAMETERS`) so a brute-force attempt against one editor's
account doesn't also lock out everyone else on the same office/VPN egress IP.
Every attempt — success, failure, lockout — logs under the `axes` logger
(also configured in `base.py`'s `LOGGING`, console handler, so it's picked up
by whatever's collecting stdout in prod). Locked-out requests get a `429`.
Covered by `core.tests.AdminBruteForceProtectionTests`.

## `DEBUG=False` + `collectstatic` + whitenoise

Verified locally against `config.settings.prod` with dummy AWS/SMTP values
(media/email backends aren't touched by `collectstatic`, so this doesn't
require a real S3 bucket or SMTP relay to confirm):

```
python manage.py check --deploy   # clean, once DJANGO_SECRET_KEY is a real long random value
python manage.py collectstatic --noinput   # clean (two harmless "found another file" notices from
                                            # django-unfold/admin overlapping static paths — not an error)
```

and a request against the collected static tree with `DEBUG=False` and
`whitenoise.storage.CompressedManifestStaticFilesStorage` renders the
homepage and a list page at 200 with `{% static %}` resolving through the
manifest correctly.

`Dockerfile` already runs `collectstatic` at build time with placeholder
`AWS_*`/`EMAIL_HOST` values (added here — see the fix note below) — that
step only touches the filesystem, never a real bucket or relay, so the
placeholders are safe.

## Fixed during this pass (relevant to deploy)

- `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/
  `EMAIL_USE_TLS` didn't exist as settings at all — `prod.py` set
  `EMAIL_BACKEND` to the SMTP backend but never configured *where* to send,
  which means it would have silently tried `localhost:25` with no auth in
  the first real deploy. Added them (see table above) and updated
  `Dockerfile`'s build-time `collectstatic` step and `.env.example` to
  match, since `EMAIL_HOST` has no default and would otherwise break the
  Docker build.

## CRITICAL — the queue worker must run as its own process

**This was the single biggest deploy risk from the readiness audit and is
now fixed, but only if you actually run the second process.** `Dockerfile`'s
`CMD` is gunicorn-only. Every notification email (contact/demo/popup,
handbook-gate, job application) and the newsletter confirmation email is
queued into django-q2's ORM broker (`core/notifications.py`), not sent
inline. If nothing is running `python manage.py qcluster`, those tasks sit
in the `django_q` broker table forever: the form still validates, still
saves the `ContactSubmission`, still shows the success state to the visitor
— and the lead just never reaches anyone. Nothing errors, nothing shows up
in logs, because from the web process's point of view the request succeeded.

**Fix:** run the image twice, with two different commands — see `Procfile`
at the repo root:

```
web:    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
worker: python manage.py qcluster
```

Most PaaS hosts (Render, Railway, Heroku-style buildpacks, Fly with a
`[processes]` block) read a `Procfile` directly and run each line as its own
process/container off the same build — no second Dockerfile needed. If your
host doesn't, translate the `worker:` line into whatever it calls a second
process type/service pointed at the same image.

**Verify it's actually running** — don't just trust that it's configured:

- `python manage.py check_worker_health` — exits non-zero with a clear
  message if no worker has checked in recently. Point a post-deploy CI step
  or a cron job at this.
- `GET /healthz/worker/` — 200 when healthy, 503 when stale/missing. Point
  an external uptime check at this **in addition to** `/healthz/` (the
  latter is gunicorn's own liveness probe via `Dockerfile`'s `HEALTHCHECK`
  and says nothing about the worker — a dead worker must not fail the web
  container's health check, since the web process itself is fine).

Both read `core/worker_health.py`, which looks for a recent `Success` row
for `core.tasks.heartbeat` — scheduled to run every 5 minutes by the
`core/migrations/0003_create_qcluster_heartbeat_schedule.py` data migration
(a django-q2 `Schedule` row, not a schema change of ours). A worker that's
been down for more than ~15 minutes reports unhealthy.

## Resolved during this pass (previously flagged as needing a decision)

- **GTM.** `SiteSettings.gtm_container_id` now renders the standard head
  script + `<body>` `<noscript>` iframe in `templates/base.html`, only when
  the field is set. Fill it in via `/manage/` when you have a container ID —
  nothing else to configure.
- **reCAPTCHA.** Still not implemented — no form does server-side
  verification. Rather than build that silently, `recaptcha_site_key` was
  removed from `SiteSettingsAdmin`'s fieldsets (model field kept, commented
  `# Reserved`) so editors can no longer fill in a value that does nothing.
  Wire up real verification before re-exposing it.

## Cookie consent — RESOLVED: GTM and Calendly are gated

`SiteSettings.calendly_url` (see `core/calendly.py`, `static/js/calendly.js`)
lazy-loads Calendly's own embed script on first use — the demo page's inline
widget, and any "Book a call" popup button. GTM (`SiteSettings.gtm_container_id`)
loads its own third-party script too. Both used to load unconditionally.

**A minimal, owned consent banner now gates both** — no third-party CMP.
One cookie (`cookie_consent` = `accepted` | `rejected`), set client-side:

- `static/js/cookie-consent.js` — the banner's Alpine component
  (`templates/components/_cookie_consent_banner.html`, included in
  `base.html` right after the skip-link so it's an early keyboard tab stop,
  `fixed bottom-0` regardless of DOM position). Escape hides it for that
  visit without recording a choice (returns next load) rather than trapping
  keyboard users; Accept/Reject are plain focusable `<button>`s. GTM only
  loads (`loadGTM()`) once `accepted`; `base.html`'s head script only ever
  stages `window.GTM_CONTAINER_ID`, never the loader itself, and there's no
  `<noscript>` fallback — a no-JS visitor can't run the banner either, so no
  tracking is the correct default for them, not an unconditional tag.
- `static/js/calendly.js` — `window.openCalendlyPopup()` checks consent
  before fetching Calendly's assets; if not yet accepted, it reopens the
  banner and retries automatically once the visitor accepts, rather than
  silently doing nothing on click. The demo page's inline widget
  (`calendlyInlineGate` Alpine component, same file) shows an
  "Enable scheduler" placeholder instead of the embed until accepted.
- Only rendered at all when there's something to gate: `base.html` includes
  the banner behind `{% if site_settings.gtm_container_id or
  site_settings.calendly_url %}`.

Tests: `tests/test_gtm.py`, `tests/test_calendly.py`. No Django test can
exercise the client-side gating itself (cookie read/write, retry-after-accept)
— that was verified manually via Playwright against the running dev server
before this was marked resolved.

## Privacy and Terms pages are unpublished — real copy needed before launch

Both are still `[TODO]` copy (`templates/pages/privacy.html`,
`templates/pages/terms.html`) and the site collects personal data through
five forms (contact, demo, popup, handbook gate, job application) — a
placeholder legal policy must not be linkable. `pages/views.py`'s `privacy()`
and `terms()` now `raise Http404` unconditionally instead of rendering.

**Every place that referenced them, so this can be restored cleanly:**

- `pages/views.py` — `privacy()`/`terms()` raise `Http404`. Restore: replace
  with the original `render(request, "pages/<name>.html", context)` call
  (kept in a comment on each view).
- `templates/base.html` — footer "Privacy"/"Terms" links removed entirely
  (the wrapping `<div>` and the copyright row's `flex justify-between`
  layout were adjusted since it's now just the copyright line — restore
  both the links and that layout together, not just the `<a>` tags).
- `config/sitemaps.py` — `StaticViewSitemap.items()` no longer lists
  `"privacy"`/`"terms"` (a 404'd URL must not appear in the sitemap).
- `tests/test_smoke.py` — moved from `SIMPLE_GET_URLS` (expects 200) to a
  new `UNPUBLISHED_GET_URLS` list (pinned to 404), so a future change can't
  silently re-expose a placeholder policy without a test failing.
- `pages/urls.py` — routes are untouched (`privacy/`, `terms/` still
  resolve, just to a 404 view) — nothing to restore there.
- `templates/pages/privacy.html` / `terms.html` — untouched, still `[TODO]`,
  ready to receive real copy whenever it lands.

**To restore:** write the real copy into both templates, revert the two
views to `render(...)`, re-add the footer links and sitemap entries, and
move the two names back from `UNPUBLISHED_GET_URLS` to `SIMPLE_GET_URLS` in
`tests/test_smoke.py`.

## Must exist externally before first deploy

- **PostgreSQL** reachable at `DATABASE_URL`. `docker-compose.yml` at the repo
  root only covers local dev — `deploy/docker-compose.prod.yml` is the prod
  equivalent (a `db` service alongside `web`/`worker`, see "Deploying to
  EC2" below).
- **S3 bucket** for media (`AWS_STORAGE_BUCKET_NAME` + region + credentials)
  — every uploaded image/PDF/resume lives here in prod, not on local disk.
- **SMTP relay** reachable at `EMAIL_HOST` with working credentials — see
  above.
- **Domain + DNS**, entered into `DJANGO_ALLOWED_HOSTS`, with TLS in front
  of it (`SECURE_SSL_REDIRECT`/HSTS are already on in `prod.py` and assume
  a proxy/load balancer terminates HTTPS and sets
  `X-Forwarded-Proto: https`, per `SECURE_PROXY_SSL_HEADER`).
- **REQUIRED: a worker process running `manage.py qcluster`**, deployed
  alongside (not instead of) the web process — see the CRITICAL section
  above. This is not optional infrastructure; skipping it means every
  contact/demo/handbook/job-application/newsletter email silently never
  sends.
- **301 redirect data** — `Redirect` rows for every old-site URL, loaded via
  `python manage.py import_redirects <csv>` before DNS cutover, per
  CLAUDE.md's SEO section. Not itself infrastructure, but blocking for
  launch and easy to forget.
- If GTM/reCAPTCHA get wired up per the decision above: a **GTM container**
  and **reCAPTCHA site/secret key pair**. Consent gating is already built —
  see the cookie consent section above.
- **Real Privacy/Terms copy**, before re-enabling those pages — see the
  section above for the full restore list.

## Deploying to EC2

Everything below targets a single Ubuntu 24.04 EC2 instance that **already
has an old site running on it** — every script here is written to be safe to
run alongside that old site without touching it, right up until the
deliberate cutover step. Don't skip ahead of that ordering.

Scripts live in `deploy/`:

| File | Runs | Does |
|---|---|---|
| `deploy/setup.sh` | once, as root, on a fresh instance | Installs Docker, Nginx, Certbot; creates the `deploy` user (Docker group, no sudo); creates `/opt/neuroml`; stages `.env.prod`/`deploy/.env` templates and `nginx.conf` (not enabled). |
| `deploy/docker-compose.prod.yml` | via `deploy.sh` | Defines `web` (gunicorn), `worker` (`qcluster`), `db` (postgres:16, named volume). No nginx service — see the file's own header comment for why. |
| `deploy/nginx.conf` | staged by `setup.sh`, enabled manually | Host nginx: TLS termination (once Certbot fills it in), `www` → apex redirect, `/static/` served directly, gzip, security headers. |
| `deploy/deploy.sh` | every deploy, as the `deploy` user | git pull → build → migrate → collectstatic → `bootstrap_superuser` → zero-downtime restart → cache clear → health check. |

### First-time setup

```bash
# On the instance, as a user that can sudo:
git clone <repo-url> /tmp/neuroml-bootstrap   # just to get deploy/setup.sh onto the box
sudo REPO_URL=<repo-url> /tmp/neuroml-bootstrap/deploy/setup.sh
rm -rf /tmp/neuroml-bootstrap

# Add your deploy/CI public key:
sudo -u deploy tee -a /home/deploy/.ssh/authorized_keys < your_key.pub

# Fill in the two env files (values by hand — nothing here generates secrets):
sudo -u deploy vi /opt/neuroml/.env.prod           # see .env.prod.example
sudo -u deploy vi /opt/neuroml/app/deploy/.env     # POSTGRES_DB/USER/PASSWORD
# Make sure .env.prod's DATABASE_URL matches deploy/.env exactly:
#   postgres://<POSTGRES_USER>:<POSTGRES_PASSWORD>@db:5432/<POSTGRES_DB>

# Bring the new site up on :8000 (NOT yet reachable from the internet —
# nginx hasn't been pointed at it):
sudo -u deploy /opt/neuroml/app/deploy/deploy.sh
```

### Verify before touching anything the old site uses

```bash
curl -i http://127.0.0.1:8000/healthz/          # 200 (or a 301 to https — SECURE_SSL_REDIRECT
                                                 # is on; either means the app answered)
curl -i http://127.0.0.1:8000/healthz/worker/   # 200 once the heartbeat schedule has run once
                                                 # (~5 min after first deploy), 503 until then
docker compose -f /opt/neuroml/app/deploy/docker-compose.prod.yml logs -f web worker
```

Only once that's clean: enable the staged nginx site, get a real cert, and
switch DNS. Not before — see the cutover checklist below.

```bash
sudo ln -s /etc/nginx/sites-available/neuroml.conf /etc/nginx/sites-enabled/neuroml.conf
sudo nginx -t && sudo systemctl reload nginx
```

At this point neuroml.ai/www.neuroml.ai (once DNS points here — see below)
serves the new site over plain HTTP. Issue the cert next.

### SSL

```bash
sudo certbot --nginx -d neuroml.ai -d www.neuroml.ai
```

Certbot edits `/etc/nginx/sites-available/neuroml.conf` in place: adds the
`listen 443 ssl` server block(s) with real certificate paths, and (unless you
pass `--no-redirect`) upgrades the existing `www` → apex redirect and adds an
HTTP → HTTPS redirect on the apex block too. It also installs its own
renewal timer (`systemctl status certbot.timer`) — nothing further to set up
for renewal. Re-run the same command to add/renew; it's idempotent.

### DNS

At your registrar/DNS provider, before running certbot (HTTP-01 validation
needs the domain to already resolve here):

| Record | Type | Value |
|---|---|---|
| `neuroml.ai` | A | the EC2 instance's **Elastic IP** (not the instance's default public IP — that changes on stop/start; allocate and associate an Elastic IP first) |
| `www.neuroml.ai` | A | same Elastic IP, **or** CNAME to `neuroml.ai` |

Propagation can take up to the previous records' TTL to fully clear — plan
the DNS change ahead of the cutover window, not as the last step.

### Cutover checklist

Work through this in order. Nothing before "Enable nginx site + SSL" touches
the old site or public traffic at all.

- [ ] `.env.prod` filled with real values (`/opt/neuroml/.env.prod`)
- [ ] `deploy/.env` filled with real Postgres credentials, matching `.env.prod`'s `DATABASE_URL`
- [ ] S3 bucket created and IAM credentials set (`AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, `AWS_S3_REGION_NAME`)
- [ ] SMTP credentials set (Postmark/SES — `EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`)
- [ ] `deploy/deploy.sh` run once, site verified on `127.0.0.1:8000` (see "Verify" above)
- [ ] `bootstrap_superuser` confirmed — `deploy.sh` runs it every deploy, but confirm you can actually log in at `/manage/` before going further
- [ ] `seed_demo` + `seed_portfolio` + `seed_igaming` run, **or** real content already loaded — a blank homepage is not a launch state
- [ ] `attach_case_study_images` run, if seeding demo/portfolio data
- [ ] Privacy and Terms pages restored from 404 — see "Privacy and Terms pages are unpublished" above; do this before DNS cutover, not after, since the placeholder-404 state must never be reachable at the real domain
- [ ] `qcluster` worker confirmed running — `docker compose -f deploy/docker-compose.prod.yml ps worker` shows it up, and `/healthz/worker/` returns 200 (allow ~5 min after first deploy for the first heartbeat)
- [ ] GTM container ID set in admin (`/manage/`, `SiteSettings.gtm_container_id`) — optional, but decide and set (or deliberately leave blank) before launch, not after
- [ ] 301 redirect data imported — `python manage.py import_redirects <csv>` (see "Must exist externally before first deploy" above)
- [ ] DNS A record(s) pointing at the instance's Elastic IP (see DNS above) — propagated, not just set
- [ ] Nginx site enabled + reloaded (`ln -s` + `nginx -t` + `systemctl reload nginx`, see above)
- [ ] SSL certificate issued via certbot (see SSL above) — confirm `https://neuroml.ai` loads with a valid cert, and `http://` and `www.` both redirect correctly
- [ ] First form submission tested end to end — submit the real contact form on the live domain, confirm the `ContactSubmission` row is created *and* the notification email actually arrives (this exercises the whole path: nginx → gunicorn → DB → qcluster → SMTP relay, and is the single check most likely to catch a worker/SMTP misconfiguration that everything above would miss)
- [ ] Only now: confirm the old site's files/config can be retired — see the opening paragraph of this section on why every step before this one was written to leave it untouched

### Ongoing deploys

Either by hand:

```bash
ssh deploy@<host> /opt/neuroml/app/deploy/deploy.sh
```

or automatically via `.github/workflows/ci.yml`'s `deploy` job — builds and
pushes the image to GitHub Container Registry (audit trail / rollback
artifact; `deploy.sh` itself does its own `git pull` + local build rather
than pulling that image, so the EC2 box never needs registry credentials),
then SSHes in and runs `deploy.sh`. Gated to `push` on `main`, after both the
`test` and `build` jobs pass. Needs three repo secrets: `EC2_HOST`,
`EC2_USER` (`deploy`), `EC2_SSH_KEY` (that user's private key — its public
half goes in `authorized_keys`, see first-time setup above).

### Monitoring

- **`GET /healthz/`** — 200 from gunicorn itself (`core/views.py`). This is
  also the Dockerfile's own `HEALTHCHECK`, so `docker ps` already reflects it
  per-container; point an external check at it too for real uptime coverage.
- **`GET /healthz/worker/`** — 200 while the `qcluster` worker has checked in
  within the last 15 minutes (3× its 5-minute heartbeat schedule — see
  `core/worker_health.py`), 503 once it's stale or has never run. A dead
  worker does **not** fail `/healthz/`'s check — the web process is fine even
  when the worker isn't, which is exactly why this is a separate endpoint;
  point a separate uptime check at it, not just a mental note to "also check
  the worker sometime."
- **UptimeRobot** (free tier): two HTTP(S) monitors, one per endpoint above,
  5-minute interval. Alert on `/healthz/` failing means the site is down;
  alert on `/healthz/worker/` failing means the site is *up* but every
  contact/demo/handbook/job-application/newsletter email is silently piling
  up unsent — different severity, different response, which is the whole
  reason these are two endpoints instead of one.
- **CloudWatch basic monitoring** (free tier, on by default for any EC2
  instance at 5-minute granularity — nothing to enable): watch CPU
  utilization, network in/out, and status check failures on the instance.
  Basic monitoring doesn't cover memory or disk out of the box; if either
  becomes a concern later, that's the CloudWatch agent (not free-tier-only),
  not something this deploy sets up preemptively.
