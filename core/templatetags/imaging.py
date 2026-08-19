"""Responsive image rendering.

Wraps easy-thumbnails so every template gets a srcset + explicit width/height
without repeating the same three-size boilerplate. SVGs (the seed_demo
placeholders) can't be resized by Pillow, so they're rendered as-is.
"""

from django import template

register = template.Library()

DEFAULT_WIDTHS = (480, 800, 1200)


@register.inclusion_tag("components/responsive_img.html")
def responsive_img(image, alt="", css_class="", widths=None, sizes="100vw", loading="lazy"):
    if not image:
        return {"src": None}

    name = getattr(image, "name", "") or ""
    if name.lower().endswith(".svg"):
        return {
            "src": image.url,
            "srcset": "",
            "sizes": sizes,
            "alt": alt,
            "css_class": css_class,
            "width": None,
            "height": None,
            "loading": loading,
        }

    if isinstance(widths, str):
        widths = [int(w) for w in widths.split(",") if w.strip()]
    widths = widths or DEFAULT_WIDTHS
    try:
        from easy_thumbnails.files import get_thumbnailer

        thumbnailer = get_thumbnailer(image)
        srcset_parts = []
        largest = None
        for width in widths:
            thumb = thumbnailer.get_thumbnail({"size": (width, 0), "crop": False})
            srcset_parts.append(f"{thumb.url} {width}w")
            largest = thumb
        return {
            "src": largest.url,
            "srcset": ", ".join(srcset_parts),
            "sizes": sizes,
            "alt": alt,
            "css_class": css_class,
            "width": largest.width,
            "height": largest.height,
            "loading": loading,
        }
    except Exception:
        # Corrupt upload, missing file, or a format Pillow can't thumbnail —
        # never let an image helper break the page.
        return {
            "src": image.url,
            "srcset": "",
            "sizes": sizes,
            "alt": alt,
            "css_class": css_class,
            "width": getattr(image, "width", None),
            "height": getattr(image, "height", None),
            "loading": loading,
        }
