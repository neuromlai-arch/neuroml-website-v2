# Deploy checklist

This is a launch-readiness reference, not a deploy trigger — nothing in this
repo has been deployed. Read this before the first real deploy.

## Environment variables

Everything is read via `django-environ` from a real `.env` file or the
process environment — see `.env.example` for the canonical list. `Required`
below means "Django raises `ImproperlyConfigured` and refuses to start
without it"; `Optional` means there's a working default.

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
| `AWS_S3_ENDPOINT_URL` | **Required in prod** | `prod.py` | Same — import-time failure. Point this at your S3-compatible provider's endpoint (AWS S3 itself, R2, Spaces, etc). |
| `AWS_S3_REGION_NAME` | **Required in prod** | `prod.py` | Same — import-time failure. |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | **Required in prod** | `prod.py` | Same — import-time failure. Without valid credentials specifically (as opposed to just being unset), every media upload/read in the admin and every image render on the public site fails once the app *does* start. |
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | Optional — only read by `manage.py bootstrap_superuser` | `bootstrap_superuser.py` | That one management command errors out (`CommandError`) if any are missing when you run it. Nothing else depends on them; there's no other way to get the first admin login without running this command or `createsuperuser` manually. |

Nothing else in the codebase reads an environment variable — `GTM
container ID` and `reCAPTCHA site key` are **not** env vars, see the gap
called out below.

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
  the field is set. Fill it in via `/admin/` when you have a container ID —
  nothing else to configure.
- **reCAPTCHA.** Still not implemented — no form does server-side
  verification. Rather than build that silently, `recaptcha_site_key` was
  removed from `SiteSettingsAdmin`'s fieldsets (model field kept, commented
  `# Reserved`) so editors can no longer fill in a value that does nothing.
  Wire up real verification before re-exposing it.

## Privacy — Calendly sets third-party cookies

`SiteSettings.calendly_url` (see `core/calendly.py`, `static/js/calendly.js`)
lazy-loads Calendly's own embed script on first use — the demo page's inline
widget, and any "Book a call" popup button. Calendly's embed sets its own
third-party cookies once loaded, outside this app's control.

**No cookie consent mechanism exists in this codebase yet.** If EU traffic is
expected, a consent banner is needed before launch, and the Calendly embed
(script load, inline widget, and every popup button) should be gated behind
consent once one exists — right now every scheduling entry point loads
Calendly the moment a visitor interacts with it, unconditionally. Not building
that banner now; flagging it as a pre-launch dependency if `calendly_url` is
set and EU visitors are in scope.

## Must exist externally before first deploy

- **PostgreSQL** reachable at `DATABASE_URL`. `docker-compose.yml` only
  covers local dev (a single `db` service, no prod config).
- **S3-compatible bucket** for media (`AWS_STORAGE_BUCKET_NAME` +
  endpoint/region/credentials) — every uploaded image/PDF/resume lives
  here in prod, not on local disk.
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
  and **reCAPTCHA site/secret key pair**.
- If `calendly_url` is set and EU traffic is expected: a **cookie consent
  banner**, with the Calendly embed gated behind it — see the Privacy section
  above. Not built yet.
