"""Attaches hero images to CaseStudy rows from a directory of files named
<slug>.png or <slug>.jpg, so real screenshots dropped into a working folder
land in MEDIA_ROOT via ImageField.save() instead of being copied in by hand.

Idempotent: skips any case study that already has a hero_image. Also skips
anonymised case studies by design — an anonymised entry shows only its
generic descriptor, never a client identifier, and that extends to not
attaching an image for it even if a placeholder file happens to share its
slug.

Never reads from a subdirectory named _verify_before_use — those are
screenshots of third-party corporate homepages, excluded on purpose.

Usage:
    python manage.py attach_case_study_images --source ~/Downloads/case-study-images
    python manage.py attach_case_study_images --source <dir> --dry-run
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from insights.models import CaseStudy

EXCLUDED_DIR_NAME = "_verify_before_use"


class Command(BaseCommand):
    help = "Attaches <slug>.png/<slug>.jpg hero images to CaseStudy rows from --source."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", required=True,
            help="Directory to search for <slug>.png / <slug>.jpg files.",
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

        attached, skipped_existing, skipped_anonymous, missing = [], [], [], []

        for case_study in CaseStudy.objects.order_by("slug"):
            if case_study.hero_image:
                skipped_existing.append(case_study.slug)
                continue

            if case_study.client_anonymous:
                skipped_anonymous.append(case_study.slug)
                continue

            image_path = self._find_image(source, case_study.slug)
            if image_path is None:
                missing.append(case_study.slug)
                continue

            attached.append((case_study.slug, image_path.name))
            if not dry_run:
                with image_path.open("rb") as fh:
                    case_study.hero_image.save(image_path.name, File(fh), save=False)
                if not case_study.hero_alt:
                    case_study.hero_alt = case_study.title
                case_study.save()

        verb = "Would attach" if dry_run else "Attached"
        self.stdout.write(f"{verb} {len(attached)} image(s):")
        for slug, filename in attached:
            self.stdout.write(f"  {slug} <- {filename}")

        self.stdout.write(
            f"Skipped {len(skipped_existing)} (already had a hero_image): "
            f"{', '.join(skipped_existing) or 'none'}"
        )
        self.stdout.write(
            f"Skipped {len(skipped_anonymous)} (anonymised, no image by design): "
            f"{', '.join(skipped_anonymous) or 'none'}"
        )
        self.stdout.write(
            f"Missing {len(missing)} (no matching file in {source}): "
            f"{', '.join(missing) or 'none'}"
        )

    def _find_image(self, source, slug):
        for suffix in (".png", ".jpg"):
            candidate = source / f"{slug}{suffix}"
            if candidate.is_file() and candidate.parent.name != EXCLUDED_DIR_NAME:
                return candidate
        return None
