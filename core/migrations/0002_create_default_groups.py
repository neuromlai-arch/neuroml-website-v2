"""Writer: drafts own content. Editor: edits and publishes everything.
Admin: superuser, no group needed.

Permissions for a model aren't guaranteed to exist yet at data-migration
time — Django only creates them via the post_migrate signal once the whole
`migrate` run finishes. Explicitly running create_permissions here (per the
official Django workaround) makes this migration order-independent.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

CONTENT_MODELS = ["blogpost", "casestudy", "handbook", "webinar", "usecase"]
EDITOR_MODELS = CONTENT_MODELS + [
    "service", "product", "testimonial", "metric", "homepage",
    "partner", "clientlogo", "tag", "teammember",
]


def create_default_groups(apps, schema_editor):
    for app_config in global_apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=global_apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    writer, _ = Group.objects.get_or_create(name="Writer")
    editor, _ = Group.objects.get_or_create(name="Editor")

    writer_perms = Permission.objects.filter(
        content_type__model__in=CONTENT_MODELS,
        codename__regex=r"^(add|change|view)_",
    )
    writer.permissions.set(writer_perms)

    editor_perms = Permission.objects.filter(content_type__model__in=EDITOR_MODELS)
    editor.permissions.set(editor_perms)


def remove_default_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Writer", "Editor"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("taxonomy", "0001_initial"),
        ("people", "0001_initial"),
        ("solutions", "0001_initial"),
        ("insights", "0001_initial"),
        ("marketing", "0001_initial"),
        ("pages", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_groups, remove_default_groups),
    ]
