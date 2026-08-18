"""The preview capability: a signed, time-limited token lets a logged-in
staff member view an unpublished object. No template exists for any content
type yet (session 2) — this renders the same stub as the real detail URLs.
"""

from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from marketing.models import Partner
from pages.models import HomePage
from solutions.models import Service

PREVIEW_SALT = "pages.preview"
PREVIEW_MAX_AGE = 60 * 60 * 24  # 24 hours


def home(request):
    home_page = HomePage.load()
    context = {
        "home": home_page,
        "seo": home_page,
        "hero_services": Service.objects.live().order_by("cluster__order", "order")[:3],
        "tech_partners": Partner.objects.filter(active=True).order_by("order"),
    }
    return render(request, "pages/home.html", context)


def make_preview_token(obj):
    content_type = ContentType.objects.get_for_model(obj)
    return signing.dumps({"ct": content_type.pk, "pk": obj.pk}, salt=PREVIEW_SALT)


def preview(request, token):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise PermissionDenied

    try:
        data = signing.loads(token, salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE)
    except signing.BadSignature as exc:
        raise Http404 from exc

    content_type = get_object_or_404(ContentType, pk=data["ct"])
    obj = get_object_or_404(content_type.model_class(), pk=data["pk"])
    return render(request, "stub_detail.html", {"object": obj, "is_preview": True})
