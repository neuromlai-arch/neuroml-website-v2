"""Attaches monochrome SVG icons to Service, Industry, and ProcessStep rows
from a directory of files named <slug>.svg or <slug>.png. Service and
Industry already have their own slug field; ProcessStep doesn't, so it's
matched on slugify(title) instead — same pattern as attach_recognition_badges
uses for Recognition.

Idempotent: skips any row that already has an icon.

Usage:
    python manage.py attach_icons --source static/brand/icons
    python manage.py attach_icons --source <dir> --dry-run
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from marketing.models import ProcessStep
from solutions.models import Service
from taxonomy.models import Industry


class Command(BaseCommand):
    help = "Attaches <slug>.svg/<slug>.png icons to Service, Industry, and ProcessStep rows from --source."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", required=True,
            help="Directory to search for <slug>.svg / <slug>.png files.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would happen without writing anything.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).expanduser()
        if not source.is_dir():
            raise CommandError(f"Not a directory: {source}")

        dry_run = options["dry_run"]
        totals = {"attached": 0, "skipped_existing": 0, "missing": 0}

        groups = [
            ("Service", Service.objects.order_by("slug"), lambda obj: obj.slug),
            ("Industry", Industry.objects.order_by("slug"), lambda obj: obj.slug),
            ("ProcessStep", ProcessStep.objects.order_by("order"), lambda obj: slugify(obj.title)),
        ]

        for label, queryset, slug_fn in groups:
            attached, skipped_existing, missing = [], [], []
            for obj in queryset:
                if obj.icon:
                    skipped_existing.append(str(obj))
                    continue

                image_path = self._find_image(source, slug_fn(obj))
                if image_path is None:
                    missing.append(str(obj))
                    continue

                attached.append((str(obj), image_path.name))
                if not dry_run:
                    with image_path.open("rb") as fh:
                        obj.icon.save(image_path.name, File(fh), save=False)
                    obj.save()

            verb = "Would attach" if dry_run else "Attached"
            self.stdout.write(f"\n{label}:")
            self.stdout.write(f"  {verb} {len(attached)}:")
            for name, filename in attached:
                self.stdout.write(f"    {name} <- {filename}")
            self.stdout.write(
                f"  Skipped {len(skipped_existing)} (already had an icon): "
                f"{', '.join(skipped_existing) or 'none'}"
            )
            self.stdout.write(
                f"  Missing {len(missing)} (no matching file in {source}): "
                f"{', '.join(missing) or 'none'}"
            )
            totals["attached"] += len(attached)
            totals["skipped_existing"] += len(skipped_existing)
            totals["missing"] += len(missing)

        verb = "Would attach" if dry_run else "Attached"
        self.stdout.write(
            f"\n{verb} {totals['attached']} total, "
            f"skipped {totals['skipped_existing']} already set, "
            f"{totals['missing']} still missing a matching file in {source}."
        )

    def _find_image(self, source, slug):
        for suffix in (".svg", ".png"):
            candidate = source / f"{slug}{suffix}"
            if candidate.is_file():
                return candidate
        return None
