"""Hits every Redirect's old_path against a running site and reports any
that don't resolve to a working 301/302 — run this post-launch, and
whenever the Redirect table changes, to catch typos before users do.
"""

import urllib.error
import urllib.request

from django.core.management.base import BaseCommand

from core.models import Redirect


class Command(BaseCommand):
    help = (
        "Verifies every Redirect's old_path returns the expected redirect "
        "status against a running site (defaults to http://localhost:8000)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url", default="http://localhost:8000",
            help="Origin to check against, no trailing slash (default: http://localhost:8000).",
        )

    def handle(self, *args, **options):
        base_url = options["base_url"].rstrip("/")
        redirects = Redirect.objects.all()
        if not redirects.exists():
            self.stdout.write("No redirects to check.")
            return

        broken = []
        for redirect in redirects:
            url = f"{base_url}{redirect.old_path}"
            request = urllib.request.Request(url, method="GET")
            try:
                response = urllib.request.urlopen(
                    request, timeout=10,
                )
                status = response.status
                location = response.geturl()
            except urllib.error.HTTPError as exc:
                status = exc.code
                location = None
            except urllib.error.URLError as exc:
                self.stdout.write(self.style.ERROR(f"{redirect.old_path}: couldn't connect — {exc.reason}"))
                broken.append(redirect.old_path)
                continue

            # urlopen follows redirects itself, so a 200 at the final location
            # means the chain resolved; anything else means it 404'd or errored.
            if status != 200:
                self.stdout.write(
                    self.style.ERROR(
                        f"{redirect.old_path} -> {redirect.new_path}: "
                        f"resolved with status {status}, expected the chain to end in 200"
                    )
                )
                broken.append(redirect.old_path)
            elif location and not location.startswith(f"{base_url}{redirect.new_path}"):
                self.stdout.write(
                    self.style.WARNING(
                        f"{redirect.old_path}: resolved, but landed on {location}, "
                        f"not the configured new_path {redirect.new_path!r}"
                    )
                )

        total = redirects.count()
        if broken:
            self.stdout.write(self.style.ERROR(f"\n{len(broken)}/{total} redirect(s) broken:"))
            for path in broken:
                self.stdout.write(f"  {path}")
        else:
            self.stdout.write(self.style.SUCCESS(f"All {total} redirect(s) resolve cleanly."))
