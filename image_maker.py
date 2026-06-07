import os
import re
import textwrap
from datetime import datetime
import random
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from config import COLORS as C, LOGO_PATH, PAGE_HANDLE, PAGE_NAME, PEXELS_KEY
from news_utils import build_visual_queries, display_source, slide_headline, slide_summary, story_label

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output_posts"
OUTPUT_DIR.mkdir(exist_ok=True)

if Path(LOGO_PATH).is_absolute():
    LOGO_FILE = Path(LOGO_PATH)
else:
    LOGO_FILE = BASE_DIR / LOGO_PATH

REQUEST_TIMEOUT = 10
PHOTO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

PEXELS_QUERIES = {
    "INDIA": ["india city", "new delhi skyline", "india parliament"],
    "WORLD": ["world city", "global news", "international"],
    "BUSINESS": ["stock market", "finance office", "economy"],
    "TECH": ["technology digital", "computer ai", "smartphone"],
    "SPORTS": ["cricket india", "football stadium", "sports action"],
    "ENTERTAINMENT": ["bollywood cinema", "movie theater", "concert stage"],
    "SCIENCE": ["space rocket", "laboratory science", "nasa"],
    "POLITICS": ["parliament building", "government politics"],
    "BREAKING": ["breaking news", "newspaper press"],
    "FINANCE": ["stock market chart", "cryptocurrency trading", "money investment"],
    "STARTUPS": ["startup team", "startup office", "entrepreneur laptop"],
    "CRIME": ["police lights", "gavel law", "crime scene tape"],
    "EDUCATION": ["university students", "college campus", "library studying"],
    "CAREERS": ["office workplace", "corporate hiring", "employees teamwork"],
}
def _fit_image(image, width, height, fit=True):
    img = image.convert("RGB")
    
    if fit:
        # Create a blurred background that fills the entire 1080x1920 canvas
        bg = ImageOps.fit(img, (width, height), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
        bg = ImageEnhance.Brightness(bg).enhance(0.5) # Darken bg slightly
        
        # Resize original image to fit perfectly inside the width without cropping
        # and paste it vertically centered on the blurred background
        fg = ImageOps.contain(img, (width, height), Image.LANCZOS)
        
        # Calculate coordinates to paste fg centered on bg
        x = (width - fg.width) // 2
        y = (height - fg.height) // 2
        bg.paste(fg, (x, y))
        
        return bg
        
    return ImageOps.contain(img, (width, height), Image.LANCZOS)


def _download_image(url, width, height, fit=True):
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers=PHOTO_HEADERS,
        stream=True,
    )
    response.raise_for_status()
    content = response.content
    if len(content) < 5000:
        raise ValueError("image payload too small")
    return _fit_image(Image.open(BytesIO(content)), width, height, fit=fit)


def get_photo(article, width, height, seed_offset=0, fit=True):
    seed = abs(hash(article["title"])) % 900 + 1 + seed_offset

    if article.get("image"):
        try:
            image = _download_image(article["image"], width, height, fit=fit)
            print("    Real news photo used")
            return image
        except Exception:
            pass

    if PEXELS_KEY and "YOUR_" not in PEXELS_KEY:
        for current_query in build_visual_queries(article):
            try:
                response = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": PEXELS_KEY, **PHOTO_HEADERS},
                    params={
                        "query": current_query,
                        "per_page": 5,
                        "orientation": "portrait", # Changed to portrait to perfectly fit 1080x1350 stories
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                photos = response.json().get("photos", [])
                if photos:
                    best_photo = max(
                        photos[:4],
                        key=lambda item: item.get("width", 0) * item.get("height", 0),
                    )
                    image = _download_image(best_photo["src"]["large2x"], width, height, fit=fit)
                    print(f"    Pexels photo: '{current_query}'")
                    return image
            except Exception:
                pass

    try:
        image = _download_image(f"https://picsum.photos/seed/{seed}/{width}/{height}", width, height, fit=fit)
        print("    Picsum photo")
        return image
    except Exception:
        pass

    print("    Gradient background")
    return _gradient(width, height)


def _gradient(width, height):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    color_1, color_2 = C["dark_red"], C["deep"]
    for y_coord in range(height):
        ratio = y_coord / height
        draw.line(
            [(0, y_coord), (width, y_coord)],
            fill=(
                int(color_1[0] + (color_2[0] - color_1[0]) * ratio),
                int(color_1[1] + (color_2[1] - color_1[1]) * ratio),
                int(color_1[2] + (color_2[2] - color_1[2]) * ratio),
            ),
        )
    return image


def paste_logo(canvas, x_coord, y_coord, size=90):
    try:
        logo = Image.open(LOGO_FILE).convert("RGBA").resize((size, size), Image.LANCZOS)
        layer = canvas.convert("RGBA")
        layer.paste(logo, (x_coord, y_coord), logo)
        canvas.paste(layer.convert("RGB"), (0, 0))
    except Exception:
        pass


def F(size, bold=True, impact=False):
    if impact:
        font_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
        ]
    elif bold:
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/verdanab.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/verdana.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]

    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def shadow(draw, xy, text, font, fill, shadow_fill=(0, 0, 0), delta=3):
    draw.text((xy[0] + delta, xy[1] + delta), text, font=font, fill=shadow_fill)
    draw.text(xy, text, font=font, fill=fill)


