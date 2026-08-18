# CLAUDE.md

Project conventions. Read this before making changes.

## What this is

A marketing site for an AI/ML consultancy. Django backend, Django admin as the
CMS, server-rendered templates. Content is authored by a small non-engineering
team, so the admin experience matters as much as the public site.

## Stack

- Django 5, PostgreSQL, Python 3.12
- django-unfold for the admin UI
- CKEditor 5 for rich text
- Tailwind + HTMX for the frontend (no React)
- django-storages -> S3-compatible object storage for media
- whitenoise for static files

## Architecture rules

**Content models are the source of truth.** Nothing that a content editor
should be able to change belongs in a template. If you find yourself
hardcoding a heading, a stat, a menu item, or a card — it's a field or a
model, not a string in HTML.

**The nav is generated, never hardcoded.** It builds from `Service`,
`Industry`, and `Product` querysets filtered on `show_in_nav`. Adding a
service should require zero template edits.

**Metrics are entered once.** `Metric` is an inline on `CaseStudy`. It renders
on both the case study page and the homepage card. Never duplicate the values
into another model or template.

**Publishing is `status` + `published_at`.** A future `published_at` on a
published record means scheduled. Use `Model.objects.live()` — never filter on
status alone in a view, or drafts leak.

## Conventions

- Apps stay small and single-purpose. If an app's models.py exceeds ~300 lines,
  it's probably two apps.
- Business logic goes in models and managers, not views. Views should be thin.
- Query optimisation is not optional on list views: `select_related` for FKs,
  `prefetch_related` for M2Ms and inlines. Every list view should be a
  bounded, predictable number of queries regardless of page size.
- Templates use `{% include %}` for repeated components; put them in
  `templates/components/`.
- No inline styles. Tailwind classes only, with design tokens defined in
  `tailwind.config.js`.
- Migrations are reviewed by hand before committing.

## Admin conventions

- Every content model gets `list_display`, `list_filter`, and `search_fields`.
  An editor should never have to scroll to find something.
- Field `help_text` is written for a non-engineer. "Shown under the title in
  search results" — not "meta description string".
- Group fields into `fieldsets`. Collapse the SEO block.
- Anything a writer shouldn't touch (submission records, hit counts) is
  `readonly_fields`.
- Writers see only their own drafts; editors see everything. This is enforced
  in `PublishableAdmin.get_queryset` — don't bypass it.

## Testing

- Models, managers, forms, and the redirect middleware need real coverage.
- Every form gets tests for: valid submit, invalid submit, honeypot triggered,
  rate limit hit.
- Templates get smoke tests (does the page render, 200 status) rather than
  assertion-heavy tests.
- Run `python manage.py check --deploy` before considering anything done.

## Security

- `DEBUG=False` in anything that isn't local dev. No exceptions.
- Secrets come from environment variables via django-environ. Nothing secret
  in the repo, ever — including in migrations, fixtures, and test files.
- Gated file downloads use time-limited signed URLs. Never expose a raw
  storage path.
- All forms are Django `Form` classes with server-side validation.

## SEO — treat as load-bearing

This is a rebuild of an existing indexed site. Losing rankings is the main risk
of the whole project.

- Every URL from the old site needs a 301. The `Redirect` model plus middleware
  handles it; the CSV import is a management command.
- Every content model uses the `SEOFields` mixin with template fallbacks.
- Sitemap covers every published content type.
- Don't change a published URL without adding a redirect in the same commit.

## What not to do

- Don't add a JavaScript framework. HTMX and a little Alpine cover the
  interactivity this site needs.
- Don't add a caching layer to fix slow pages. Fix the queries or the images.
- Don't create a model without asking whether an existing one plus a field
  would do.
- Don't invent copy. If content is missing, use an obvious placeholder like
  `[TODO: hero heading]` so it's greppable before launch.
