"""Run this from an uptime check, a cron job, or by hand after a deploy —
see DEPLOY.md. Exits non-zero (and prints to stderr) when no qcluster
process appears to be alive, since that means every queued notification
and newsletter-confirmation email is silently stuck (see core/worker_health.py)."""

from django.core.management.base import BaseCommand, CommandError

from core.worker_health import get_worker_status


class Command(BaseCommand):
    help = "Reports whether a qcluster worker process has checked in recently."

    def handle(self, *args, **options):
        status = get_worker_status()
        if not status.healthy:
            raise CommandError(f"qcluster worker unhealthy — {status.detail}")
        self.stdout.write(self.style.SUCCESS(f"qcluster worker healthy — {status.detail}"))