def center_x(draw, y_coord, text, font, fill, width, shadow_fill=None, delta=2):
    bounds = draw.textbbox((0, 0), text, font=font)
    x_coord = (width - (bounds[2] - bounds[0])) // 2
    if shadow_fill:
        draw.text((x_coord + delta, y_coord + delta), text, font=font, fill=shadow_fill)
    draw.text((x_coord, y_coord), text, font=font, fill=fill)
    return bounds[3] - bounds[1]


def shorten(text, limit):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def darken_background(image, factor=0.34):
    return ImageEnhance.Brightness(image).enhance(factor)


def add_bottom_fade(canvas, start_y):
    width, height = canvas.size
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y_coord in range(start_y, height):
        alpha = min(245, int((y_coord - start_y) * 0.42))
        draw.line([(0, y_coord), (width, y_coord)], fill=(8, 3, 5, alpha))
    output = canvas.convert("RGBA")
    output.alpha_composite(layer)
    return output.convert("RGB")


def add_overlay_box(canvas, box, fill):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=40, fill=fill)
    output = canvas.convert("RGBA")
    output.alpha_composite(layer)
    return output.convert("RGB")


def draw_brand_header(canvas, width, label="LIVE NEWS", transparent=False):
    draw = ImageDraw.Draw(canvas)
    if not transparent:
        draw.rectangle([0, 0, width, 150], fill=C["maroon"])
    paste_logo(canvas, 28, 28, size=94)
    draw = ImageDraw.Draw(canvas)
    draw.text((138, 24), "NEWS", font=F(48, True), fill=C["white"])
    draw.text((138, 76), "FLASH5", font=F(48, True), fill=C["red"])
    if not transparent:
        draw.rectangle([0, 150, width, 158], fill=C["red"])


def _summary_lines(summary, width=34, max_lines=3, max_chars=170):
    return textwrap.wrap(shorten(summary, max_chars), width=width)[:max_lines]


def slide1_main(article, path):
    width, height = 1080, 1350
    print("    Slide 1 - MAIN...")
    headline_text = article.get("ai_title") or slide_headline(article, max_chars=95)
    summary_text = article.get("ai_summary") or slide_summary(article, max_chars=150)
    canvas = Image.new("RGB", (width, height), C["white"])
    draw_brand_header(canvas, width, label="BREAKING")
    draw = ImageDraw.Draw(canvas)

    badge_text = "BREAKING" if article.get("breaking") else article["category"].upper()
    badge_font = F(102, True)
    badge_box = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_x = (width - (badge_box[2] - badge_box[0])) // 2
    draw.text((badge_x + 3, 174), badge_text, font=badge_font, fill=C["maroon"])
    draw.text((badge_x, 170), badge_text, font=badge_font, fill=C["red"])
    draw.line([(badge_x, 278), (badge_x + badge_box[2] - badge_box[0], 278)], fill=C["red"], width=5)

    headline_font = F(62, True)
    headline_y = 298
    for line in textwrap.wrap(headline_text.upper(), width=20)[:4]:
        line_box = draw.textbbox((0, 0), line, font=headline_font)
        line_x = (width - (line_box[2] - line_box[0])) // 2
        shadow(draw, (line_x, headline_y), line, headline_font, C["dark_bg"], (190, 185, 185), 2)
        headline_y += 76

    photo = get_photo(article, width, 500)
    canvas.paste(photo, (0, 510))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 990, width, 1008], fill=C["red"])
    draw.rectangle([0, 1008, width, 1230], fill=C["dark_bg"])

    summary_y = 1020
    summary_font = F(44, True)
    for line in textwrap.wrap(summary_text.upper(), width=25)[:4]:
        line_box = draw.textbbox((0, 0), line, font=summary_font)
        line_x = (width - (line_box[2] - line_box[0])) // 2
        draw.text((line_x, summary_y), line, font=summary_font, fill=C["white"])
        summary_y += 56

    draw.rectangle([0, 1230, width, 1308], fill=C["maroon"])
    draw.text((36, 1252), "Follow for breaking news 24/7", font=F(30, False), fill=C["offwhite"])
    paste_logo(canvas, width - 326, 1238, size=60)
    draw = ImageDraw.Draw(canvas)
    draw.text((width - 254, 1258), PAGE_HANDLE, font=F(30, False), fill=C["red"])

    draw.rectangle([0, 1308, width, 1350], fill=C["light_grey"])
    source_line = f"Source: {display_source(article['source'])} | Verified | {datetime.now().strftime('%d %b %Y')}"
    draw.text((36, 1322), source_line, font=F(28, False), fill=(110, 80, 80))
    center_x(draw, 1290, "Swipe for more context ->", F(26, False), (160, 130, 130), width)

    canvas.save(path, "JPEG", quality=96)
    return path


