"""Attaches colour logo files to Technology rows from a directory of files
named <slug>.svg or <slug>.png, where <slug> is Technology.slug — same
pattern as attach_recognition_badges and attach_icons.

Idempotent: skips any Technology that already has a logo.

Usage:
    python manage.py attach_tech_logos --source ~/Downloads/tech-logos
    python manage.py attach_tech_logos --source <dir> --dry-run
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from solutions.models import Technology


class Command(BaseCommand):
    help = "Attaches <slug>.svg/<slug>.png logo files to Technology rows from --source."

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

        attached, skipped_existing, missing = [], [], []

        for tech in Technology.objects.order_by("slug"):
            if tech.logo:
                skipped_existing.append(tech.slug)
                continue

            image_path = self._find_image(source, tech.slug)
            if image_path is None:
                missing.append(tech.slug)
                continue

            attached.append((tech.slug, image_path.name))
            if not dry_run:
                with image_path.open("rb") as fh:
                    tech.logo.save(image_path.name, File(fh), save=False)
                tech.save()

        verb = "Would attach" if dry_run else "Attached"
        self.stdout.write(f"{verb} {len(attached)} logo(s):")
        for slug, filename in attached:
            self.stdout.write(f"  {slug} <- {filename}")

        self.stdout.write(
            f"Skipped {len(skipped_existing)} (already had a logo): "
            f"{', '.join(skipped_existing) or 'none'}"
        )
        self.stdout.write(
            f"Missing {len(missing)} (no matching file in {source}): "
            f"{', '.join(missing) or 'none'}"
        )

    def _find_image(self, source, slug):
        for suffix in (".svg", ".png"):
            candidate = source / f"{slug}{suffix}"
            if candidate.is_file():
                return candidate
        return None
