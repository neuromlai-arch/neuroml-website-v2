"""Resume downloads never expose the raw storage path — a staff member gets a
signed, time-limited URL instead (mirrors pages.views' preview-token pattern).
"""

from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from careers.models import JobApplication

RESUME_SALT = "careers.resume"
RESUME_MAX_AGE = 60 * 15  # 15 minutes


def make_resume_token(application):
    return signing.dumps({"pk": application.pk}, salt=RESUME_SALT)


def resume_download(request, token):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise PermissionDenied

    try:
        data = signing.loads(token, salt=RESUME_SALT, max_age=RESUME_MAX_AGE)
    except signing.BadSignature as exc:
        raise Http404 from exc

    application = get_object_or_404(JobApplication, pk=data["pk"])
    filename = application.resume.name.rsplit("/", 1)[-1]
    return FileResponse(
        application.resume.open("rb"), as_attachment=True, filename=filename,
    )
