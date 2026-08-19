"""Schedules core.tasks.heartbeat to run every few minutes via django-q2's
own Schedule model — not one of ours, so this doesn't touch our schema.
Its Success rows are how check_worker_health / /healthz/worker/ tell a live
qcluster process from a dead one. See core/worker_health.py.

The func path and interval are duplicated here as literals rather than
imported from core.worker_health — migrations should stay frozen even if
that module's constants change later."""

from django.db import migrations

SCHEDULE_NAME = "qcluster heartbeat"


def create_heartbeat_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.get_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "func": "core.tasks.heartbeat",
            "schedule_type": "I",  # Minutes
            "minutes": 5,
            "repeats": -1,
        },
    )


def remove_heartbeat_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(name=SCHEDULE_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_create_default_groups"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(create_heartbeat_schedule, remove_heartbeat_schedule),
    ]
