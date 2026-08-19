"""Shared logic for `check_worker_health` and the /healthz/worker/ view.

Neither the ORM broker nor django-q2's cache-based Stat() are reliable
cross-process signals here: Stat() needs a shared cache backend (this
project uses per-process locmem in dev, and nothing guarantees otherwise in
prod), and the broker only tells you tasks are *queued*, not that anything
is picking them up. Instead, core.tasks.heartbeat is scheduled (see the
0003 migration) to run every HEARTBEAT_INTERVAL_MINUTES for as long as a
qcluster process is alive — a stale or missing Success row for it means no
worker is running, which also means every queued notification/newsletter
email is silently stuck.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

HEARTBEAT_FUNC = "core.tasks.heartbeat"
HEARTBEAT_INTERVAL_MINUTES = 5
# Generous multiple of the interval so a slow scheduler tick or a worker
# mid-restart doesn't flap the check red.
STALE_AFTER = timedelta(minutes=HEARTBEAT_INTERVAL_MINUTES * 3)


@dataclass
class WorkerStatus:
    healthy: bool
    last_seen: "timezone.datetime | None"

    @property
    def detail(self):
        if self.last_seen is None:
            return "no qcluster worker has ever checked in"
        age = timezone.now() - self.last_seen
        return f"last checked in {age.total_seconds():.0f}s ago (at {self.last_seen.isoformat()})"


def get_worker_status():
    from django_q.models import Success

    last = (
        Success.objects.filter(func=HEARTBEAT_FUNC)
        .order_by("-stopped")
        .values_list("stopped", flat=True)
        .first()
    )
    if last is None:
        return WorkerStatus(healthy=False, last_seen=None)
    return WorkerStatus(healthy=timezone.now() - last <= STALE_AFTER, last_seen=last)
