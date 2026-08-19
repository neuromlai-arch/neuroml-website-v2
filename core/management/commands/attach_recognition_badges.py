"""Attaches badge images to Recognition rows from a directory of files named
<slug>.png or <slug>.jpg, where <slug> is slugify(name) — same pattern as
attach_case_study_images.

Idempotent: skips any Recognition that already has a badge.

Usage:
    python manage.py attach_recognition_badges --source ~/Downloads/recognition
    python manage.py attach_recognition_badges --source <dir> --dry-run
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from marketing.models import Recognition


class Command(BaseCommand):
    help = "Attaches <slug>.png/<slug>.jpg badge images to Recognition rows from --source."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", required=True,
            help="Directory to search for <slug>.png / <slug>.jpg files, where "
                 "<slug> is slugify(name).",
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

        for recognition in Recognition.objects.order_by("name"):
            if recognition.badge:
                skipped_existing.append(recognition.name)
                continue

            image_path = self._find_image(source, slugify(recognition.name))
            if image_path is None:
                missing.append(recognition.name)
                continue

            attached.append((recognition.name, image_path.name))
            if not dry_run:
                with image_path.open("rb") as fh:
                    recognition.badge.save(image_path.name, File(fh), save=False)
                recognition.save()

        verb = "Would attach" if dry_run else "Attached"
        self.stdout.write(f"{verb} {len(attached)} badge(s):")
        for name, filename in attached:
            self.stdout.write(f"  {name} <- {filename}")

        self.stdout.write(
            f"Skipped {len(skipped_existing)} (already had a badge): "
            f"{', '.join(skipped_existing) or 'none'}"
        )
        self.stdout.write(
            f"Missing {len(missing)} (no matching file in {source}): "
            f"{', '.join(missing) or 'none'}"
        )

    def _find_image(self, source, slug):
        for suffix in (".png", ".jpg"):
            candidate = source / f"{slug}{suffix}"
            if candidate.is_file():
                return candidate
        return None
