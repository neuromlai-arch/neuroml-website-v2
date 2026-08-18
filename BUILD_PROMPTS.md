# Build prompts for Claude Code

Four sessions. Run them in order, start a fresh session for each, and commit
between phases. Drop `models.py`, `admin.py`, and `CONTENT_MAP.md` into the repo
root before session 1 so Claude has them as reference.

**Default stack assumed below:** Django 5 + PostgreSQL + Django templates +
Tailwind + HTMX. If you'd rather do Django-as-API + Next.js, see the note at the
bottom — sessions 1 and 3 are unchanged either way.

---

## Session 1 — Project scaffold, models, admin

```
I'm building a marketing site for an AI/ML consultancy. Django 5 + PostgreSQL
backend, Django admin as the CMS. Server-rendered templates with Tailwind and
HTMX for the frontend (that comes in a later session — not now).

I've put three reference files in the repo root:
- models.py — the full content model I want, already designed
- admin.py — the admin configuration I want
- CONTENT_MAP.md — page inventory, URL scheme, and rationale

Read all three first. They're the spec, not a starting point to improvise on.

Set up the project:

1. Django 5 project named `site_backend`, with apps split as described in the
   docstring at the top of models.py: core, taxonomy, people, solutions,
   insights, marketing, pages. Split the reference models.py and admin.py into
   the right app files — don't leave them as monoliths.

2. Settings split into base/dev/prod under `config/settings/`. Use
   django-environ for config. Never commit secrets.

3. PostgreSQL via DATABASE_URL. Include a docker-compose.yml with Postgres
   so I can run this locally without installing anything.

4. Dependencies: django, psycopg[binary], django-environ, Pillow,
   django-storages[s3], django-unfold, django-ckeditor-5, whitenoise,
   gunicorn. Pin versions in requirements.txt (or pyproject if you prefer uv).

5. Wire django-unfold: change the ModelAdmin/TabularInline/StackedInline
   imports in the admin files to unfold's equivalents and add the required
   settings. Everything else in admin.py should work unchanged.

6. Swap the `RichTextField = models.TextField` alias in core for CKEditor 5's
   CKEditor5Field, and configure a sensible toolbar (headings, bold, italic,
   lists, links, images, code blocks, blockquote).

7. Media on S3-compatible storage via django-storages in prod, local
   filesystem in dev. Static via whitenoise.

8. Add the redirect middleware described in section 4 of CONTENT_MAP.md:
   catch 404s, look up the Redirect model, increment hit_count, return 301.

9. Turn `create_default_groups()` at the bottom of admin.py into a proper
   data migration so the Writer and Editor groups exist after migrate.

10. Add a `preview` capability: a signed-token view that lets a logged-in
    editor see an unpublished object rendered. Stub the template for now —
    just make the URL and permission check work.

Then: make migrations, run them, create a superuser via a management command
with credentials from env vars, and confirm `python manage.py check` and
`python manage.py runserver` both come up clean.

Don't write any frontend templates in this session beyond a bare base.html
placeholder. I want the admin working end to end first.
```

**Done when:** you can log into `/admin/`, create a case study with metrics
inline, save it as a draft, and publish it.

---

## Session 2 — Templates and frontend

```
Continuing the marketing site build. The Django backend, models, and admin are
done and working — read the existing apps before writing anything.

Build the frontend with Django templates + Tailwind + HTMX. No React.

Design direction: [DESCRIBE YOUR DESIGN HERE — see note below]

1. Tailwind via django-tailwind or a standalone CLI build. Set up a design
   token layer in tailwind.config.js — colours, type scale, spacing — so the
   whole site restyles from one file.

2. base.html with:
   - A megamenu generated from querysets, NOT hardcoded. Solutions pulls from
     ServiceCluster -> Service (show_in_nav=True, ordered). Industries pulls
     from Industry -> UseCase. Products pulls from Product. Build this as a
     context processor or template tag so it's cached and available everywhere.
   - Footer with quick links, services, contact, newsletter signup.
   - SEO block: title, meta description, canonical, OG tags, all reading from
     the SEOFields mixin with sensible fallbacks.

3. Homepage. Every section reads from the database:
   - Hero from the HomePage singleton
   - Expertise cards from ServiceCluster
   - Partner and client logo rows from Partner / ClientLogo
   - Industry-tabbed use cases from UseCase where show_on_homepage=True,
     grouped by industry. Tabs via HTMX or Alpine, no full page reload.
   - Featured case studies from CaseStudy where featured=True, rendering the
     Metric inlines as the stat pairs
   - Insights section from BlogPost and Handbook
   - Testimonials from Testimonial where featured=True
   - CTA with the contact form

4. Detail templates: service, use case, product, blog post, case study,
   handbook, webinar, industry hub.

5. List templates: blog index, case study index, handbook index, webinar index.
   Each with filtering by industry/tag via HTMX so filters don't reload the page.
   Paginate at 12.

6. Flat pages: about (pulling TeamMember, ProcessStep, EngagementModel),
   careers, contact, privacy.

7. Responsive at 375 / 768 / 1280. Mobile nav as a full-screen drawer.

8. Images: use django-imagekit or easy-thumbnails to generate responsive
   srcsets. Lazy-load everything below the fold. This site should score 90+
   on Lighthouse performance without a caching plugin.

9. Finish the preview view from session 1 so drafts render in the real template.

Accessibility is not optional: semantic landmarks, visible focus states, alt
text from the hero_alt fields, keyboard-navigable menus, AA contrast.
```

