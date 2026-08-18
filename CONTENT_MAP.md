# Content map & rebuild plan

Derived from the current site structure. Design is being redone from scratch —
this covers information architecture only.

---

## 1. Page inventory → model mapping

| Current page type | Count | New model | Notes |
|---|---|---|---|
| Homepage | 1 | `HomePage` (singleton) + querysets | Sections pull from real models instead of hardcoded Elementor blocks |
| Service pages | ~14 | `Service` | Grouped by `ServiceCluster` (Enterprise AI Agent / Agentic AI Foundry / AI Readiness & Roadmap) |
| Use-case pages | ~24 | `UseCase` | Grouped by `Industry`; `show_on_homepage` drives the homepage tabs |
| Product pages | 2 | `Product` | AI Agent for Logistics, AI Retail Assistant |
| Blog posts | many | `BlogPost` | Currently `/category/blog/` |
| Case studies | many | `CaseStudy` + `Metric` inline | Currently `/category/case-study/` |
| Handbooks | many | `Handbook` | Currently `/category/handbook/`; gating optional |
| Webinars | many | `Webinar` | Currently `/category/webinar/`; upcoming vs on-demand |
| About | 1 | Template + `TeamMember`, `ProcessStep`, `EngagementModel` | The four "Why choose us" tabs are three small models |
| Careers | 1 | Template (or a `JobPosting` model if you post roles often) | Out of scope for v1 unless you're hiring |
| Contact / Book a demo | 2 | Template + `ContactSubmission` | |
| Privacy policy | 1 | Flat page | |

**The big win:** ~38 hand-built layout pages collapse into 3 models and 3
templates. A writer fills in fields; the layout is not their problem.

---

## 2. What's currently structural debt

1. **Four content types faked as WordPress categories.** Case studies can't
   carry client, industry, or metrics as real fields, so the "98% Stock
   Accuracy" numbers on the homepage are typed by hand into a separate widget
   from the case study they describe. They drift. `Metric` as an inline on
   `CaseStudy` fixes this — enter once, render on both the case study and the
   homepage card.

2. **The megamenu is hardcoded.** Six industries × four use cases, three
   service clusters × four services, plus the org-type column — all maintained
   by hand in Elementor. Generate it from `Service`, `Industry`, `Product`
   querysets filtered on `show_in_nav` and ordered by `order`. Adding a
   service becomes one admin save, not a menu edit.

3. **NitroPack is a symptom.** A caching layer bolted on to fight page weight.
   Server-rendered Django templates don't need it.

4. **Dead-end nav links.** A significant number of menu items point at
   `/book-a-demo/` rather than a real page. Worth deciding per item: build the
   page, or drop it from the nav. Nav entries that don't resolve to content
   hurt both users and crawl budget.

---

## 3. URL scheme

Current URLs are flat (`/respond-to-rfps-faster/`) with categories at
`/category/<name>/`. Flat slugs across five content types risk collisions and
make it impossible to tell a blog post from a service page.

Recommended:

```
/                               home
/services/<slug>/               Service
/industries/<slug>/             Industry hub
/use-cases/<slug>/              UseCase
/products/<slug>/               Product
/blog/                          BlogPost list
/blog/<slug>/                   BlogPost
/case-studies/                  CaseStudy list
/case-studies/<slug>/           CaseStudy
/handbooks/<slug>/              Handbook
/webinars/<slug>/               Webinar
/about/  /careers/  /contact/   flat pages
```

If preserving existing link equity matters more than clean URLs, the
alternative is keeping flat slugs and adding a global slug-uniqueness check
across all content models. Cleaner URLs plus 301s is the better trade —
redirects pass nearly all ranking signal.

---

## 4. Redirect plan

Non-negotiable before launch. Every existing indexed URL needs a 301.

1. Export the full URL list: `sitemap_index.xml` on the current site, or
   Screaming Frog if the sitemap is incomplete.
2. Pull Google Search Console → Pages → all indexed URLs. Catches pages
   missing from the sitemap that still earn traffic.
3. Load both into the `Redirect` model (`old_path` → `new_path`).
4. Add middleware that catches 404s, looks up `Redirect`, increments
   `hit_count`, and issues the 301.
5. Post-launch, sort `Redirect` by `hit_count` to see what's actually being
   followed, and check GSC for 404 spikes weekly for the first month.

The `hit_count` field also surfaces URLs you forgot — anything hitting a 404
with real traffic shows up in logs.

---

## 5. Build phases

**Phase 1 — data layer**
Models, migrations, admin, roles, media storage (S3/GCS via `django-storages`),
`django-unfold` for the admin skin. Import existing content. At the end of
this phase the team can write, even with no frontend.

**Phase 2 — templates**
Base layout, generated nav, the three list templates and five detail templates,
homepage sections wired to querysets. Responsive from the start.

**Phase 3 — forms & integrations**
Contact, demo booking, handbook gating, newsletter. All land in
`ContactSubmission` tagged by `source`. If you keep Zoho Bookings, embed it
rather than rebuilding scheduling.

**Phase 4 — launch**
Redirects loaded, sitemap + robots.txt, structured data (`Article` for posts,
`Organization` for the site), OG tags, analytics, then cutover.

---

## 6. Open decisions

- **Frontend:** Django templates + Tailwind, or Django API + Next.js. Templates
  are one deploy and fast by default; Next.js gives more animation headroom.
  Doesn't affect anything in `models.py`.
- **Rich text:** CKEditor 5 (familiar, WYSIWYG) or TipTap with a JSON field
  (cleaner output, more frontend work). Swap the `RichTextField` alias.
- **Careers:** flat page, or a `JobPosting` model with an application form.
- **Content ownership:** if this rebuild is for a different brand, the copy,
  case studies, testimonials, and client logos on the reference site belong to
  that company — the structure is fair game, the words and client names aren't.