def slide2_facts(article, path):
    width, height = 1080, 1350
    print("    Slide 2 - FACTS...")
    headline_text = slide_headline(article, max_chars=70)
    summary_text = slide_summary(article, max_chars=180)
    canvas = Image.new("RGB", (width, height), C["dark_bg"])
    draw_brand_header(canvas, width, label="KEY FACTS")
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([0, 168, width, 232], fill=C["dark_red"])
    center_x(draw, 180, "KEY FACTS", F(46, True), C["white"], width)

    title_y = 250
    for line in textwrap.wrap(headline_text.upper(), width=26)[:2]:
        line_box = draw.textbbox((0, 0), line, font=F(48, True))
        line_x = (width - (line_box[2] - line_box[0])) // 2
        draw.text((line_x, title_y), line, font=F(48, True), fill=C["red"])
        title_y += 62
    draw.line([80, title_y + 6, width - 80, title_y + 6], fill=C["dark_red"], width=2)

    sentences = [item.strip() for item in re.split(r"[.!?]", summary_text) if len(item.strip()) > 20]
    if len(sentences) < 2:
        words = summary_text.split()
        chunk_size = max(len(words) // 4, 1)
        sentences = [" ".join(words[index:index + chunk_size]) for index in range(0, len(words), chunk_size)]

    facts = sentences[:4]
    if len(facts) < 4:
        facts += [f"Follow {PAGE_HANDLE} for live updates"] * (4 - len(facts))

    facts_y = title_y + 36
    for index, fact in enumerate(facts, start=1):
        circle_x, circle_y = 52, facts_y
        draw.ellipse([circle_x, circle_y, circle_x + 66, circle_y + 66], fill=C["red"])
        number_font = F(40, True)
        number_box = draw.textbbox((0, 0), str(index), font=number_font)
        draw.text(
            (
                circle_x + (66 - (number_box[2] - number_box[0])) // 2,
                circle_y + (66 - (number_box[3] - number_box[1])) // 2,
            ),
            str(index),
            font=number_font,
            fill=C["white"],
        )

        line_y = facts_y + 6
        wrapped = textwrap.wrap(shorten(fact, 110), width=28)[:2]
        for row, line in enumerate(wrapped):
            font = F(42, True) if row == 0 else F(36, False)
            draw.text((136, line_y + row * 44), line, font=font, fill=C["offwhite"])

        facts_y += 136
        draw.line([52, facts_y - 10, width - 52, facts_y - 10], fill=(40, 15, 20), width=1)

    draw.rectangle([0, height - 92, width, height], fill=C["maroon"])
    draw.text((36, height - 74), "Swipe for visual story ->", font=F(30, False), fill=C["offwhite"])
    draw.text((width - 260, height - 74), PAGE_HANDLE, font=F(30, False), fill=C["red"])

    canvas.save(path, "JPEG", quality=96)
    return path


def slide3_visual(article, path):
    width, height = 1080, 1350
    print("    Slide 3 - VISUAL...")
    headline_text = slide_headline(article, max_chars=75)
    summary_text = slide_summary(article, max_chars=150)
    canvas = darken_background(get_photo(article, width, height, seed_offset=300), factor=0.32)
    canvas = add_bottom_fade(canvas, 450)
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([0, 0, width, 120], fill=(90, 5, 15))
    paste_logo(canvas, 24, 14, size=92)
    draw = ImageDraw.Draw(canvas)
    draw.text((128, 20), "NEWS", font=F(46, True), fill=C["white"])
    draw.text((128, 68), "FLASH", font=F(46, True), fill=C["red"])

    category = article["category"]
    category_box = draw.textbbox((0, 0), category, font=F(34, True))
    category_width = category_box[2] - category_box[0] + 32
    draw.rectangle([width - category_width - 20, 28, width - 20, 92], fill=C["red"])
    draw.text((width - category_width - 4, 38), category, font=F(34, True), fill=C["white"])

    quote = shorten(" ".join(headline_text.split()[:10]), 70)
    quote_y = 650
    draw.rectangle([40, quote_y - 16, width - 40, quote_y], fill=C["red"])
    quote_font = F(70, True)
    for line in textwrap.wrap(f'"{quote}"', width=22)[:3]:
        line_box = draw.textbbox((0, 0), line, font=quote_font)
        line_x = (width - (line_box[2] - line_box[0])) // 2
        shadow(draw, (line_x, quote_y), line, quote_font, C["white"], (0, 0, 0), 4)
        quote_y += 86
    draw.rectangle([40, quote_y + 6, width - 40, quote_y + 20], fill=C["red"])

    source_text = f"Source: {display_source(article['source'])}"
    source_box = draw.textbbox((0, 0), source_text, font=F(34, False))
    source_x = (width - (source_box[2] - source_box[0])) // 2
    draw.text((source_x, quote_y + 36), source_text, font=F(34, False), fill=C["offwhite"])

    summary_y = quote_y + 100
    for line in _summary_lines(summary_text, width=36, max_lines=3, max_chars=150):
        draw.text((50, summary_y), line, font=F(36, False), fill=(210, 185, 185))
        summary_y += 46

    draw.rectangle([0, height - 90, width, height], fill=(14, 6, 9))
    draw.text((36, height - 70), "Follow " + PAGE_HANDLE, font=F(32, True), fill=C["red"])
    draw.text((width - 320, height - 70), "Tap save for updates", font=F(28, False), fill=(160, 130, 130))

    canvas.save(path, "JPEG", quality=96)
    return path


def slide4_cta(article, path):
    width, height = 1080, 1350
    print("    Slide 4 - CTA...")
    canvas = _gradient(width, height)
    draw = ImageDraw.Draw(canvas)

    grid_color = (100, 30, 40)
    for x_coord in range(0, width, 60):
        draw.line([(x_coord, 0), (x_coord, height)], fill=grid_color, width=1)
    for y_coord in range(0, height, 60):
        draw.line([(0, y_coord), (width, y_coord)], fill=grid_color, width=1)

    paste_logo(canvas, width // 2 - 180, 160, size=360)
    draw = ImageDraw.Draw(canvas)
    center_x(draw, 550, PAGE_NAME.upper(), F(78, True), C["white"], width, shadow_fill=C["dark_bg"])
    center_x(draw, 640, PAGE_HANDLE, F(54, True), C["red"], width)
    draw.rectangle([160, 715, width - 160, 723], fill=C["red"])

    cta_y = 745
    for text, color in [
        ("Follow", C["white"]),
        (PAGE_HANDLE, C["red"]),
        ("for hourly India + world news", C["offwhite"]),
        ("and fast breaking updates", C["offwhite"]),
    ]:
        center_x(draw, cta_y, text, F(50, True), color, width)
        cta_y += 70

    draw.rectangle([160, 1030, width - 160, 1038], fill=C["dark_red"])
    center_x(draw, 1056, "Turn on notifications", F(44, True), C["white"], width)
    center_x(draw, 1114, "Never miss a breaking story", F(34, False), (180, 150, 150), width)
    center_x(draw, 1200, "Instagram | Telegram | WhatsApp | YouTube", F(28, False), (160, 130, 130), width)
    center_x(draw, 1244, "news.flash5 on all platforms", F(28, False), C["red"], width)

    canvas.save(path, "JPEG", quality=96)
    return path


def digest_cover_slide(articles, path):
    width, height = 1080, 1350
    print("    Slide 1 - DIGEST COVER...")
    
    # Fetch a stunning background image based on the top story
    top_article = articles[0] if articles else {"category": "WORLD"}
    base_img = get_photo(top_article, width, height, seed_offset=800, fit=True)
    
    # Apply a smooth, heavy cinematic vignette/gradient so text is 100% readable everywhere
    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    for y in range(height):
        # Create a parabolic alpha curve: dark at top, lighter in middle, very dark at bottom.
        ny = (y / (height / 2)) - 1  # -1 at top, 0 at middle, 1 at bottom
        
        # Base darkness 150. Edges push towards 255.
        base_alpha = 150
        # Make the bottom edge darker than the top edge
        edge_boost = 105 * (ny ** 2) if ny < 0 else 105 * (ny ** 1.5)
        
        alpha = int(min(255, base_alpha + edge_boost))
        
        # Add a slight red tint towards the bottom
        red_tint = int(10 + 15 * (y / height))
        
        draw_ov.line([(0, y), (width, y)], fill=(red_tint, 4, 8, alpha))
        
    canvas = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(canvas)
    
    # Header
    draw_brand_header(canvas, width, label="NEWS", transparent=True)
    draw = ImageDraw.Draw(canvas)
    
    # Top Right Badge: "BREAKING NEWS | • LIVE"
    badge_x = width - 260
    badge_y = 50
    # Red Top Half
    draw.rectangle([badge_x, badge_y, badge_x + 220, badge_y + 45], fill=(220, 15, 20))
    t1 = "BREAKING"
    w1 = draw.textbbox((0,0), t1, font=F(28, True))[2]
    draw.text((badge_x + (220 - w1)//2, badge_y + 5), t1, font=F(28, True), fill=C["white"])
    # White Bottom Half
    draw.rectangle([badge_x, badge_y + 45, badge_x + 220, badge_y + 90], fill=C["white"])
    t2 = "NEWS"
    w2 = draw.textbbox((0,0), t2, font=F(36, True))[2]
    draw.text((badge_x + (220 - w2)//2, badge_y + 45), t2, font=F(36, True), fill=(0, 0, 0))
    # Live Pill
    draw.rounded_rectangle([badge_x + 130, badge_y + 100, badge_x + 220, badge_y + 135], radius=15, fill=(200, 15, 20))
    draw.text((badge_x + 145, badge_y + 102), "• LIVE", font=F(22, True), fill=C["white"])

    # Grab the viral hook or headline from the #1 story
    hook_text = top_article.get("ai_hook") or top_article.get("ai_title") or "THE WORLD RIGHT NOW"
    hook_text = hook_text.upper()
    
    # Font Awesome Setup
    fa_font = ImageFont.truetype("assets/fa-solid-900.ttf", 45)
    
    # Draw massive centered text: "5 BIG STORIES IN 60 SECONDS"
    title_y = 200
    
    # Calculate widths to center perfectly and prevent overlaps
    font_5 = F(480, True, impact=True)
    w5 = draw.textbbox((0,0), "5", font=font_5)[2]
    
    font_big = F(140, True, impact=True)
    w_big = draw.textbbox((0,0), "BIG", font=font_big)[2]
    
    font_stories = F(140, True, impact=True)
    w_stories = draw.textbbox((0,0), "STORIES", font=font_stories)[2]
    
    # Total block width = w5 + gap (20) + max(w_big, w_stories) + motion_lines (160)
    gap = 20
    motion_w = 160
    block_width = w5 + gap + max(w_big, w_stories) + motion_w
    start_x = (width - block_width) // 2
    
    # Draw "5"
    draw.text((start_x, title_y - 20), "5", font=font_5, fill=C["white"])
    
    # Draw "BIG"
    right_x = start_x + w5 + gap
    draw.text((right_x, title_y + 40), "BIG", font=font_big, fill=C["white"])
    
    # Draw "STORIES"
    draw.text((right_x, title_y + 170), "STORIES", font=font_stories, fill=(255, 195, 0)) # Yellow
    
    # Motion lines extending from STORIES
    line_x = right_x + w_stories + 40
    line_y_base = title_y + 170
    draw.line([(line_x, line_y_base + 60), (line_x + 160, line_y_base + 60)], fill=(220, 15, 20), width=10)
    draw.line([(line_x, line_y_base + 90), (line_x + 200, line_y_base + 90)], fill=(220, 15, 20), width=10)
    draw.line([(line_x, line_y_base + 120), (line_x + 180, line_y_base + 120)], fill=(220, 15, 20), width=10)
    
    # "IN 60 SECONDS" (Red slanted block) - moved down to prevent 5 overlap
    block_y = title_y + 400
    block_w = 600
    block_h = 90
    block_x = (width - block_w) // 2
    
    # Draw slanted polygon
    slant = 30
    draw.polygon([
        (block_x + slant, block_y), 
        (block_x + block_w, block_y), 
        (block_x + block_w - slant, block_y + block_h), 
        (block_x, block_y + block_h)
    ], fill=(220, 15, 20))
    
    font_60 = F(70, True, impact=True)
    # Text inside block
    draw.text((block_x + 60, block_y + 10), "IN", font=font_60, fill=C["white"])
    draw.text((block_x + 135, block_y + 10), "60", font=font_60, fill=(255, 195, 0))
    draw.text((block_x + 235, block_y + 10), "SECONDS", font=font_60, fill=C["white"])
    
    # Divider: FAST . FACTUAL . ESSENTIAL
    div_y = block_y + 130
    
    font_div = F(32, True)
    w_fast = draw.textbbox((0,0), "FAST", font=font_div)[2]
    w_factual = draw.textbbox((0,0), "FACTUAL", font=font_div)[2]
    w_essential = draw.textbbox((0,0), "ESSENTIAL", font=font_div)[2]
    w_dot = draw.textbbox((0,0), ".", font=font_div)[2]
    gap_div = 20
    
    total_div_w = w_fast + gap_div + w_dot + gap_div + w_factual + gap_div + w_dot + gap_div + w_essential
    dx = (width - total_div_w) // 2
    
    # Draw text piece by piece
    draw.text((dx, div_y), "FAST", font=font_div, fill=C["white"])
    dx += w_fast + gap_div
    draw.text((dx, div_y - 6), ".", font=font_div, fill=(220, 15, 20))
    dx += w_dot + gap_div
    draw.text((dx, div_y), "FACTUAL", font=font_div, fill=C["white"])
    dx += w_factual + gap_div
    draw.text((dx, div_y - 6), ".", font=font_div, fill=(220, 15, 20))
    dx += w_dot + gap_div
    draw.text((dx, div_y), "ESSENTIAL", font=font_div, fill=C["white"])
    
    # Draw exact lines
    draw.line([((width - total_div_w)//2 - 120, div_y + 20), ((width - total_div_w)//2 - 20, div_y + 20)], fill=C["white"], width=3)
    draw.line([(dx + w_essential + 20, div_y + 20), (dx + w_essential + 120, div_y + 20)], fill=C["white"], width=3)
    
    # 5 Circles Row
    circle_y = div_y + 80
    circle_r = 45
    spacing = 180
    start_x = width//2 - int(2 * spacing)
    labels = ["GLOBAL\nUPDATES", "POLITICS &\nGOVERNANCE", "ECONOMY\nIN FOCUS", "PEOPLE &\nSOCIETY", "MORE STORIES\nINSIDE"]
    # FontAwesome Unicodes: Globe, Bank, Chart, Users, Bullhorn
    icons = ["\uf0ac", "\uf19c", "\uf201", "\uf0c0", "\uf0a1"]
    
    for i in range(5):
        cx = start_x + i * spacing
        # Draw red circle with white outline
        draw.ellipse([cx - circle_r, circle_y, cx + circle_r, circle_y + circle_r*2], outline=(220, 15, 20), width=6)
        draw.ellipse([cx - circle_r + 4, circle_y + 4, cx + circle_r - 4, circle_y + circle_r*2 - 4], outline=C["white"], width=2)
        
        # Icon
        icon_str = icons[i]
        icon_w = draw.textbbox((0,0), icon_str, font=fa_font)[2]
        draw.text((cx - icon_w//2, circle_y + 20), icon_str, font=fa_font, fill=C["white"])
        
        # Draw vertical separator line after circle (except last)
        if i < 4:
            draw.line([(cx + spacing//2, circle_y + 10), (cx + spacing//2, circle_y + 90)], fill=(100, 100, 100, 180), width=2)
            
        # Label
        lines = labels[i].split('\n')
        for idx, lbl_line in enumerate(lines):
            lw = draw.textbbox((0,0), lbl_line, font=F(18, True))[2]
            draw.text((cx - lw//2, circle_y + 105 + idx*22), lbl_line, font=F(18, True), fill=C["white"])
            
    # Engagement Hook Block: WAIT TILL YOU SEE...
    hook_y = circle_y + 180
    hook_w = 700
    hook_h = 100
    hook_x = (width - hook_w) // 2
    
    # Draw black box with red outline
    draw.rounded_rectangle([hook_x, hook_y, hook_x + hook_w, hook_y + hook_h], radius=15, fill=(10, 5, 8), outline=(220, 15, 20), width=4)
    
    # Clock icon
    fa_clock = "\uf2f2"
    fa_clock_font = ImageFont.truetype("assets/fa-solid-900.ttf", 60)
    draw.text((hook_x + 40, hook_y + 20), fa_clock, font=fa_clock_font, fill=(220, 15, 20))
    
    # Text inside hook box
    hook_text_1 = "WAIT TILL YOU SEE"
    hook_text_2 = "THE LAST ONE..."
    font_h1 = F(32, True)
    font_h2 = F(36, True, impact=True)
    draw.text((hook_x + 130, hook_y + 15), hook_text_1, font=font_h1, fill=C["white"])
    draw.text((hook_x + 130, hook_y + 50), hook_text_2, font=font_h2, fill=(255, 195, 0))
    
    # Arrows inside hook box
    fa_angles = "\uf101"
    draw.text((hook_x + 600, hook_y + 25), fa_angles, font=fa_clock_font, fill=(220, 15, 20))

    # Footer Date
    footer_y = 1170
    date_str = datetime.now().strftime('%d %b %Y   |   %H:%M')
    # Calendar icon
    fa_cal = "\uf133"
    cal_w = draw.textbbox((0,0), fa_cal, font=F(24, True))[2]
    # Center everything
    footer_text = f"UPDATED: {date_str.upper()}"
    ft_w = draw.textbbox((0,0), footer_text, font=F(24, True))[2]
    total_w = cal_w + 10 + ft_w
    fx = (width - total_w) // 2
    
    fa_small = ImageFont.truetype("assets/fa-solid-900.ttf", 24)
    draw.text((fx, footer_y), fa_cal, font=fa_small, fill=(220, 15, 20))
    draw.text((fx + cal_w + 10, footer_y), footer_text, font=F(24, True), fill=(200, 200, 200))
    
    # Black Swipe Button (Bottom CTA)
    btn_w, btn_h = 600, 75
    btn_x, btn_y = (width - btn_w) // 2, 1220
    draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=40, fill=(10, 5, 8), outline=(220, 15, 20), width=4)
    
    btn_text = "WATCH FULL BREAKDOWN"
    text_w = draw.textbbox((0,0), btn_text, font=F(32, True))[2]
    # Place text and arrows perfectly
    btn_content_w = text_w + 20 + draw.textbbox((0,0), fa_angles, font=F(32, True))[2]
    bx = btn_x + (btn_w - btn_content_w) // 2
    draw.text((bx, btn_y + 20), btn_text, font=F(32, True), fill=C["white"])
    
    fa_mid = ImageFont.truetype("assets/fa-solid-900.ttf", 32)
    draw.text((bx + text_w + 20, btn_y + 20), fa_angles, font=fa_mid, fill=(220, 15, 20))

    canvas.save(path, "JPEG", quality=96)
    return path


def digest_story_slide(article, path, index, total):
    width, height = 1080, 1350
    print(f"    Slide {index + 1} - DIGEST STORY...")
    headline_text = article.get("ai_title") or slide_headline(article, max_chars=120)
    summary_text = article.get("ai_summary") or slide_summary(article, max_chars=350)
    label_text = story_label(article)
    
    # Base Image (Zoomed to perfectly fill the vertical canvas)
    base_img = get_photo(article, width, height, seed_offset=200 + index * 70, fit=True)
    
    # Cinematic Vignette Overlay (Dark left and bottom for text readability)
    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    # Overall subtle dimming to ensure text pops
    draw_ov.rectangle([0, 0, width, height], fill=(12, 6, 10, 80))
    
    # Heavy left gradient for the massive headline and summary box
    fade_w = int(width * 0.75)
    for x in range(fade_w):
        alpha = int(220 * (1 - (x / fade_w)))
        draw_ov.line([(x, 0), (x, height)], fill=(12, 6, 10, alpha))
        
    # Heavy bottom gradient for the page counter
    fade_h_start = int(height * 0.75)
    for y in range(fade_h_start, height):
        alpha = int(240 * ((y - fade_h_start) / (height - fade_h_start)))
        draw_ov.line([(0, y), (width, y)], fill=(12, 6, 10, alpha))
    # Composite vignette overlay onto base image
    canvas = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')

    draw = ImageDraw.Draw(canvas)

    # Transparent Header
    draw_brand_header(canvas, width, label=label_text, transparent=True)
    draw = ImageDraw.Draw(canvas)

    # Date & Category Pill
    pill_y = 160
    date_str = article.get("ai_date") or datetime.now().strftime('%d %b %Y')
    draw.text((60, pill_y + 5), date_str.upper(), font=F(28, False), fill=C["offwhite"])
    draw.line([(240, pill_y), (240, pill_y + 40)], fill=(100, 100, 100), width=2)
    
    category = article["category"].upper()
    cat_w = draw.textbbox((0, 0), category, font=F(28, True))[2]
    draw.rounded_rectangle([260, pill_y, 260 + cat_w + 30, pill_y + 40], radius=8, fill=(160, 15, 20))
    draw.text((275, pill_y + 5), category, font=F(28, True), fill=C["white"])

    # Huge Left-Aligned Headline
    title_y = 240
    title_font = F(84, True)
    wrapped_title = textwrap.wrap(headline_text.upper(), width=16)[:4]

    # Draw a smooth transparent dark panel EXACTLY behind the headline lines only
    # This avoids any hard-edge seam — it's drawn per-line as a rounded rect with low alpha
    panel_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel_layer)
    for i, line in enumerate(wrapped_title):
        lw = draw.textbbox((0, 0), line, font=title_font)[2]
        lh = draw.textbbox((0, 0), line, font=title_font)[3]
        px1 = 40
        py1 = title_y - 8
        px2 = px1 + lw + 30
        py2 = title_y + lh + 8
        panel_draw.rounded_rectangle([px1, py1, px2, py2], radius=8, fill=(8, 4, 6, 100))
        title_y += 90
    canvas = Image.alpha_composite(canvas.convert("RGBA"), panel_layer).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Now draw headline text on top
    # AI generates 2-part headlines: "WHAT HAPPENED — Why it matters"
    title_y = 240
    title_font = F(78, True)       # Part 1: large, bold
    title_font_sm = F(58, True)    # Part 2: smaller, informative

    full_headline = headline_text.upper()

    if " — " in full_headline or " - " in full_headline:
        sep = " — " if " — " in full_headline else " - "
        part1, part2 = full_headline.split(sep, 1)

        # Part 1: large white — the event/action
        for line in textwrap.wrap(part1, width=18)[:2]:
            draw.text((63, title_y + 3), line, font=title_font, fill=(0, 0, 0))
            draw.text((60, title_y), line, font=title_font, fill=C["white"])
            title_y += 88

        # Thin red accent divider
        title_y += 6
        draw.line([(60, title_y), (420, title_y)], fill=C["red"], width=4)
        title_y += 16

        # Part 2: smaller yellow — the impact/context
        for line in textwrap.wrap(part2, width=24)[:2]:
            draw.text((63, title_y + 2), line, font=title_font_sm, fill=(0, 0, 0))
            draw.text((60, title_y), line, font=title_font_sm, fill=(255, 195, 0))
            title_y += 68
    else:
        # Fallback: line 1 white, line 2 yellow, line 3 red
        for i, line in enumerate(textwrap.wrap(full_headline, width=18)[:4]):
            color = C["white"] if i == 0 else (255, 195, 0) if i == 1 else C["red"]
            draw.text((63, title_y + 3), line, font=title_font, fill=(0, 0, 0))
            draw.text((60, title_y), line, font=title_font, fill=color)
            title_y += 88

    # Summary Intro Paragraph (Enlarged)
    title_bottom = title_y + 20
    summary_y = title_bottom
    
    if article.get("ai_rewritten"):
        intro_text = summary_text
        bullets = article.get("ai_highlights", [])[:4]
    else:
        sentences = [s.strip() for s in re.split(r'[.!?]', summary_text) if len(s.strip()) > 15]
        if len(sentences) > 1:
            intro_text = sentences[0] + "."
            bullets = sentences[1:4]
        else:
            clauses = [c.strip() for c in re.split(r'[,;]\s+', summary_text) if len(c.strip()) > 15]
            if len(clauses) > 1:
                intro_text = clauses[0] + ","
                bullets = clauses[1:4]
            else:
                intro_text = "Latest development:"
                bullets = [summary_text]
            
    # Wrap up to 6 lines for the 40-60 word AI summary
    summary_lines = textwrap.wrap(intro_text, width=40)[:6]

    # Draw per-line frosted glass panel under summary (same style as headline)
    summary_panel_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    summary_panel_draw = ImageDraw.Draw(summary_panel_layer)
    _sy = summary_y
    for line in summary_lines:
        lw = draw.textbbox((0, 0), line, font=F(38, False))[2]
        lh = draw.textbbox((0, 0), line, font=F(38, False))[3]
        summary_panel_draw.rounded_rectangle(
            [40, _sy - 4, 40 + lw + 25, _sy + lh + 4],
            radius=6,
            fill=(8, 4, 6, 110)
        )
        _sy += 50
    canvas = Image.alpha_composite(canvas.convert("RGBA"), summary_panel_layer).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Draw summary text on top
    for line in summary_lines:
        draw.text((61, summary_y + 2), line, font=F(38, False), fill=(0, 0, 0))  # shadow
        draw.text((60, summary_y), line, font=F(38, False), fill=(220, 220, 220))
        summary_y += 50

    # Key Highlights Box (Enlarged and dynamic)
    summary_y += 40
    box_w = 780
        
    # Precisely calculate box height based on wrapping
    box_h = 80
    wrapped_bullets_list = []
    for bullet in bullets:
        b_text = shorten(bullet.capitalize(), 80)
        wrapped_b = textwrap.wrap(b_text, width=42)
        wrapped_bullets_list.append(wrapped_b)
        box_h += len(wrapped_b) * 45
    box_h += (len(bullets) - 1) * 30 + 20 # Add padding for separators and bottom

    draw.rounded_rectangle([60, summary_y, 60 + box_w, summary_y + box_h], radius=20, fill=(15, 8, 10, 200), outline=(80, 20, 25), width=3)
    draw.rounded_rectangle([60, summary_y, 60 + 320, summary_y + 55], radius=16, fill=(160, 15, 20))
    draw.text((80, summary_y + 12), "KEY HIGHLIGHTS", font=F(30, True), fill=C["white"])
    
    bullet_y = summary_y + 80
    for idx, wrapped_b in enumerate(wrapped_bullets_list):
        draw.ellipse([85, bullet_y + 15, 97, bullet_y + 27], fill=C["red"])
        for line in wrapped_b:
            draw.text((125, bullet_y), line, font=F(34, False), fill=C["offwhite"])
            bullet_y += 45
        if idx < len(bullets) - 1:
            draw.line([(80, bullet_y + 10), (60 + box_w - 30, bullet_y + 10)], fill=(60, 40, 45), width=2)
        bullet_y += 30

    # Bottom Footer
    draw.text((60, 1220), f"Source: {display_source(article['source'])}", font=F(32, True), fill=(180, 180, 180))
    
    draw.rectangle([0, 1270, width, height], fill=(120, 10, 15))
    draw.text((60, 1295), "STAY INFORMED. STAY AHEAD.", font=F(28, True), fill=C["white"])
    draw.text((width - 400, 1295), "Swipe for next update ->" if index < total else "End of Hourly Digest", font=F(28, True), fill=C["white"])

    canvas.save(path, "JPEG", quality=96)
    return path


def create_carousel(article, prefix=None):
    timestamp = datetime.now().strftime("%H%M%S%f")[:10]
    prefix = prefix or f"{article['category'].lower()}_{timestamp}"
    print(f"\n  Story carousel: {article['title'][:55]}...")
    paths = [
        OUTPUT_DIR / f"{prefix}_1_main.jpg",
        OUTPUT_DIR / f"{prefix}_2_facts.jpg",
        OUTPUT_DIR / f"{prefix}_3_visual.jpg",
        OUTPUT_DIR / f"{prefix}_4_cta.jpg",
    ]
    slide1_main(article, str(paths[0]))
    slide2_facts(article, str(paths[1]))
    slide3_visual(article, str(paths[2]))
    slide4_cta(article, str(paths[3]))
    print("  4 slides saved")
    return [str(path) for path in paths]


def create_single(article, prefix=None):
    timestamp = datetime.now().strftime("%H%M%S%f")[:10]
    prefix = prefix or f"{article['category'].lower()}_{timestamp}"
    path = OUTPUT_DIR / f"{prefix}_breaking.jpg"
    print(f"\n  Single post: {article['title'][:55]}...")
    slide1_main(article, str(path))
    print("  Saved")
    return str(path)


def create_digest_carousel(articles, prefix=None):
    timestamp = datetime.now().strftime("%H%M%S%f")[:10]
    prefix = prefix or f"digest_{timestamp}"
    print(f"\n  Hourly digest carousel with {len(articles)} stories")
    paths = [OUTPUT_DIR / f"{prefix}_1_cover.jpg"]
    for index in range(len(articles)):
        paths.append(OUTPUT_DIR / f"{prefix}_{index + 2}_story.jpg")

    digest_cover_slide(articles, str(paths[0]))
    for index, article in enumerate(articles, start=1):
        digest_story_slide(article, str(paths[index]), index, len(articles))

    print(f"  {len(paths)} digest slides saved")
    return [str(path) for path in paths]
