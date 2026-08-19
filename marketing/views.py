"""HTMX-submitted forms. Every view here follows the same shape: honeypot +
rate limit -> validate -> save -> queue a notification email -> render a
success partial, or re-render the form partial with inline errors.
"""

from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django_ratelimit.decorators import ratelimit

from core.calendly import build_calendly_url
from core.notifications import notify_staff_of_submission, send_templated_email
from core.utm import utm_initial
from marketing.forms import ContactForm, DemoForm, NewsletterForm, PopupForm
from marketing.models import ContactSubmission, NewsletterSubscriber
from pages.models import SiteSettings


def _prefilled_calendly_url(submission, site_settings):
    """The same page-level calendly_url the context processor already
    provides, but with the just-submitted name/email baked in so a visitor
    who books right after submitting doesn't have to type them again.
    Passed to render() explicitly, which takes precedence over the context
    processor's version of the same key."""
    return build_calendly_url(
        site_settings.calendly_url,
        utm_source=submission.utm_source, utm_medium=submission.utm_medium,
        utm_campaign=submission.utm_campaign,
        name=f"{submission.first_name} {submission.last_name}".strip(),
        email=submission.email,
    )

NEWSLETTER_SALT = "marketing.newsletter"


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "")


@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def contact_submit(request):
    was_limited = getattr(request, "limited", False)
    if request.method == "POST" and not was_limited:
        form = ContactForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.source = ContactSubmission.Source.CONTACT
            submission.source_url = request.META.get("HTTP_REFERER", "")
            submission.save()
            site_settings = SiteSettings.load()
            notify_staff_of_submission(submission, site_settings=site_settings)
            return render(request, "components/_form_success.html", {
                "message": "Thanks — we'll be in touch within one business day.",
                "show_booking_button": True,
                "calendly_url": _prefilled_calendly_url(submission, site_settings),
            })
    else:
        form = ContactForm(initial=utm_initial(request))
    context = {"form": form, "rate_limited": was_limited}
    return render(request, "components/_contact_form_fields.html", context)


@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def demo_submit(request):
    was_limited = getattr(request, "limited", False)
    if request.method == "POST" and not was_limited:
        form = DemoForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.source = ContactSubmission.Source.DEMO
            submission.source_url = request.META.get("HTTP_REFERER", "")
            submission.save()
            notify_staff_of_submission(submission, site_settings=SiteSettings.load())
            return render(request, "components/_form_success.html", {
                "message": "Thanks — we'll reach out to schedule your call.",
            })
    else:
        form = DemoForm(initial=utm_initial(request))
    context = {"form": form, "rate_limited": was_limited}
    return render(request, "marketing/_demo_form_fields.html", context)


@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def popup_submit(request):
    was_limited = getattr(request, "limited", False)
    if request.method == "POST" and not was_limited:
        form = PopupForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.source = ContactSubmission.Source.POPUP
            submission.source_url = request.META.get("HTTP_REFERER", "")
            submission.save()
            site_settings = SiteSettings.load()
            notify_staff_of_submission(submission, site_settings=site_settings)
            response = render(request, "components/_form_success.html", {
                "message": "Thanks — we'll be in touch shortly.",
                "show_booking_button": True,
                "calendly_url": _prefilled_calendly_url(submission, site_settings),
            })
            response["HX-Trigger"] = "popup:submitted"
            return response
    else:
        form = PopupForm(initial=utm_initial(request))
    context = {"form": form, "rate_limited": was_limited}
    return render(request, "marketing/_popup_form_fields.html", context)


@ratelimit(key="ip", rate="3/h", method="POST", block=False)
def newsletter_signup(request):
    was_limited = getattr(request, "limited", False)
    if request.method == "POST" and not was_limited:
        form = NewsletterForm(request.POST)
        if form.is_valid():
            subscriber, _ = NewsletterSubscriber.objects.get_or_create(
                email=form.cleaned_data["email"],
            )
            token = signing.dumps({"pk": subscriber.pk}, salt=NEWSLETTER_SALT)
            confirm_url = request.build_absolute_uri(f"/newsletter/confirm/{token}/")
            send_templated_email(
                subject="Confirm your subscription",
                template_name="emails/newsletter_confirmation.html",
                context={"confirm_url": confirm_url},
                to=[subscriber.email],
            )
            return render(request, "components/_form_success.html", {
                "message": "Almost there — check your inbox to confirm.",
            })
    else:
        form = NewsletterForm()
    context = {"form": form, "rate_limited": was_limited}
    return render(request, "marketing/_newsletter_form_fields.html", context)


def newsletter_confirm(request, token):
    try:
        data = signing.loads(token, salt=NEWSLETTER_SALT, max_age=60 * 60 * 24 * 7)
    except signing.BadSignature as exc:
        raise Http404 from exc
    subscriber = get_object_or_404(NewsletterSubscriber, pk=data["pk"])
    subscriber.confirmed = True
    subscriber.save(update_fields=["confirmed"])
    return render(request, "marketing/newsletter_confirmed.html", {"subscriber": subscriber})


def demo(request):
    context = {
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Book a demo", "url": None},
        ],
        "form": DemoForm(initial=utm_initial(request)),
    }
    return render(request, "marketing/demo.html", context)
