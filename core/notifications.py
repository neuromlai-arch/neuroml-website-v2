"""Templated HTML email, sent off the request/response cycle via django-q2.

Every form submission on the site calls `notify_submission` (or, for the
newsletter's double opt-in, `send_confirmation_email` directly) instead of
touching django.core.mail from a view.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django_q.tasks import async_task


def _deliver(subject, template_name, context, to):
    if not to:
        return
    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)
    message = EmailMultiAlternatives(subject=subject, body=text_body, to=to)
    message.attach_alternative(html_body, "text/html")
    message.send()


def send_templated_email(*, subject, template_name, context, to):
    """Queue an HTML email for async delivery. `to` is a list of addresses."""
    async_task(_deliver, subject, template_name, context, to)


def notify_staff_of_submission(submission, *, site_settings):
    """Every ContactSubmission (any source) triggers this — one place to
    change the internal notification instead of one per form."""
    if not site_settings or not site_settings.email:
        return
    send_templated_email(
        subject=f"New {submission.get_source_display()} enquiry — {submission.first_name} {submission.last_name}".strip(),
        template_name="emails/submission_notification.html",
        context={"submission": submission},
        to=[site_settings.email],
    )


def notify_staff_of_application(application, *, site_settings):
    """A JobApplication notification — mirrors notify_staff_of_submission
    but falls back to the posting's own apply_email if site-wide contact
    email isn't set, since hiring notifications are often routed per role."""
    to = (site_settings.email if site_settings else "") or application.job.apply_email
    if not to:
        return
    send_templated_email(
        subject=f"New application — {application.job.title} — {application.full_name}",
        template_name="emails/job_application_notification.html",
        context={"application": application},
        to=[to],
    )
