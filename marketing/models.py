from django.db import models

from core.models import TimeStampedModel
from insights.models import CaseStudy, Handbook


class Testimonial(TimeStampedModel):
    quote = models.TextField()
    author_name = models.CharField(max_length=120)
    author_role = models.CharField(max_length=140, blank=True)
    company = models.CharField(max_length=140, blank=True)
    avatar = models.ImageField(upload_to="testimonials/", blank=True)
    case_study = models.ForeignKey(
        CaseStudy, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testimonials",
        help_text="Link this to a case study to show it on that page too.",
    )
    featured = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.author_name} — {self.company or 'n/a'}"


class Partner(models.Model):
    """Technology partners: AWS, Databricks, OpenAI, etc."""

    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="partners/")
    url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ClientLogo(models.Model):
    """The logo marquee. Separate from Partner — different meaning, different row."""

    name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="clients/")
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Recognition(models.Model):
    """Awards and badges in the footer."""

    name = models.CharField(max_length=140)
    badge = models.ImageField(upload_to="recognition/")
    url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ProcessStep(models.Model):
    """Discovery -> Pilot -> Rollout -> Support."""

    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="process/", blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class EngagementModel(models.Model):
    """Fixed price, T&M, dedicated team, hybrid."""

    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="engagement/", blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class ContactSubmission(TimeStampedModel):
    """Every form on the site lands here, tagged by source."""

    class Source(models.TextChoices):
        CONTACT = "contact", "Contact page"
        DEMO = "demo", "Book a demo"
        HANDBOOK = "handbook", "Handbook download"
        FOOTER = "footer", "Footer CTA"
        OTHER = "other", "Other"

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=140, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.CONTACT, db_index=True,
    )
    source_url = models.CharField(max_length=400, blank=True)
    handbook = models.ForeignKey(
        Handbook, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="submissions",
    )
    handled = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Internal only.")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"


class NewsletterSubscriber(TimeStampedModel):
    email = models.EmailField(unique=True)
    confirmed = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
