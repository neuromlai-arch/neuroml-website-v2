"""Placeholder detail view.

Session 1 wires up every named URL that a model's get_absolute_url() needs
(so admin preview links resolve) without building real templates yet — that's
session 2's job. Every model routed through here has a unique `slug`.
"""

from django.shortcuts import get_object_or_404, render


def stub_detail(request, slug, *, model):
    manager = model.objects
    is_preview = (
        request.GET.get("preview") == "1"
        and request.user.is_authenticated
        and request.user.is_staff
    )
    if hasattr(manager, "live") and not is_preview:
        obj = get_object_or_404(manager.live(), slug=slug)
    else:
        obj = get_object_or_404(model, slug=slug)
    return render(request, "stub_detail.html", {"object": obj, "seo": obj})
