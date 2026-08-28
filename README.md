# Site rebuild

Marketing site for an AI/ML consultancy. Django 5 + PostgreSQL backend,
Django admin (skinned with django-unfold) as the CMS, server-rendered
templates with Tailwind + HTMX for the frontend. See `CLAUDE.md` for the full
set of project conventions — read it before making changes.

## Stack

- Django 5, PostgreSQL, Python 3.12
- django-unfold for the admin UI, CKEditor 5 for rich text
- Tailwind + HTMX + a little Alpine for the frontend — no JS framework
- django-storages → S3-compatible object storage for media (prod only);
  local filesystem in dev
- easy-thumbnails for responsive image srcsets
- django-q2 for async email (ORM broker — no Redis needed at this volume)
- django-csp for Content-Security-Policy headers
- whitenoise for static files

## Local setup

1. **Start Postgres.**

   ```
   docker compose up -d
   ```

2. **Create a virtualenv and install dependencies.**

   ```
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install frontend tooling and build CSS once.**

   ```
   npm install
   npm run build:css
   ```

   Use `npm run watch:css` instead while actively changing `tailwind.config.js`
   or `static/css/src/input.css` — it rebuilds `static/css/dist/main.css` on
   every change. That file is gitignored; nothing loads without running one
   of these at least once.

4. **Copy `.env.example` to `.env` and fill it in.** The defaults match
   `docker-compose.yml`, so local setup mostly just needs a real
   `DJANGO_SECRET_KEY` and superuser credentials.

5. **Migrate and create a superuser.**

   ```
   python manage.py migrate
   python manage.py bootstrap_superuser
   ```

6. **Seed demo content** so every page section has something to render
   (placeholder copy and grey SVG images throughout — never ships to
   production by accident):

   ```
   python manage.py seed_demo
   ```

   Add `--flush` to wipe and reseed.

7. **Run the server.**

   ```
   python manage.py runserver
   ```

   Visit `/` for the site, `/manage/` for the CMS.

8. **(Optional) run the async email worker** so queued notification/newsletter
   emails actually send (to the console in dev, since `EMAIL_BACKEND` there is
   `console`):

   ```
   python manage.py qcluster
   ```

   Without this running, form submissions still save correctly — the email
   just sits queued in the `django_q` tables until a worker picks it up.

## Running tests

```
python manage.py test
```

Every form (contact, demo, popup, newsletter, gated handbook, job
application) has coverage for: valid submit, invalid submit, honeypot
triggered, rate limit hit. The redirect middleware and the `Publishable.live()`
manager (the thing standing between a draft and it leaking onto a public page)
are covered directly in `core/tests.py`.

## Adding content

Everything a content editor touches lives in `/manage/`, not in a template or
a migration. A few things worth knowing before you start:

- **Draft → In review → Published** is the workflow on every content type.
  Nothing goes live without a `published_at` — set a future date to schedule
  a post, past/now to publish immediately.
- **Preview**: every publishable admin form has a "Open preview" link that
  works even in draft, via a signed token — no need to flip status to
  Published just to see how something looks.
- **The nav is never hand-edited.** Adding a service, industry, or product
  and ticking `show_in_nav` is enough — the megamenu, footer, and homepage
  sections that reference it all update automatically (cached 5 minutes; see
  `core/context_processors.py`).
- **Metrics live on the case study**, not the homepage. Add them once as
  `Metric` inlines on a `CaseStudy` and they render both there and in the
  homepage's featured case study cards.
- **Writers vs. editors**: writers only see their own drafts; editors and
  superusers see everything. This is enforced in `PublishableAdmin.get_queryset`
  — don't bypass it from a shell or a script.
- **Images**: upload whatever size you have — `core/templatetags/imaging.py`
  generates a responsive srcset via easy-thumbnails automatically. SVGs (like
  the seed data's placeholder logos) pass through untouched.

## How redirects work

Every URL from the old site needs to keep working after cutover — the
`Redirect` model plus `core.middleware.RedirectMiddleware` handles this.

- The middleware only ever looks at a response that's *already* a real 404 —
  it never intercepts a URL that resolved successfully — looks up
  `Redirect.old_path`, and issues a 301 (or 302, if `permanent=False`) to
  `new_path`. Each hit increments `hit_count`, so sorting the admin list by
  that column after launch tells you which redirects are actually earning
  their keep, and cross-referencing against GSC's 404 report catches
  anything missing.
- **Bulk import**: put every `old_path,new_path[,permanent]` row in a CSV and
  run:

  ```
  python manage.py import_redirects path/to/redirects.csv --dry-run
  python manage.py import_redirects path/to/redirects.csv
  ```

  `permanent` is optional per-row and defaults to `true` (301).

- **Verify before and after launch**:

  ```
  python manage.py check_redirects --base-url https://your-live-domain.example
  ```

  Hits every stored `old_path` against that origin and reports any that
  don't resolve cleanly to a 200 at the end of the chain.

## Deploying

`Dockerfile` is a multi-stage build (Node stage compiles Tailwind, Python
stage installs dependencies, a slim runtime stage runs as a non-root `app`
user) exposing `/healthz/` for the container/load balancer health check.
`.github/workflows/ci.yml` runs `manage.py check`, `check --deploy` against
prod settings, the test suite, and a build of the image on every push and PR.

Before going live: fill in every `AWS_S3_*` var, set `DJANGO_SETTINGS_MODULE=
config.settings.prod`, and run `python manage.py check --deploy` against
those settings — it's clean today, but re-run it after any settings change.

For an actual deploy to AWS EC2 — server setup, Docker Compose, Nginx/TLS,
the deploy script, CI's `deploy` job, DNS, and the cutover checklist — see
`deploy/` and DEPLOY.md's "Deploying to EC2" section.

## What's still a placeholder

- Logo: `SiteSettings.logo` / `logo_dark` render an SVG once uploaded; until
  then the header/footer fall back to the site name set in Instrument Serif.
- Several homepage/flat-page headings and the closing CTA copy are
  `[TODO: ...]` strings — obvious and greppable on purpose, per CLAUDE.md.
- Video (`Testimonial.video_url`, `Webinar.recording_url`) links out rather
  than embedding inline — no iframe/CSP `frame-src` wiring yet.
# neuroml-site-v2
