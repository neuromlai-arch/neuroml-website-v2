"""Upload-time image processing, kept out of models.py so it can be unit
tested without pulling in the ORM.

Two jobs, both run once per upload (from CaseStudy.save()), not per
request:

1. Cap the stored original at MAX_ORIGINAL_WIDTH. Case study hero
   screenshots come in at whatever resolution the source site rendered at
   (some over 2000px wide, several megabytes) — nothing on the public site
   ever needs more than that, and every later thumbnail generation is
   cheaper against an already-reasonable source.
2. Pre-warm the WebP + JPEG renditions at the site's standard widths, so
   the first real visitor after a publish doesn't pay Pillow's resize cost
   — see core/templatetags/imaging.py for the matching render-time widths.
"""

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

MAX_ORIGINAL_WIDTH = 1600
RENDITION_WIDTHS = (480, 800, 1200, 1600)


def downscale_in_place(image_field_file, max_width=MAX_ORIGINAL_WIDTH):
    """If the stored image is wider than max_width, replace it with a
    same-format resize at max_width, preserving aspect ratio. No-op for
    anything Pillow can't open (e.g. the SVG placeholders from seed_demo)
    or images already within the cap."""
    name = getattr(image_field_file, "name", "") or ""
    if not name or name.lower().endswith(".svg"):
        return

    try:
        image_field_file.open()
        image_field_file.seek(0)
        img = Image.open(image_field_file)
        img.load()
    except Exception:
        return

    if img.width <= max_width:
        image_field_file.close()
        return

    ratio = max_width / img.width
    new_size = (max_width, max(1, round(img.height * ratio)))
    if img.mode in ("P", "CMYK"):
        img = img.convert("RGB")
    resized = img.resize(new_size, Image.LANCZOS)

    fmt = img.format or "PNG"
    save_kwargs = {"optimize": True}
    if fmt == "JPEG":
        save_kwargs["quality"] = 85

    buffer = BytesIO()
    resized.save(buffer, format=fmt, **save_kwargs)
    buffer.seek(0)

    image_field_file.close()
    filename = name.rsplit("/", 1)[-1]
    image_field_file.save(filename, ContentFile(buffer.read()), save=False)


def warm_renditions(image_field_file, widths=RENDITION_WIDTHS):
    """Eagerly generates the WebP + JPEG thumbnails responsive_img would
    otherwise generate lazily on first render. Best-effort: a thumbnailing
    failure here shouldn't block saving the case study — responsive_img's
    own try/except falls back to the original image if a rendition is
    genuinely missing."""
    name = getattr(image_field_file, "name", "") or ""
    if not name or name.lower().endswith(".svg"):
        return

    try:
        from easy_thumbnails.files import get_thumbnailer

        thumbnailer = get_thumbnailer(image_field_file)
        for width in widths:
            for extension in ("jpg", "webp"):
                thumbnailer.thumbnail_extension = extension
                thumbnailer.get_thumbnail({"size": (width, 0), "crop": False})
    except Exception:
        return
