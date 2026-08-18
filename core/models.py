"""Abstract mixins shared across content apps, plus the Redirect model."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SEOFields(models.Model):
    """Attach to anything that gets its own URL."""

    meta_title = models.CharField(
        max_length=70, blank=True,
        help_text="Overrides the page title in search results. Leave blank to use the title.",
    )
    meta_description = models.CharField(
        max_length=160, blank=True,
        help_text="Shown under the title in search results. Aim for 140-160 characters.",
    )
    og_image = models.ImageField(
        upload_to="seo/og/", blank=True,
        help_text="1200x630. Falls back to the hero image if blank.",
    )
    canonical_url = models.URLField(
        blank=True,
        help_text="Only set this if the content is republished from elsewhere.",
    )
    noindex = models.BooleanField(
        default=False,
        help_text="Hide this page from search engines.",
    )

    class Meta:
        abstract = True

    @property
    def seo_title(self):
        return self.meta_title or getattr(self, "title", "")


class PublishableQuerySet(models.QuerySet):
    def live(self):
        return self.filter(
            status=Publishable.Status.PUBLISHED,
            published_at__lte=timezone.now(),
        )

    def drafts(self):
        return self.filter(status=Publishable.Status.DRAFT)

    def scheduled(self):
        return self.filter(
            status=Publishable.Status.PUBLISHED,
            published_at__gt=timezone.now(),
        )


class Publishable(models.Model):
    """Draft / scheduled / published workflow.

    Scheduling is just a published_at in the future — a cron job or the
    live() filter handles it, no extra state to keep in sync.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "In review"
        PUBLISHED = "published", "Published"

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True,
    )
    published_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Set a future date to schedule. Required to go live.",
    )

    objects = PublishableQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_live(self):
        return (
            self.status == self.Status.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )

    def clean(self):
        if self.status == self.Status.PUBLISHED and not self.published_at:
            raise ValidationError(
                {"published_at": "Set a publish date before marking this published."}
            )


class Redirect(TimeStampedModel):
    """Legacy WordPress URLs -> new URLs. Populate before launch."""

    old_path = models.CharField(
        max_length=400, unique=True, db_index=True,
        help_text="Path only, with leading slash. e.g. /respond-to-rfps-faster/",
    )
    new_path = models.CharField(max_length=400)
    permanent = models.BooleanField(default=True, help_text="301 if set, 302 if not.")
    hit_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["old_path"]

    def __str__(self):
        return f"{self.old_path} -> {self.new_path}"
