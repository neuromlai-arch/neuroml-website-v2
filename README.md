# Site rebuild — spec bundle

This is **not a runnable Django project.** It's the content architecture and the
build plan. The actual project gets scaffolded in the first Claude Code session
using these files as the spec.

## What's here

| File | What it is |
|---|---|
| `CONTENT_MAP.md` | Page inventory, model mapping, URL scheme, redirect plan, build phases. Read this first. |
| `models.py` | The full content model. Designed to be split across apps — see the docstring at the top. |
| `admin.py` | Django admin config: fieldsets, inlines, publish workflow, Writer/Editor roles. |
| `BUILD_PROMPTS.md` | Four session prompts for Claude Code, in order. |
| `CLAUDE.md` | Project conventions. Claude Code reads this automatically each session. |

## Order of operations

1. `git init` and commit these files as-is. You want the scaffold to land as a
   reviewable diff against the spec, not mixed in with it.
2. Open the repo in VS Code with Claude Code.
3. Paste **Session 1** from `BUILD_PROMPTS.md`. This scaffolds the project,
   splits the models and admin into apps, and gets the admin working.
4. Commit. Verify you can create a case study with metrics and publish it.
5. Fill in the `[DESCRIBE YOUR DESIGN HERE]` placeholder in Session 2 before
   running it. Leave it blank and you'll get generic output.
6. Sessions 2, 3, 4 in order, committing between each.

## Before you start

Two decisions that aren't made yet:

- **Frontend:** Django templates + Tailwind (the default in these prompts), or
  Django-as-API + Next.js. See the last section of `BUILD_PROMPTS.md`. Doesn't
  affect `models.py` either way.
- **Rich text:** CKEditor 5 (assumed here) or TipTap with a JSONField. One-line
  change to the `RichTextField` alias in `models.py`.

## The two things most likely to bite

**Redirects.** If this replaces an indexed site, every existing URL needs a 301
before cutover. Section 4 of `CONTENT_MAP.md` covers the process. This is the
highest-risk part of the whole project and the easiest to leave until too late.

**The megamenu.** It generates from querysets rather than being hardcoded. It's
the most likely place where the model design meets reality and needs adjusting —
if it fights you, change the models rather than patching it in templates.

## Content ownership

If this rebuild references an existing site you don't own, the structure and
models here are yours to use. The copy, case studies, testimonials, client names,
and logos on that site are not — those need writing fresh.
