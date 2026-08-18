from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from core.fields import RichTextField
from core.models import Publishable, SEOFields, TimeStampedModel

RESUME_ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
RESUME_MAX_BYTES = 5 * 1024 * 1024


def validate_resume_extension(value):
    ext = Path(value.name).suffix.lower()
    if ext not in RESUME_ALLOWED_EXTENSIONS:
        raise ValidationError("Upload a PDF, DOC, or DOCX file.")


def validate_resume_size(value):
    if value.size > RESUME_MAX_BYTES:
        raise ValidationError("Resume must be 5 MB or smaller.")


class JobPosting(TimeStampedModel, SEOFields, Publishable):
    class WorkMode(models.TextChoices):
        ONSITE = "onsite", "On-site"
        HYBRID = "hybrid", "Hybrid"
        REMOTE = "remote", "Remote"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    department = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=120, blank=True)
    work_mode = models.CharField(max_length=20, choices=WorkMode.choices)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    experience_min_years = models.PositiveSmallIntegerField(null=True, blank=True)
    experience_max_years = models.PositiveSmallIntegerField(null=True, blank=True)
    summary = models.TextField()
    responsibilities = RichTextField(blank=True)
    requirements = RichTextField(blank=True)
    nice_to_have = RichTextField(blank=True)
    benefits = RichTextField(blank=True)
    is_open = models.BooleanField(default=True)
    apply_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("job_posting_detail", kwargs={"slug": self.slug})

    @property
    def experience_label(self):
        lo, hi = self.experience_min_years, self.experience_max_years
        if lo is None and hi is None:
            return ""
        if lo is not None and hi is not None:
            return f"{lo} yrs" if lo == hi else f"{lo}–{hi} yrs"
        if lo is not None:
            return f"{lo}+ yrs"
        return f"Up to {hi} yrs"


class JobApplication(TimeStampedModel):
    """Resumes are never served from a public storage path — see
    careers.views.resume_download, which hands out a signed, time-limited URL."""

    class Stage(models.TextChoices):
        NEW = "new", "New"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        REJECTED = "rejected", "Rejected"

    job = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="applications",
    )
    full_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    resume = models.FileField(
        upload_to="careers/resumes/%Y/%m/",
        validators=[validate_resume_extension, validate_resume_size],
        help_text="PDF, DOC, or DOCX. 5 MB max.",
    )
    portfolio_url = models.URLField(blank=True)
    cover_note = models.TextField(blank=True)
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.NEW, db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.job}"
