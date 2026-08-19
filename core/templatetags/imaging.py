"""Responsive image rendering.

Wraps easy-thumbnails so every template gets a <picture> with a WebP source
plus a JPEG fallback srcset, at explicit width/height, without repeating the
same boilerplate. SVGs (the seed_demo placeholders) can't be resized by
Pillow, so they're rendered as a plain <img> as-is.
"""

from django import template

register = template.Library()

DEFAULT_WIDTHS = (480, 800, 1200)

_EMPTY = {
    "src": None, "srcset": "", "webp_srcset": "", "sizes": "",
    "alt": "", "css_class": "", "width": None, "height": None, "loading": "lazy",
}


def _svg_result(image, alt, css_class, sizes, loading):
    return {
        "src": image.url, "srcset": "", "webp_srcset": "", "sizes": sizes,
        "alt": alt, "css_class": css_class, "width": None, "height": None,
        "loading": loading,
    }


def _fallback_result(image, alt, css_class, sizes, loading):
    # Corrupt upload, missing file, or a format Pillow can't thumbnail —
    # never let an image helper break the page.
    return {
        "src": image.url, "srcset": "", "webp_srcset": "", "sizes": sizes,
        "alt": alt, "css_class": css_class,
        "width": getattr(image, "width", None), "height": getattr(image, "height", None),
        "loading": loading,
    }


@register.inclusion_tag("components/responsive_img.html")
def responsive_img(image, alt="", css_class="", widths=None, sizes="100vw", loading="lazy"):
    if not image:
        return dict(_EMPTY)

    name = getattr(image, "name", "") or ""
    if name.lower().endswith(".svg"):
        return _svg_result(image, alt, css_class, sizes, loading)

    if isinstance(widths, str):
        widths = [int(w) for w in widths.split(",") if w.strip()]
    widths = widths or DEFAULT_WIDTHS
    try:
        from easy_thumbnails.files import get_thumbnailer

        thumbnailer = get_thumbnailer(image)
        jpeg_parts, webp_parts = [], []
        largest_jpeg = None
        # thumbnail_extension controls both the output filename AND the
        # Pillow save format (see Thumbnailer.get_thumbnail_name /
        # generate_thumbnail) — it's an instance attribute, not a per-call
        # option, so it has to be set on the thumbnailer before each call.
        for width in widths:
            thumbnailer.thumbnail_extension = "jpg"
            jpeg_thumb = thumbnailer.get_thumbnail({"size": (width, 0), "crop": False})
            jpeg_parts.append(f"{jpeg_thumb.url} {width}w")
            largest_jpeg = jpeg_thumb

            thumbnailer.thumbnail_extension = "webp"
            webp_thumb = thumbnailer.get_thumbnail({"size": (width, 0), "crop": False})
            webp_parts.append(f"{webp_thumb.url} {width}w")

        return {
            "src": largest_jpeg.url,
            "srcset": ", ".join(jpeg_parts),
            "webp_srcset": ", ".join(webp_parts),
            "sizes": sizes,
            "alt": alt,
            "css_class": css_class,
            "width": largest_jpeg.width,
            "height": largest_jpeg.height,
            "loading": loading,
        }
    except Exception:
        return _fallback_result(image, alt, css_class, sizes, loading)
