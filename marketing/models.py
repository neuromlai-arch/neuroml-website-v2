from django.db import models

from core.fields import RichTextField
from core.models import TimeStampedModel
from insights.models import CaseStudy, Handbook
from pages.models import SingletonModel
from solutions.models import Service


class Testimonial(TimeStampedModel):
    class SourcePlatform(models.TextChoices):
        DIRECT = "direct", "Direct"
        UPWORK = "upwork", "Upwork"
        CLUTCH = "clutch", "Clutch"
        GOOGLE = "google", "Google"
        LINKEDIN = "linkedin", "LinkedIn"

    quote = models.TextField()
    author_name = models.CharField(max_length=120)
    author_role = models.CharField(max_length=140, blank=True)
    company = models.CharField(max_length=140, blank=True)
    avatar = models.ImageField(upload_to="testimonials/", blank=True)
    video_url = models.URLField(blank=True)
    video_thumbnail = models.ImageField(upload_to="testimonials/video/", blank=True)
    source_platform = models.CharField(
        max_length=20, choices=SourcePlatform.choices, default=SourcePlatform.DIRECT,
    )
    source_url = models.URLField(blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
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
        POPUP = "popup", "Lead popup"
        HIRE = "hire", "Hire developers"
        CHAT = "chat", "Chat widget"
        OTHER = "other", "Other"

    class ProjectStage(models.TextChoices):
        IDEA = "idea", "Just an idea"
        PROTOTYPE = "prototype", "Early prototype / MVP"
        ACTIVE = "active", "Active development"
        LIVE = "live", "Live product needing improvement"
        SCALING = "scaling", "Scaling / expansion"

    class BudgetRange(models.TextChoices):
        UNDER_10K = "under_10k", "Under $10K"
        BETWEEN_10_25K = "10_25k", "$10K – $25K"
        BETWEEN_25_50K = "25_50k", "$25K – $50K"
        BETWEEN_50_100K = "50_100k", "$50K – $100K"
        OVER_100K = "over_100k", "$100K+"
        UNSURE = "unsure", "Not sure yet"

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
    service_interest = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enquiries",
    )
    project_stage = models.CharField(
        max_length=20, choices=ProjectStage.choices, blank=True,
    )
    budget_range = models.CharField(
        max_length=20, choices=BudgetRange.choices, blank=True,
    )
    utm_source = models.CharField(max_length=120, blank=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=120, blank=True)
    handled = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Internal only.")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def is_qualified(self):
        return self.budget_range not in ("", self.BudgetRange.UNDER_10K)


class NewsletterSubscriber(TimeStampedModel):
    email = models.EmailField(unique=True)
    confirmed = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class FAQ(models.Model):
    class Placement(models.TextChoices):
        HOME = "home", "Home"
        SERVICES = "services", "Services"
        HIRE = "hire", "Hire"
        CONTACT = "contact", "Contact"
        GENERAL = "general", "General"

    question = models.CharField(max_length=250)
    answer = RichTextField()
    placement = models.CharField(
        max_length=20, choices=Placement.choices, default=Placement.GENERAL,
        db_index=True,
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, null=True, blank=True,
        related_name="faqs",
    )
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["placement", "order"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


class ComparisonTable(models.Model):
    """E.g. 'Us vs Freelancers vs Agencies'. Rows are the criteria."""

    title = models.CharField(max_length=200)
    intro = models.TextField(blank=True)
    column_1_label = models.CharField(max_length=60)
    column_2_label = models.CharField(max_length=60)
    column_3_label = models.CharField(max_length=60)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class ComparisonRow(models.Model):
    table = models.ForeignKey(
        ComparisonTable, on_delete=models.CASCADE, related_name="rows",
    )
    criterion = models.CharField(max_length=140)
    icon = models.ImageField(upload_to="comparison/", blank=True)
    column_1_value = models.CharField(max_length=120, blank=True)
    column_2_value = models.CharField(max_length=120, blank=True)
    column_3_value = models.CharField(max_length=120, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.table} — {self.criterion}"


class LeadPopup(SingletonModel, TimeStampedModel):
    """The exit-intent / delayed lead capture popup. One row, site-wide."""

    class Trigger(models.TextChoices):
        DELAY = "delay", "After a delay"
        SCROLL = "scroll", "After scrolling"
        EXIT = "exit", "On exit intent"
        DELAY_OR_EXIT = "delay_or_exit", "Delay or exit intent"

    enabled = models.BooleanField(default=True)
    heading = models.CharField(max_length=120)
    subheading = models.CharField(max_length=120, blank=True)
    footer_text = models.TextField(blank=True)
    panel_image = models.ImageField(upload_to="popup/", blank=True)
    badges = models.ManyToManyField(Recognition, blank=True)
    form_heading = models.CharField(max_length=120)
    submit_label = models.CharField(max_length=40)
    success_message = models.TextField()
    trigger = models.CharField(
        max_length=20, choices=Trigger.choices, default=Trigger.DELAY_OR_EXIT,
    )
    delay_seconds = models.PositiveSmallIntegerField(default=25)
    scroll_percent = models.PositiveSmallIntegerField(default=50)
    frequency_days = models.PositiveSmallIntegerField(
        default=7, help_text="Don't show again for this many days after a dismissal.",
    )
    hide_after_submit_days = models.PositiveSmallIntegerField(default=90)
    show_on_mobile = models.BooleanField(default=False)
    exclude_paths = models.TextField(
        blank=True, help_text="One path per line, e.g. /careers/.",
    )

    class Meta:
        verbose_name = "lead popup"

    def __str__(self):
        return "Lead popup"

    def excluded_path_list(self):
        return [line.strip() for line in self.exclude_paths.splitlines() if line.strip()]


class PopupStep(models.Model):
    """A short benefit line shown in the popup, e.g. 'Free 30-min consult'."""

    popup = models.ForeignKey(LeadPopup, on_delete=models.CASCADE, related_name="steps")
    text = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text
