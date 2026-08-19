"""Functions queued via django-q2. Currently just the worker heartbeat —
see core/worker_health.py and core/migrations/0003_create_qcluster_heartbeat_schedule.py.
Actual notification emails are queued from core/notifications.py instead of here."""

from django.utils import timezone


def heartbeat():
    """Scheduled to run every few minutes for as long as a qcluster process
    is up and pulling from the ORM broker. Its own return value is never
    read — what matters is that a Success row lands in django_q's table, so
    core.worker_health can tell a live worker from a dead one."""
    return timezone.now().isoformat()
