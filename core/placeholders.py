"""Grey SVG placeholder images for seed_demo — no stock photos, no network
calls. Django's ImageField doesn't run Pillow validation on a plain model
save() (only through a ModelForm/full_clean()), so handing it raw SVG bytes
is safe even though Pillow itself can't open SVGs.
"""

from django.core.files.base import ContentFile

FILL = "#E5E5E5"
TEXT = "#9B9B9B"


def placeholder_svg_bytes(width, height, label=""):
    font_size = max(11, min(width, height) // 8)
    safe_label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="{FILL}"/>'
        f'<text x="50%" y="50%" font-family="sans-serif" font-size="{font_size}" '
        f'fill="{TEXT}" text-anchor="middle" dominant-baseline="middle">{safe_label}</text>'
        f"</svg>"
    )
    return svg.encode("utf-8")


def set_placeholder(instance, field_name, width, height, label, slug="image"):
    """Assigns a placeholder SVG to an ImageField, only if it's currently
    empty — so re-running seed_demo against existing rows is a no-op here."""
    field = getattr(instance, field_name)
    if field:
        return
    filename = f"{slug}.svg"
    field.save(
        filename,
        ContentFile(placeholder_svg_bytes(width, height, label)),
        save=False,
    )
