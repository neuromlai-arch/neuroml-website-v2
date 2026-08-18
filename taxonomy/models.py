from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Industry(models.Model):
    """Marketing & e-commerce, Procurement, Sales & service, Supply chain,
    Finance, HR. Drives the homepage use-case tabs and the Industries menu."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    blurb = models.CharField(max_length=200, blank=True)
    icon = models.ImageField(upload_to="taxonomy/industries/", blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    show_in_nav = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "industries"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("industry_detail", kwargs={"slug": self.slug})


class ServiceCluster(models.Model):
    """Top-level grouping in the Solutions menu, e.g. 'Agentic AI Foundry'."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    blurb = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
