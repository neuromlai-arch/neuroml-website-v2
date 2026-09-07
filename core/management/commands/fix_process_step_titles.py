"""Strips the leading "NN " step number that was typed straight into
ProcessStep.title (e.g. "01 Scope honestly"). The homepage template already
renders that number itself, from `forloop.counter` next to the title
(templates/pages/home.html) — so the stored prefix was making every step
show its number twice.

Idempotent: matches only a leading two-digit-plus-space pattern, so
rerunning after the fix is a no-op.
"""

import re

from django.core.management.base import BaseCommand

from marketing.models import ProcessStep

LEADING_NUMBER = re.compile(r"^\d{1,2}\s+")


class Command(BaseCommand):
    help = "Removes the redundant leading step number from ProcessStep titles."

    def handle(self, *args, **options):
        fixed = 0
        for step in ProcessStep.objects.all():
            new_title = LEADING_NUMBER.sub("", step.title)
            if new_title != step.title:
                step.title = new_title
                step.save(update_fields=["title"])
                fixed += 1
                self.stdout.write(f"  {step.order}: {step.title!r}")
        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed} ProcessStep title(s)."))
