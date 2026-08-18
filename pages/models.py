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

    capabilities_deck = models.FileField(
        upload_to="decks/", blank=True, help_text="The downloadable capabilities PDF.",
    )

    class Meta:
        verbose_name = "home page"

    def __str__(self):
        return "Home page"
