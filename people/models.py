from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class TeamMember(TimeStampedModel):
    """Doubles as post author and About-page content."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="team_profile",
        help_text="Link to a login account if this person writes content.",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=130, unique=True)
    role = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="team/", blank=True)
    linkedin_url = models.URLField(blank=True)
    show_on_about = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
