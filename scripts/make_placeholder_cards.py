"""Generate branded placeholder case-study cards.

Standalone script — not a Django management command. It only writes PNG
files; it does not touch the database. Run it directly:

    python scripts/make_placeholder_cards.py

Output goes to ~/Downloads/case-study-images/ as <slug>.png. Existing files
are left untouched so real screenshots already dropped in that folder are
never overwritten.
"""

import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("~/Downloads/case-study-images/").expanduser()

CANVAS_SIZE = (1600, 900)
GRID_STEP = 64
GRID_COLOR = "#F4F4F4"
BG_COLOR = "#FFFFFF"
INK_COLOR = "#0B0B0B"
EYEBROW_COLOR = "#6B6B6B"
BOTTOM_BAR_HEIGHT = 96

SERIF_FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Georgia.ttf",
]
SANS_FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
]

PROJECTS = [
    ("betvaro", "BetVaro", "CUSTOM SPORTSBOOK PLATFORM"),
    ("awash-bet", "Awash Bet", "SPORTSBOOK — ETHIOPIA"),
    ("prime-stakes", "Prime Stakes", "CASINO PLATFORM — NIGERIA"),
    ("funbet", "FunBet", "MULTI-TENANT DEPLOYMENT"),
    ("malibets", "MaliBets", "CRASH-LED CASINO — KENYA"),
    ("lastabet", "Lastabet", "MULTI-MARKET SPORTSBOOK"),
    ("pollo-ai", "Pollo AI", "AI VIDEO GENERATION"),
    ("askfred", "AskFred", "AI SUPPORT ASSISTANT"),
    ("conversational-ai-platform", "Conversational AI Platform", "CUSTOMER SERVICE AUTOMATION"),
    ("industrial-vision-inspection", "Industrial Vision Inspection", "MANUFACTURING"),
    ("hr-automation-suite", "HR Automation Suite", "ENTERPRISE SAAS"),
    ("contract-intelligence-system", "Contract Intelligence", "LEGALTECH DOCUMENT AI"),
    ("ai-email-workspace", "AI Email Workspace", "PRODUCTIVITY SAAS"),
    ("clinical-ai-agents", "Clinical AI Agents", "HEALTHCARE AUTOMATION"),
    ("logistics-operations-platform", "Gemstone Logistics", "LOGISTICS PLATFORM"),
    ("contractor-marketplace", "Good Contractors List", "MARKETPLACE PLATFORM"),
    ("tax-automation-platform", "MuseTax", "FINTECH PLATFORM"),
    ("field-service-management", "Infinity Fire Prevention", "FIELD SERVICE"),
    ("ecommerce-platform", "Archies Footwear", "ECOMMERCE PLATFORM"),
    ("food-delivery-marketplace", "Food Delivery Marketplace", "FOODTECH"),
    ("same-day-delivery-platform", "Same-Day Delivery", "QUICK COMMERCE"),
    ("gardening-community-platform", "Gardenstead", "AGRITECH COMMUNITY"),
    ("shipping-management-saas", "Ship District", "SHIPPING SAAS"),
    ("telemedicine-mobile-app", "MOSC Telemedicine", "HEALTHCARE MOBILE"),
    ("dating-social-platform", "TrulyMadly", "SOCIAL NETWORKING"),
    ("news-aggregation-app", "Newsfeed", "NEWS AGGREGATION"),
    ("fashion-d2c-organic-growth", "The Merino Polo", "FASHION D2C — SEO"),
    ("home-security-local-seo", "Securelux", "HOME SECURITY — SEO"),
    ("hvac-services-local-seo", "All Type Mech", "HVAC SERVICES — SEO"),
    ("medical-practice-organic-growth", "Carpal Tunnel Pros", "HEALTHCARE — SEO"),
]


def load_font(paths, size):
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_grid(draw, size):
    width, height = size
    for x in range(0, width + 1, GRID_STEP):
        draw.line([(x, 0), (x, height)], fill=GRID_COLOR, width=1)
    for y in range(0, height + 1, GRID_STEP):
        draw.line([(0, y), (width, y)], fill=GRID_COLOR, width=1)


def wrap_title(draw, title, font, max_width):
    words = title.split()
    if not words:
        return [title]
    lines = []
    for width_guess in range(1, len(words) + 1):
        wrapped = textwrap.wrap(title, width=width_guess * 6, break_long_words=False)
        if len(wrapped) <= 2:
            lines = wrapped
    if not lines:
        lines = [title]
    if len(lines) > 2:
        lines = [" ".join(words[: len(words) // 2]), " ".join(words[len(words) // 2 :])]
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        if bbox[2] - bbox[0] > max_width:
            return textwrap.wrap(title, width=max(10, int(len(title) / 2)))[:2]
    return lines


def make_card(slug, title, eyebrow):
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_grid(draw, CANVAS_SIZE)

    margin = 96
    eyebrow_font = load_font(SANS_FONT_PATHS, 22)
    title_font = load_font(SERIF_FONT_PATHS, 84)

    eyebrow_text = " ".join(eyebrow.upper())
    eyebrow_y = margin
    draw.text((margin, eyebrow_y), eyebrow_text, font=eyebrow_font, fill=EYEBROW_COLOR)

    rule_y = eyebrow_y + 56
    draw.line([(margin, rule_y), (margin + 64, rule_y)], fill=INK_COLOR, width=3)

    max_text_width = CANVAS_SIZE[0] - margin * 2
    lines = wrap_title(draw, title, title_font, max_text_width)

    line_height = 96
    title_y = rule_y + 60
    for line in lines[:2]:
        draw.text((margin, title_y), line, font=title_font, fill=INK_COLOR)
        title_y += line_height

    bar_top = CANVAS_SIZE[1] - BOTTOM_BAR_HEIGHT
    draw.rectangle(
        [(0, bar_top), (CANVAS_SIZE[0], CANVAS_SIZE[1])], fill=INK_COLOR,
    )

    out_path = OUTPUT_DIR / f"{slug}.png"
    img.save(out_path, "PNG")
    return out_path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    for slug, title, eyebrow in PROJECTS:
        out_path = OUTPUT_DIR / f"{slug}.png"
        if out_path.exists():
            skipped += 1
            continue
        make_card(slug, title, eyebrow)
        created += 1

    print(f"Created: {created}")
    print(f"Skipped (already existed): {skipped}")


if __name__ == "__main__":
    main()
