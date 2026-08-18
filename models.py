"""
Content models for the site rebuild.

Organised in sections so it's easy to split into apps later:
    core/        -> mixins, Redirect
    taxonomy/    -> Industry, ServiceCluster, Tag
    people/      -> TeamMember
    solutions/   -> Service, UseCase, Product, OrganizationSolution
    insights/    -> BlogPost, CaseStudy, Handbook, Webinar, Metric
    marketing/   -> Testimonial, Partner, ClientLogo, Recognition,
                    ProcessStep, EngagementModel, ContactSubmission,
                    NewsletterSubscriber
    pages/       -> HomePage (singleton)

Rich text: swap the RichTextField alias below for CKEditor5Field or a
TipTap JSONField and every body field changes at once.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# Swap this one line to change the editor everywhere.
RichTextField = models.TextField


# ---------------------------------------------------------------------------
# core: abstract mixins
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# taxonomy
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# people
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# solutions
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------

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

    @property
    def display_client(self):
        if self.client_anonymous or not self.client_name:
            return "Confidential client"
        return self.client_name


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
    presenters = models.ManyToManyField(TeamMember, blank=True, related_name="webinars")
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


# ---------------------------------------------------------------------------
# marketing
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

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
    hero_heading = models.CharField(max_length=200)
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
