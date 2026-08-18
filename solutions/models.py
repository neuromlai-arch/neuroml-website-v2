from django.db import models
from django.urls import reverse

from core.fields import RichTextField
from core.models import Publishable, SEOFields, TimeStampedModel
from taxonomy.models import Industry, ServiceCluster


class Service(TimeStampedModel, SEOFields, Publishable):
    """Replaces the ~14 hand-built service pages."""

    cluster = models.ForeignKey(
        ServiceCluster, on_delete=models.PROTECT, related_name="services",
    )
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    tagline = models.CharField(
        max_length=160, blank=True, help_text="One line, shown in the nav dropdown.",
    )
    summary = models.TextField(blank=True, help_text="Card and listing text.")
    body = RichTextField(blank=True)
    icon = models.ImageField(upload_to="services/icons/", blank=True)
    hero_image = models.ImageField(upload_to="services/heroes/", blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    show_in_nav = models.BooleanField(default=True)

    class Meta:
        ordering = ["cluster__order", "order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("service_detail", kwargs={"slug": self.slug})


class UseCase(TimeStampedModel, SEOFields, Publishable):
    """Replaces the ~24 Elementor use-case pages. One model, one template."""

    industry = models.ForeignKey(
        Industry, on_delete=models.PROTECT, related_name="use_cases",
    )
    related_service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="use_cases",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.TextField(help_text="Shown on the homepage industry tabs.")
    body = RichTextField(blank=True)
    hero_image = models.ImageField(upload_to="use-cases/", blank=True)
    cta_label = models.CharField(max_length=40, default="Explore now")
    cta_url = models.CharField(
        max_length=300, blank=True,
        help_text="Leave blank to link to this use case's own page.",
    )
    show_on_homepage = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["industry__order", "order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("use_case_detail", kwargs={"slug": self.slug})


class Product(TimeStampedModel, SEOFields, Publishable):
    """Packaged offerings, e.g. AI Agent for Logistics."""

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    tagline = models.CharField(max_length=180, blank=True)
    summary = models.TextField(blank=True)
    body = RichTextField(blank=True)
    card_image = models.ImageField(upload_to="products/cards/", blank=True)
    hero_image = models.ImageField(upload_to="products/heroes/", blank=True)
    industries = models.ManyToManyField(Industry, blank=True, related_name="products")
    order = models.PositiveSmallIntegerField(default=0)
    show_in_nav = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})


class OrganizationSolution(models.Model):
    """The Enterprise / SMB / Startup column in the Solutions menu.

    These are nav promos rather than full pages, so they stay lightweight.
    """

    class OrgType(models.TextChoices):
        ENTERPRISE = "enterprise", "Enterprise"
        SMB = "smb", "SMB"
        STARTUP = "startup", "Startup"

    org_type = models.CharField(max_length=20, choices=OrgType.choices, db_index=True)
    title = models.CharField(max_length=120)
    tagline = models.CharField(max_length=180, blank=True)
    icon = models.ImageField(upload_to="solutions/org/", blank=True)
    target_url = models.CharField(max_length=300, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["org_type", "order"]

    def __str__(self):
        return f"{self.get_org_type_display()}: {self.title}"
