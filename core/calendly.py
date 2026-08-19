"""Builds a Calendly scheduling URL with UTM and prefill query params baked
in, using Calendly's own documented query-param mechanism (?name=&email=&
utm_source=&utm_medium=&utm_campaign=) rather than a client-side JS config
object — so the same fully-formed URL works identically whether it ends up
in an inline embed's data-url or a popup widget's initPopupWidget({url})
call, and there's exactly one place this logic lives.

Returns "" when base_url is blank, so every call site can gate on the
return value alone: `{% if calendly_url %}`.
"""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def build_calendly_url(base_url, *, utm_source="", utm_medium="", utm_campaign="", name="", email=""):
    if not base_url:
        return ""

    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query))

    if utm_source:
        params["utm_source"] = utm_source
    if utm_medium:
        params["utm_medium"] = utm_medium
    if utm_campaign:
        params["utm_campaign"] = utm_campaign
    if name:
        params["name"] = name
    if email:
        params["email"] = email

    return urlunparse(parsed._replace(query=urlencode(params)))