**Fill in the design direction before running this.** Claude Code will invent
something generic otherwise. Give it: two or three reference sites you like, your
colour palette, your font choices, and whether you want the feel to be dense and
technical or spacious and editorial.

---

## Session 3 — Forms and integrations

```
Continuing the marketing site. Backend and templates are done — read them first.

Add the forms layer:

1. Contact form -> ContactSubmission with source='contact'. HTMX submit,
   inline validation, success state without a page reload.

2. Book-a-demo form -> ContactSubmission with source='demo'. If there's an
   existing scheduling tool (Calendly/Zoho), embed it after submit rather
   than rebuilding scheduling.

3. Handbook gating: when Handbook.gated is True, show a form instead of the
   download button. On submit, create a ContactSubmission with
   source='handbook' and the handbook FK set, then serve the PDF via a
   time-limited signed URL — don't expose the raw file path.

4. Newsletter signup -> NewsletterSubscriber, with double opt-in: send a
   confirmation email, set confirmed=True on click.

5. Email notifications on every form submission, sent async. Use django-q2 or
   Celery with Redis — pick the simpler one and justify it. Templated HTML
   emails, not plain strings in the view.

6. Spam protection: honeypot field plus rate limiting per IP. No CAPTCHA
   unless the honeypot proves insufficient.

7. All forms as Django Form classes with server-side validation. Never trust
   client-side validation alone.

Write tests for each form: valid submission, invalid submission, honeypot
triggered, rate limit hit.
```

---

## Session 4 — Launch prep

```
Final phase for the marketing site. Read the whole codebase first.

1. sitemap.xml via django.contrib.sitemaps, covering every published content
   type. robots.txt pointing at it.

2. JSON-LD structured data: Organization on every page, Article on blog posts,
   FAQPage where relevant. Validate against Google's Rich Results Test.

3. A management command `import_redirects` that takes a CSV of old_path,new_path
   and bulk-loads the Redirect model. Include a --dry-run flag.

4. A management command `check_redirects` that hits every Redirect's old_path
   against the live site and reports any that don't resolve.

5. Error pages: 404 and 500, styled to match the site.

6. Security pass: SECURE_SSL_REDIRECT, HSTS, secure cookies, CSP headers via
   django-csp, DEBUG=False verified in prod settings. Run
   `python manage.py check --deploy` and fix everything it flags.

7. Dockerfile (multi-stage, non-root user) and a deploy config for [YOUR HOST].
   Include a health check endpoint.

8. GitHub Actions: run tests, run `check --deploy`, build the image.

9. A README covering local setup, how to run migrations, how to add content,
   and how the redirect system works — written for someone who isn't me.

10. Test coverage report. Aim for the models, forms, and redirect middleware
    to be well covered; templates less so.
```

---

## If you want Next.js instead of templates

Session 1 stays the same. Replace session 2 with:

```
Add Django REST Framework and expose read-only endpoints for every published
content type, with filtering by industry/tag and pagination. Include a preview
endpoint that returns unpublished content when given a valid signed token.
Generate an OpenAPI schema with drf-spectacular.
```

Then build the Next.js frontend as a separate repo/session using the generated
schema. Trade-off: two deploys and two repos, in exchange for more animation and
layout freedom. The Django admin experience is identical either way.

---

## Tips for running these

- **Start each session fresh.** Long contexts degrade; a clean session reading
  existing code beats one session carrying four phases of history.
- **Commit between phases**, and ideally between numbered items within a phase.
  Gives you a rollback point when Claude Code takes a wrong turn.
- **Add a CLAUDE.md to the repo root** (see the companion file) so conventions
  don't need restating every session.
- **Review the migrations by hand.** Auto-generated migrations on a model set
  this size occasionally do something surprising with M2M through-tables.
- **Push back in-session.** If it generates something you don't like, say so
  specifically rather than starting over — it iterates well on concrete
  criticism.
