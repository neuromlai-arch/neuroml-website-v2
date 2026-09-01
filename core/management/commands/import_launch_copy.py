"""Bulk-load real copy over the [TODO] placeholders left by seed_demo.

Reads the CSV produced alongside content/launch_copy_template.csv (same
columns: model,slug,field,notes,current_placeholder,new_copy) and writes
new_copy into the named field on the record matched by model+slug. Rows
with an empty new_copy are skipped, so a partially-filled sheet is safe to
import repeatedly as more copy lands.

`body` fields are RichTextField (CKEditor 5 HTML) — plain text input is
wrapped into <p> tags, one per blank-line-separated paragraph. Any other
field is written as-is.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from solutions.models import Service, Technology, UseCase
from taxonomy.models import Industry, ServiceCluster

MODELS = {
    "servicecluster": ServiceCluster,
    "industry": Industry,
    "service": Service,
    "usecase": UseCase,
    "technology": Technology,
}

RICHTEXT_FIELDS = {"body"}


def as_html_paragraphs(text):
    paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in paras)


class Command(BaseCommand):
    help = "Import real copy from a launch_copy CSV, overwriting [TODO] placeholder fields."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, csv_path, dry_run, **options):
        updated = 0
        skipped_empty = 0
        errors = []

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for i, row in enumerate(rows, start=2):  # header is line 1
            new_copy = (row.get("new_copy") or "").strip()
            if not new_copy:
                skipped_empty += 1
                continue

            model_key = row["model"].strip()
            model = MODELS.get(model_key)
            if model is None:
                errors.append(f"line {i}: unknown model '{model_key}'")
                continue

            try:
                obj = model.objects.get(slug=row["slug"].strip())
            except model.DoesNotExist:
                errors.append(f"line {i}: no {model_key} with slug '{row['slug']}'")
                continue

            field = row["field"].strip()
            if not hasattr(obj, field):
                errors.append(f"line {i}: {model_key} has no field '{field}'")
                continue

            value = as_html_paragraphs(new_copy) if field in RICHTEXT_FIELDS else new_copy
            setattr(obj, field, value)
            if not dry_run:
                obj.save(update_fields=[field])
            updated += 1

        if errors:
            for e in errors:
                self.stderr.write(self.style.WARNING(e))

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {updated} field(s); {skipped_empty} row(s) left blank (skipped); "
            f"{len(errors)} error(s)."
        ))
        if errors and not dry_run:
            raise CommandError(f"{len(errors)} row(s) failed — see warnings above.")
