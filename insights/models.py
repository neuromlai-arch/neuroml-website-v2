from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from core.fields import RichTextField
from core.images import downscale_in_place, warm_renditions
from core.models import Publishable, SEOFields, TimeStampedModel
from people.models import TeamMember
from solutions.models import Service
from taxonomy.models import Industry, Tag

PLACEHOLDER_PREFIXES = ("[TODO]", "[Placeholder]")


def is_placeholder_text(value):
    """True for seed-fixture stand-in copy (`[TODO] ...`, `[Placeholder]
    ...`) that must never reach a published page. Compares against
    stripped, tag-free text so it works on both plain and rich-text
    fields."""
    text = strip_tags(value or "").strip()
    return any(text.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


class InsightBase(TimeStampedModel, SEOFields, Publishable):
    """Shared spine for the four insight types."""

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    excerpt = models.TextField(
        max_length=400, blank=True, help_text="Card and listing text.",
    )
    hero_image = models.ImageField(upload_to="insights/heroes/", blank=True)
    hero_alt = models.CharField(max_length=200, blank=True)
    body = RichTextField(blank=True)
    author = models.ForeignKey(
        TeamMember, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)ss",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="%(class)ss")
    featured = models.BooleanField(
        default=False, help_text="Surface this in featured slots on the homepage.",
    )

    class Meta:
        abstract = True
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class BlogPost(InsightBase):
    industries = models.ManyToManyField(Industry, blank=True, related_name="posts")
    related_services = models.ManyToManyField(Service, blank=True, related_name="posts")
    reading_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Leave blank to calculate from the body.",
    )

    class Meta(InsightBase.Meta):
        abstract = False
        ordering = ["-published_at"]

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})


class CaseStudy(InsightBase):
    client_name = models.CharField(max_length=140, blank=True)
    client_logo = models.ImageField(upload_to="case-studies/logos/", blank=True)
    client_anonymous = models.BooleanField(
        default=False, help_text="Tick if the client can't be named publicly.",
    )
    industry = models.ForeignKey(
        Industry, on_delete=models.PROTECT, null=True, blank=True,
        related_name="case_studies",
    )
    services = models.ManyToManyField(Service, blank=True, related_name="case_studies")

    challenge = RichTextField(blank=True, help_text="What the client was up against.")
    approach = RichTextField(blank=True, help_text="What you built and why.")
    outcome = RichTextField(blank=True, help_text="What changed as a result.")
    tech_stack = models.ManyToManyField(Tag, blank=True, related_name="case_studies_stack")

    class Meta(InsightBase.Meta):
        abstract = False
        ordering = ["-published_at"]
        verbose_name_plural = "case studies"

    def get_absolute_url(self):
        return reverse("case_study_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if self.hero_image:
            downscale_in_place(self.hero_image)
        super().save(*args, **kwargs)
        if self.hero_image:
            warm_renditions(self.hero_image)

    @property
    def display_client(self):
        if self.client_anonymous or not self.client_name:
            return "Confidential client"
        return self.client_name

    @property
    def has_real_challenge(self):
        return bool(self.challenge) and not is_placeholder_text(self.challenge)

    @property
    def has_real_approach(self):
        return bool(self.approach) and not is_placeholder_text(self.approach)

    @property
    def has_real_outcome(self):
        return bool(self.outcome) and not is_placeholder_text(self.outcome)

    @property
    def real_metrics(self):
        """Metrics with real content — skips [TODO]/[Placeholder] rows.
        Reads through .all() so a prefetch_related("metrics") in the view
        is reused rather than triggering a second query."""
        return [
            metric for metric in self.metrics.all()
            if not is_placeholder_text(metric.value) and not is_placeholder_text(metric.label)
        ]


class Metric(models.Model):
    """The '98% / Stock Accuracy' pairs. Entered once on the case study,
    rendered on both the case study page and the homepage card."""

    case_study = models.ForeignKey(
        CaseStudy, on_delete=models.CASCADE, related_name="metrics",
    )
    value = models.CharField(max_length=24, help_text="e.g. 98%, 3.2x, -40%")
    label = models.CharField(max_length=80, help_text="e.g. Stock accuracy")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.value} {self.label}"


class Handbook(InsightBase):
    """Long-form guides, optionally gated behind a form."""

    pdf = models.FileField(upload_to="handbooks/", blank=True)
    page_count = models.PositiveSmallIntegerField(null=True, blank=True)
    gated = models.BooleanField(
        default=False, help_text="Require an email address before download.",
    )
    cover_image = models.ImageField(upload_to="handbooks/covers/", blank=True)

    class Meta(InsightBase.Meta):
        abstract = False
        ordering = ["-published_at"]

    def get_absolute_url(self):
        return reverse("handbook_detail", kwargs={"slug": self.slug})


class Webinar(InsightBase):
    starts_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    presenters = models.ManyToManyField(
        TeamMember, blank=True, related_name="presented_webinars",
    )
    guest_presenters = models.CharField(
        max_length=300, blank=True, help_text="External speakers, comma separated.",
    )
    registration_url = models.URLField(blank=True)
    recording_url = models.URLField(
        blank=True, help_text="Set this once the recording is available.",
    )

    class Meta(InsightBase.Meta):
        abstract = False
        ordering = ["-starts_at"]

    def get_absolute_url(self):
        return reverse("webinar_detail", kwargs={"slug": self.slug})

    @property
    def is_on_demand(self):
        return bool(self.recording_url)

    @property
    def is_upcoming(self):
        return self.starts_at is not None and self.starts_at > timezone.now()
