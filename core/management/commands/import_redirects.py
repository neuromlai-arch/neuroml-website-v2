"""Bulk-load the Redirect model from a CSV of old_path,new_path[,permanent].

See CONTENT_MAP.md section 4: export the old site's sitemap and GSC-indexed
URLs, put them in a CSV, and run this before cutover.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from core.models import Redirect


class Command(BaseCommand):
    help = (
        "Bulk-import 301/302 redirects from a CSV with columns "
        "old_path,new_path[,permanent]. permanent defaults to true if omitted."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the redirects CSV.")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would be created/updated without writing anything.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]

        try:
            fh = open(csv_path, newline="", encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"Couldn't open {csv_path}: {exc}") from exc

        created, updated, skipped = 0, 0, 0
        with fh:
            reader = csv.DictReader(fh)
            missing = {"old_path", "new_path"} - set(reader.fieldnames or [])
            if missing:
                raise CommandError(
                    f"CSV is missing required column(s): {', '.join(sorted(missing))}"
                )

            for line_num, row in enumerate(reader, start=2):
                old_path = (row.get("old_path") or "").strip()
                new_path = (row.get("new_path") or "").strip()
                permanent_raw = (row.get("permanent") or "true").strip().lower()
                permanent = permanent_raw not in ("false", "0", "no")

                if not old_path or not new_path:
                    self.stdout.write(
                        self.style.WARNING(f"Line {line_num}: skipping — blank old_path or new_path")
                    )
                    skipped += 1
                    continue
                if not old_path.startswith("/"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Line {line_num}: skipping {old_path!r} — old_path must start with /"
                        )
                    )
                    skipped += 1
                    continue

                existing = Redirect.objects.filter(old_path=old_path).first()
                if existing:
                    changed = existing.new_path != new_path or existing.permanent != permanent
                    if changed:
                        updated += 1
                        if not dry_run:
                            existing.new_path = new_path
                            existing.permanent = permanent
                            existing.save(update_fields=["new_path", "permanent"])
                else:
                    created += 1
                    if not dry_run:
                        Redirect.objects.create(
                            old_path=old_path, new_path=new_path, permanent=permanent,
                        )

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}{created} to create, {updated} to update, {skipped} skipped."
        ))
