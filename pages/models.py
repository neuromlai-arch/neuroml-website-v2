from django.db import models

from core.models import SEOFields, TimeStampedModel


class SingletonModel(models.Model):
    """One row, always pk=1. Used for pages that exist exactly once."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HomePage(SingletonModel, SEOFields, TimeStampedModel):
    hero_heading = models.TextField(
        help_text="Up to three lines. The middle line renders in the muted "
                   "two-tone colour — this is the site's signature headline treatment.",
    )
    hero_subheading = models.TextField(blank=True)
    hero_cta_label = models.CharField(max_length=40, default="Talk to an expert")
    hero_cta_url = models.CharField(max_length=300, blank=True)
    hero_image = models.ImageField(upload_to="home/", blank=True)

    expertise_heading = models.CharField(max_length=160, default="Our area of expertise")
    expertise_intro = models.TextField(blank=True)

    use_cases_heading = models.CharField(
        max_length=160, default="AI use cases for every industry",
    )
    case_studies_heading = models.CharField(
        max_length=160, default="Driving transformation across industries",
    )
    insights_heading = models.CharField(
        max_length=160, default="Insights that drive measurable impact",
    )

    show_partners = models.BooleanField(default=True)
    show_client_logos = models.BooleanField(default=True)
    show_testimonials = models.BooleanField(default=True)

    # The first three stats-band figures are always derived live (published
    # case studies, live iGaming platforms, technologies) — never stored,
    # never stale. This fourth one has no database source (years in
    # operation, team size, whatever comes up), so it's a plain editable
    # pair instead. Leave stat_4_value blank to omit that slot entirely
    # rather than show a placeholder.
    stat_4_value = models.CharField(
        max_length=24, blank=True, help_text="e.g. 6+. Leave blank to omit this slot.",
    )
    stat_4_label = models.CharField(max_length=80, blank=True, help_text="e.g. Years in operation.")

    capabilities_deck = models.FileField(
        upload_to="decks/", blank=True, help_text="The downloadable capabilities PDF.",
    )

    class Meta:
        verbose_name = "home page"

    def __str__(self):
        return "Home page"


class SiteSettings(SingletonModel, TimeStampedModel):
    """Global chrome: logo, contact details, social links, tracking IDs.

    No address field — offices are separate, see Office below.
    """

    site_name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="site/", blank=True)
    logo_dark = models.ImageField(upload_to="site/", blank=True)
    favicon = models.ImageField(upload_to="site/", blank=True)
    default_og_image = models.ImageField(upload_to="site/", blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp_number = models.CharField(max_length=40, blank=True)
    whatsapp_prefill = models.CharField(max_length=200, blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    gtm_container_id = models.CharField(max_length=30, blank=True)
    calendly_url = models.URLField(
        blank=True,
        help_text="Your Calendly scheduling link, e.g. https://calendly.com/you/30min. "
                   "Every 'Book a call' button and the demo page's scheduling embed is "
                   "hidden entirely when this is blank — nothing breaks, they just don't "
                   "render.",
    )
    # Reserved — no form does server-side reCAPTCHA verification yet, and
    # this field is hidden from SiteSettingsAdmin so an editor can't fill it
    # in believing it does something. Wire up verification before exposing
    # it again.
    recaptcha_site_key = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"


class Office(models.Model):
    city = models.CharField(max_length=80)
    country = models.CharField(max_length=80, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    image = models.ImageField(upload_to="offices/", blank=True)
    is_headquarters = models.BooleanField(default=False)
    map_url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "city"]

    def __str__(self):
        return self.city
