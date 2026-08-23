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

HINDI_TRANSLATE = {
    "INDIA": "भारत",
    "WORLD": "दुनिया",
    "BUSINESS": "बिज़नेस",
    "TECH": "तकनीक",
    "SPORTS": "खेल",
    "ENTERTAINMENT": "मनोरंजन",
    "SCIENCE": "विज्ञान",
    "POLITICS": "राजनीति",
    "BREAKING": "ब्रेकिंग न्यूज़",
    "BREAKING NEWS": "ब्रेकिंग न्यूज़",
    "SUMMARY EXCLUSIVE": "विशेष सारांश",
    "KEY FACTS": "मुख्य तथ्य",
    "KEY HIGHLIGHTS": "मुख्य झलकियां",
    "WATCH FULL BREAKDOWN": "पूरा विश्लेषण देखें",
    "WAIT TILL YOU SEE": "अंत तक देखें",
    "THE LAST ONE...": "बहुत महत्वपूर्ण है...",
    "FAST . FACTUAL . ESSENTIAL": "तेज़ . सटीक . ज़रूरी",
    "GLOBAL UPDATES": "ग्लोबल अपडेट्स",
    "POLITICS & GOVERNANCE": "राजनीति एवं शासन",
    "ECONOMY IN FOCUS": "अर्थव्यवस्था",
    "PEOPLE & SOCIETY": "लोग और समाज",
    "MORE STORIES INSIDE": "अन्य मुख्य खबरें",
    "UPDATED": "अपडेटेड",
    "STAY INFORMED. STAY AHEAD.": "सटीक जानकारी, सबसे पहले।",
    "Follow for breaking news 24/7": "24/7 ताज़ा खबरों के लिए फॉलो करें"
}

def translate_to_hindi(text):
    text_upper = str(text).upper().strip()
    return HINDI_TRANSLATE.get(text_upper, text)


def _add_bottom_vignette(image):
    """Add a smooth dark gradient vignette to the lower half of the background image to ensure text legibility while keeping top/center photo 100% sharp."""
    width, height = image.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Gradient starts smoothly at 25% height down to 88% opacity near bottom
    start_y = int(height * 0.25)
    gradient_height = max(1, height - start_y)
    
    for y in range(start_y, height):
        ratio = (y - start_y) / gradient_height
        alpha = int(225 * (ratio ** 1.5)) # Non-linear smooth curve for natural vignette
        draw.line([(0, y), (width, y)], fill=(10, 11, 16, alpha))
        
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _fit_image(image, width, height, fit=True):
    img = image.convert("RGB")
    
    if fit:
        # Crisp full-bleed 1080p sharp image fit (no heavy blur side panels)
        scaled = ImageOps.fit(img, (width, height), Image.LANCZOS)
        # Apply smooth dark bottom vignette gradient overlay
        return _add_bottom_vignette(scaled)
        
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


def get_category_color(category):
    cat = str(category).upper().strip()
    if cat in ["INDIA", "NATIONAL", "DELHI"]:
        return (245, 124, 0)      # Saffron Orange
    elif cat in ["WORLD", "GLOBAL", "INTERNATIONAL"]:
        return (0, 122, 255)      # Electric Blue
    elif cat in ["BUSINESS", "FINANCE", "STARTUPS", "ECONOMY"]:
        return (16, 185, 129)     # Emerald Green
    elif cat in ["TECH", "TECHNOLOGY", "SCIENCE", "AI"]:
        return (6, 182, 212)      # Cyan/Teal
    elif cat in ["SPORTS"]:
        return (245, 158, 11)     # Amber Gold
    elif cat in ["ENTERTAINMENT", "BOLLYWOOD"]:
        return (168, 85, 247)     # Purple/Magenta
    elif cat in ["POLITICS", "BREAKING"]:
        return (230, 30, 45)      # Crimson Red
    return (230, 30, 45)          # Default red


def paste_logo(canvas, x_coord, y_coord, size=90):
    try:
        logo = Image.open(LOGO_FILE).convert("RGBA").resize((size, size), Image.LANCZOS)
        layer = canvas.convert("RGBA")
        layer.paste(logo, (x_coord, y_coord), logo)
        canvas.paste(layer.convert("RGB"), (0, 0))
    except Exception:
        pass


def F(size, bold=True, impact=False, lang="en"):
    if impact and lang == "en":
        local_path = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"
        if local_path.exists():
            return ImageFont.truetype(str(local_path), size)
        font_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
        ]
    elif bold or (impact and lang != "en"):
        font_name = "Poppins-Bold.ttf" if lang != "en" else "Roboto-Bold.ttf"
        local_path = BASE_DIR / "assets" / "fonts" / font_name
        if local_path.exists():
            return ImageFont.truetype(str(local_path), size)
        font_paths = [
            "C:/Windows/Fonts/mangal.ttf" if lang != "en" else "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/verdanab.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        font_name = "Poppins-Regular.ttf" if lang != "en" else "Roboto-Regular.ttf"
        local_path = BASE_DIR / "assets" / "fonts" / font_name
        if local_path.exists():
            return ImageFont.truetype(str(local_path), size)
        font_paths = [
            "C:/Windows/Fonts/mangal.ttf" if lang != "en" else "C:/Windows/Fonts/arial.ttf",
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


def slide1_main(article, path, lang="en"):
    width, height = 1080, 1350
    print("    Slide 1 - MAIN...")
    
    if lang == "hi":
        headline_text = article.get("ai_title_hindi") or article.get("ai_title") or slide_headline(article, max_chars=95)
        summary_text = article.get("ai_summary_hindi") or article.get("ai_summary") or slide_summary(article, max_chars=150)
    else:
        headline_text = article.get("ai_title") or slide_headline(article, max_chars=95)
        summary_text = article.get("ai_summary") or slide_summary(article, max_chars=150)
    
    # 1. Start with a premium dark canvas
    canvas = Image.new("RGB", (width, height), C["dark_bg"])
    
    # 2. Get and paste image in the upper 2/3 (height 820)
    photo = get_photo(article, width, 820, fit=True)
    canvas.paste(photo, (0, 0))
    
    # 3. Apply a heavy bottom fade to the image so text on top is 100% readable
    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    fade_start = 320
    fade_end = 820
    for y in range(fade_start, fade_end):
        ratio = (y - fade_start) / (fade_end - fade_start)
        alpha = int(255 * ratio)
        draw_ov.line([(0, y), (width, y)], fill=(C["dark_bg"][0], C["dark_bg"][1], C["dark_bg"][2], alpha))
        
    # Black out everything below fade_end
    draw_ov.rectangle([0, fade_end, width, height], fill=(C["dark_bg"][0], C["dark_bg"][1], C["dark_bg"][2], 255))
    
    canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(canvas)
    
    # 4. Draw modern transparent brand header at the very top
    draw_brand_header(canvas, width, transparent=True)
    draw = ImageDraw.Draw(canvas)
    
    # 5. Accent color based on category
    category_name = article.get("category", "WORLD").upper()
    accent_color = get_category_color(category_name)
    
    # 6. Category / Status Tag at y=180
    tag_y = 180
    is_breaking = article.get("breaking")
    tag_text = "BREAKING NEWS" if is_breaking else category_name
    if lang == "hi":
        tag_text = translate_to_hindi(tag_text)
    tag_bg = C["red"] if is_breaking else accent_color
    
    tag_font = F(28, True, lang=lang)
    tb = draw.textbbox((0, 0), tag_text, font=tag_font)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    
    pill_padding_x = 24
    pill_padding_y = 10
    pill_w = tw + 2 * pill_padding_x
    pill_h = th + 2 * pill_padding_y
    pill_x = 60
    draw.rounded_rectangle([pill_x, tag_y, pill_x + pill_w, tag_y + pill_h], radius=8, fill=tag_bg)
    draw.text((pill_x + pill_padding_x, tag_y + pill_padding_y), tag_text, font=tag_font, fill=C["white"])
    
    # Thin accent line to the right of the tag
    draw.line([(pill_x + pill_w + 20, tag_y + pill_h // 2), (width - 60, tag_y + pill_h // 2)], fill=(40, 45, 60), width=3)
    
    # 7. Sleek, Premium Headline (starts at y=260)
    headline_y = 260
    headline_font = F(64, True, lang=lang)
    
    wrapped_headline = textwrap.wrap(headline_text, width=24)[:4]
    
    # Draw subtle background glow block for the headline lines
    panel_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel_layer)
    _hy = headline_y
    for line in wrapped_headline:
        lw = draw.textbbox((0, 0), line, font=headline_font)[2]
        lh = draw.textbbox((0, 0), line, font=headline_font)[3]
        panel_draw.rounded_rectangle([50, _hy - 6, 50 + lw + 24, _hy + lh + 6], radius=6, fill=(10, 11, 16, 150))
        _hy += 76
    canvas = Image.alpha_composite(canvas.convert("RGBA"), panel_layer).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    
    _hy = headline_y
    for line in wrapped_headline:
        draw.text((62, _hy + 2), line, font=headline_font, fill=(0, 0, 0))
        draw.text((60, _hy), line, font=headline_font, fill=C["white"])
        _hy += 76
        
    # Draw vertical accent bar next to the headline
    draw.rectangle([44, headline_y, 48, _hy - 16], fill=tag_bg)
    
    # 8. Premium Summary Card at the bottom (y=650)
    summary_y = 650
    summary_font = F(38, False, lang=lang)
    wrapped_summary = textwrap.wrap(summary_text, width=44)[:4]
    
    card_x1 = 50
    card_y1 = summary_y - 20
    card_x2 = width - 50
    card_y2 = height - 160
    
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=16, fill=(20, 22, 32, 180), outline=(45, 48, 65), width=2)
    
    card_title = translate_to_hindi("SUMMARY EXCLUSIVE") if lang == "hi" else "SUMMARY EXCLUSIVE"
    draw.text((74, summary_y), card_title, font=F(26, True, lang=lang), fill=accent_color)
    summary_y += 42
    
    for line in wrapped_summary:
        draw.text((74, summary_y), line, font=summary_font, fill=C["offwhite"])
        summary_y += 50
        
    # 9. Bottom Footer Bar (y=1220 onwards)
    footer_y = 1220
    draw.line([(50, footer_y - 10), (width - 50, footer_y - 10)], fill=(45, 48, 65), width=2)
    
    paste_logo(canvas, 60, footer_y, size=60)
    draw = ImageDraw.Draw(canvas)
    handle_text = f"{PAGE_HANDLE}.hindi" if lang == "hi" else PAGE_HANDLE
    draw.text((134, footer_y + 12), handle_text, font=F(32, True, lang=lang), fill=C["white"])
    
    swipe_text = translate_to_hindi("Swipe for context →") if lang == "hi" else "Swipe for context →"
    sw_w = draw.textbbox((0, 0), swipe_text, font=F(28, True, lang=lang))[2]
    draw.text((width - 60 - sw_w, footer_y + 14), swipe_text, font=F(28, True, lang=lang), fill=accent_color)
    
    source_label = "स्रोत" if lang == "hi" else "Source"
    source_line = f"{source_label}: {display_source(article['source'])}  |  {datetime.now().strftime('%d %b %Y')}"
    draw.text((60, footer_y + 80), source_line.upper(), font=F(24, True, lang=lang), fill=(100, 105, 120))
    
    canvas.save(path, "JPEG", quality=96)
    return path


def slide2_facts(article, path, lang="en"):
    width, height = 1080, 1350
    print("    Slide 2 - FACTS...")
    
    if lang == "hi":
        headline_text = article.get("ai_title_hindi") or article.get("ai_title") or slide_headline(article, max_chars=75)
        summary_text = article.get("ai_summary_hindi") or article.get("ai_summary") or slide_summary(article, max_chars=250)
    else:
        headline_text = article.get("ai_title") or slide_headline(article, max_chars=75)
        summary_text = article.get("ai_summary") or slide_summary(article, max_chars=250)
    
    # 1. Premium dark background
    canvas = Image.new("RGB", (width, height), C["dark_bg"])
    draw_brand_header(canvas, width, transparent=True)
    draw = ImageDraw.Draw(canvas)
    
    # Category accent color
    category_name = article.get("category", "WORLD").upper()
    accent_color = get_category_color(category_name)
    
    # 2. Header Tag at y=160
    tag_y = 160
    tag_text = translate_to_hindi("KEY FACTS") if lang == "hi" else "KEY FACTS"
    tag_font = F(24, True, lang=lang)
    tb = draw.textbbox((0, 0), tag_text, font=tag_font)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    
    draw.rounded_rectangle([60, tag_y, 60 + tw + 32, tag_y + th + 16], radius=6, fill=accent_color)
    draw.text((76, tag_y + 8), tag_text, font=tag_font, fill=C["white"])
    
    # 3. Slide Title (Article Headline)
    title_y = 220
    title_font = F(46, True, lang=lang)
    wrapped_title = textwrap.wrap(headline_text, width=38)[:2]
    for line in wrapped_title:
        draw.text((60, title_y), line, font=title_font, fill=C["white"])
        title_y += 56
        
    # 4. Vertical Timeline Line
    timeline_x = 90
    timeline_start_y = title_y + 30
    timeline_end_y = 1140
    draw.line([(timeline_x, timeline_start_y), (timeline_x, timeline_end_y)], fill=(45, 48, 65), width=4)
    
    # 5. Extract sentences
    sentences = [item.strip() for item in re.split(r"[.!?]", summary_text) if len(item.strip()) > 20]
    if len(sentences) < 2:
        words = summary_text.split()
        chunk_size = max(len(words) // 4, 1)
        sentences = [" ".join(words[index:index + chunk_size]) for index in range(0, len(words), chunk_size)]
        
    facts = sentences[:4]
    handle_text = f"{PAGE_HANDLE}.hindi" if lang == "hi" else PAGE_HANDLE
    while len(facts) < 4:
        fallback_msg = f"इस खबर पर लेटेस्ट लाइव अपडेट के लिए {handle_text} को फॉलो करें।" if lang == "hi" else f"Follow {PAGE_HANDLE} for more live updates on this story."
        facts.append(fallback_msg)
        
    # Draw facts
    fact_y = timeline_start_y + 20
    fact_spacing = (timeline_end_y - timeline_start_y - 40) // 4
    
    for index, fact in enumerate(facts, start=1):
        # Draw number bullet circle centered on timeline
        bullet_r = 24
        bullet_box = [
            timeline_x - bullet_r, 
            fact_y + 6, 
            timeline_x + bullet_r, 
            fact_y + 6 + 2 * bullet_r
        ]
        
        # Draw glowing circle border
        draw.ellipse(bullet_box, fill=(20, 22, 32), outline=accent_color, width=3)
        
        # Draw number inside
        num_str = str(index)
        num_font = F(26, True, lang=lang)
        nb = draw.textbbox((0, 0), num_str, font=num_font)
        nw = nb[2] - nb[0]
        nh = nb[3] - nb[1]
        draw.text(
            (
                timeline_x - nw // 2, 
                fact_y + 6 + bullet_r - nh // 2 - 2
            ), 
            num_str, 
            font=num_font, 
            fill=C["white"]
        )
        
        # Draw Fact Text
        fact_font = F(34, False, lang=lang)
        wrapped_fact = textwrap.wrap(shorten(fact, 140), width=44)[:3]
        
        text_y = fact_y
        for i, line in enumerate(wrapped_fact):
            # Bold the first few words of the first line for editorial emphasis
            if i == 0 and len(line.split()) > 2:
                words = line.split()
                bold_part = " ".join(words[:2])
                normal_part = " " + " ".join(words[2:])
                
                # Draw bold part
                draw.text((144, text_y), bold_part, font=F(34, True, lang=lang), fill=accent_color)
                bp_w = draw.textbbox((0, 0), bold_part, font=F(34, True, lang=lang))[2]
                # Draw normal part
                draw.text((144 + bp_w, text_y), normal_part, font=fact_font, fill=C["offwhite"])
            else:
                draw.text((144, text_y), line, font=fact_font, fill=C["offwhite"])
            text_y += 44
            
        fact_y += fact_spacing
        
    # 6. Footer
    footer_y = 1200
    draw.line([(60, footer_y), (width - 60, footer_y)], fill=(45, 48, 65), width=2)
    
    paste_logo(canvas, 60, footer_y + 20, size=60)
    draw = ImageDraw.Draw(canvas)
    draw.text((134, footer_y + 32), handle_text, font=F(32, True, lang=lang), fill=C["white"])
    
    swipe_text = translate_to_hindi("Swipe for visual breakdown →") if lang == "hi" else "Swipe for visual breakdown →"
    sw_w = draw.textbbox((0, 0), swipe_text, font=F(28, True, lang=lang))[2]
    draw.text((width - 60 - sw_w, footer_y + 34), swipe_text, font=F(28, True, lang=lang), fill=accent_color)
    
    source_label = "स्रोत" if lang == "hi" else "Source"
    source_line = f"{source_label}: {display_source(article['source'])}  |  {datetime.now().strftime('%d %b %Y')}"
    draw.text((60, footer_y + 94), source_line.upper(), font=F(24, True, lang=lang), fill=(100, 105, 120))
    
    canvas.save(path, "JPEG", quality=96)
    return path


def slide3_visual(article, path, lang="en"):
    width, height = 1080, 1350
    print("    Slide 3 - VISUAL...")
    
    if lang == "hi":
        headline_text = article.get("ai_title_hindi") or article.get("ai_title") or slide_headline(article, max_chars=75)
        summary_text = article.get("ai_summary_hindi") or article.get("ai_summary") or slide_summary(article, max_chars=150)
        quote_text = article.get("ai_hook_hindi") or article.get("ai_title_hindi") or article.get("ai_hook") or headline_text
    else:
        headline_text = article.get("ai_title") or slide_headline(article, max_chars=75)
        summary_text = article.get("ai_summary") or slide_summary(article, max_chars=150)
        quote_text = article.get("ai_hook") or headline_text
        
    # 1. Base Image - full bleed
    photo = get_photo(article, width, height, seed_offset=300, fit=True)
    
    # 2. Cinematic Vignette Overlay (Dark at bottom and top)
    overlay = Image.new('RGBA', photo.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    # Global dim
    draw_ov.rectangle([0, 0, width, height], fill=(12, 13, 20, 90))
    
    # Top fade (for header)
    for y in range(220):
        alpha = int(180 * (1 - (y / 220)))
        draw_ov.line([(0, y), (width, y)], fill=(10, 11, 16, alpha))
        
    # Bottom fade (for text and footer)
    fade_start = 550
    for y in range(fade_start, height):
        ratio = (y - fade_start) / (height - fade_start)
        alpha = int(240 * ratio)
        draw_ov.line([(0, y), (width, y)], fill=(10, 11, 16, alpha))
        
    canvas = Image.alpha_composite(photo.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(canvas)
    
    # 3. Transparent Brand Header
    draw_brand_header(canvas, width, transparent=True)
    draw = ImageDraw.Draw(canvas)
    
    # Category / Accent
    category_name = article.get("category", "WORLD").upper()
    accent_color = get_category_color(category_name)
    
    # Category Tag pill in top right
    category_text = translate_to_hindi(category_name) if lang == "hi" else category_name
    tag_font = F(24, True, lang=lang)
    tb = draw.textbbox((0, 0), category_text, font=tag_font)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    
    pill_x = width - tw - 80
    pill_y = 44
    draw.rounded_rectangle([pill_x, pill_y, pill_x + tw + 32, pill_y + th + 16], radius=6, fill=accent_color)
    draw.text((pill_x + 16, pill_y + 8), category_text, font=tag_font, fill=C["white"])
    
    # 4. Premium Glassmorphic Quote Card (y=620)
    card_y = 660
    card_x1 = 60
    card_x2 = width - 60
    
    # Let's wrap quote first to calculate height dynamically
    if not quote_text.startswith('"'):
        quote_text = f'"{quote_text}"'
        
    quote_font = F(56, True, lang=lang)
    wrapped_quote = textwrap.wrap(quote_text, width=32)[:3]
    
    card_h = 40 + len(wrapped_quote) * 66 + 60 # padding + text + citation space
    card_y2 = card_y + card_h
    
    # Draw rounded rect background
    draw.rounded_rectangle([card_x1, card_y, card_x2, card_y2], radius=16, fill=(15, 17, 26, 190), outline=(45, 48, 65), width=2)
    
    # Draw thick accent color left border line
    draw.rectangle([card_x1 + 4, card_y + 12, card_x1 + 10, card_y2 - 12], fill=accent_color)
    
    # Draw Quote Lines
    qy = card_y + 24
    for line in wrapped_quote:
        draw.text((card_x1 + 34, qy), line, font=quote_font, fill=C["white"])
        qy += 66
        
    # Draw Source Citation inside the card bottom right
    source_label = "स्रोत" if lang == "hi" else "SOURCE"
    source_text = f"— {source_label}: {display_source(article['source']).upper()}"
    source_font = F(24, True, lang=lang)
    sb = draw.textbbox((0, 0), source_text, font=source_font)
    sw = sb[2] - sb[0]
    draw.text((card_x2 - sw - 30, qy + 10), source_text, font=source_font, fill=accent_color)
    
    # 5. Summary Text below Quote Card
    summary_y = card_y2 + 40
    summary_font = F(34, False, lang=lang)
    wrapped_summary = textwrap.wrap(summary_text, width=50)[:3]
    
    for line in wrapped_summary:
        draw.text((61, summary_y + 1), line, font=summary_font, fill=(0, 0, 0))
        draw.text((60, summary_y), line, font=summary_font, fill=C["offwhite"])
        summary_y += 44
        
    # 6. Transparent Footer
    footer_y = 1200
    draw.line([(60, footer_y), (width - 60, footer_y)], fill=(45, 48, 65), width=2)
    
    paste_logo(canvas, 60, footer_y + 20, size=60)
    draw = ImageDraw.Draw(canvas)
    handle_text = f"{PAGE_HANDLE}.hindi" if lang == "hi" else PAGE_HANDLE
    draw.text((134, footer_y + 32), handle_text, font=F(32, True, lang=lang), fill=C["white"])
    
    save_text = translate_to_hindi("Save this post for later") if lang == "hi" else "Save this post for later"
    sv_w = draw.textbbox((0, 0), save_text, font=F(28, True, lang=lang))[2]
    draw.text((width - 60 - sv_w, footer_y + 34), save_text, font=F(28, True, lang=lang), fill=accent_color)
    
    footer_title = "न्यूज़ फ़्लैश 5  |  सटीक एवं निष्पक्ष विश्लेषण" if lang == "hi" else "NEWS FLASH 5  |  VERIFIED & FACTUAL UPDATES"
    draw.text((60, footer_y + 94), footer_title, font=F(24, True, lang=lang), fill=(100, 105, 120))
    
    canvas.save(path, "JPEG", quality=96)
    return path


def slide4_cta(article, path, lang="en"):
    width, height = 1080, 1350
    print("    Slide 4 - CTA...")
    
    # Category Accent Color
    category_name = article.get("category", "WORLD").upper()
    accent_color = get_category_color(category_name)
    
    # 1. Premium background gradient with a subtle corner glow
    canvas = Image.new("RGB", (width, height), C["dark_bg"])
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        ratio = y / height
        c_r = int(C["dark_bg"][0] + (accent_color[0] - C["dark_bg"][0]) * 0.12 * ratio)
        c_g = int(C["dark_bg"][1] + (accent_color[1] - C["dark_bg"][1]) * 0.12 * ratio)
        c_b = int(C["dark_bg"][2] + (accent_color[2] - C["dark_bg"][2]) * 0.12 * ratio)
        draw.line([(0, y), (width, y)], fill=(c_r, c_g, c_b))
        
    draw = ImageDraw.Draw(canvas)
    
    # 2. Logo with glowing ring (centered at y=180)
    logo_size = 280
    logo_x = (width - logo_size) // 2
    logo_y = 180
    
    # Draw glowing circular ring border
    ring_padding = 20
    draw.ellipse(
        [
            logo_x - ring_padding, 
            logo_y - ring_padding, 
            logo_x + logo_size + ring_padding, 
            logo_y + logo_size + ring_padding
        ], 
        outline=accent_color, 
        width=5
    )
    
    paste_logo(canvas, logo_x, logo_y, size=logo_size)
    draw = ImageDraw.Draw(canvas)
    
    # 3. Brand Header Title
    title_y = 520
    brand_name = "न्यूज़ फ़्लैश 5" if lang == "hi" else "NEWS FLASH 5"
    brand_font = F(72, True, lang=lang)
    center_x(draw, title_y, brand_name, brand_font, C["white"], width)
    
    handle_text = f"{PAGE_HANDLE}.hindi" if lang == "hi" else PAGE_HANDLE
    handle_font = F(38, True, lang=lang)
    center_x(draw, title_y + 80, handle_text, handle_font, accent_color, width)
    
    # 4. Premium CTA Card
    card_x1 = 100
    card_y1 = 690
    card_x2 = width - 100
    card_y2 = 1140
    
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=20, fill=(20, 22, 32, 200), outline=(45, 48, 65), width=2)
    
    # CTA Card Content
    card_draw_y = card_y1 + 40
    card_header = "हर घंटे देश और दुनिया की ताज़ा खबरें" if lang == "hi" else "YOUR DAILY PORTAL FOR INSTANT GLOBAL NEWS"
    center_x(draw, card_draw_y, card_header, F(28, True, lang=lang), (140, 145, 160), width)
    
    # Follow instruction text
    card_draw_y += 64
    line1 = "हर घंटे की ताज़ा अपडेट और विश्लेषण के लिए" if lang == "hi" else "Follow for hourly updates, visual breakdowns"
    line2 = "पेज को आज ही फॉलो करें।" if lang == "hi" else "and verified breaking news alerts."
    center_x(draw, card_draw_y, line1, F(34, False, lang=lang), C["offwhite"], width)
    center_x(draw, card_draw_y + 42, line2, F(34, False, lang=lang), C["offwhite"], width)
    
    # Turn on notifications button
    btn_w = 560
    btn_h = 76
    btn_x = (width - btn_w) // 2
    btn_y = card_draw_y + 120
    
    draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=38, fill=accent_color)
    
    btn_text = "नोटिफिकेशन ऑन करें" if lang == "hi" else "TURN ON NOTIFICATIONS"
    btn_font = F(30, True, lang=lang)
    bt_b = draw.textbbox((0, 0), btn_text, font=btn_font)
    bt_w = bt_b[2] - bt_b[0]
    bt_h = bt_b[3] - bt_b[1]
    
    draw.text((btn_x + (btn_w - bt_w) // 2, btn_y + (btn_h - bt_h) // 2 - 2), btn_text, font=btn_font, fill=C["white"])
    
    # Spacing and multi-platform links
    platform_y = btn_y + 120
    center_x(draw, platform_y, "INSTAGRAM  |  TELEGRAM  |  WHATSAPP  |  YOUTUBE", F(26, True, lang=lang), (120, 125, 140), width)
    
    # 5. Footer Copyright
    footer_y = 1220
    draw.line([(100, footer_y), (width - 100, footer_y)], fill=(45, 48, 65), width=2)
    
    copyright_text = "© न्यूज़ फ़्लैश 5. सर्वाधिकार सुरक्षित।" if lang == "hi" else "© NEWS FLASH 5. ALL RIGHTS RESERVED."
    center_x(draw, footer_y + 36, copyright_text, F(24, True, lang=lang), (90, 95, 110), width)
    
    canvas.save(path, "JPEG", quality=96)
    return path


def digest_cover_slide(articles, path, lang="en"):
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
        
        # Base darkness 140. Edges push towards 255.
        base_alpha = 140
        # Make the bottom edge darker than the top edge
        edge_boost = 115 * (ny ** 2) if ny < 0 else 115 * (ny ** 1.5)
        
        alpha = int(min(255, base_alpha + edge_boost))
        
        # Premium dark blue/purple tint towards the bottom
        draw_ov.line([(0, y), (width, y)], fill=(12, 13, 22, alpha))
        
    canvas = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(canvas)
    
    # Header
    draw_brand_header(canvas, width, label="NEWS", transparent=True)
    draw = ImageDraw.Draw(canvas)
    
    accent_color = (255, 195, 0) # Gold Accent
    
    # Top Right Badge: "BREAKING NEWS | • LIVE"
    badge_x = width - 260
    badge_y = 50
    # Red Top Half
    draw.rectangle([badge_x, badge_y, badge_x + 220, badge_y + 45], fill=C["red"])
    t1 = "ब्रेकिंग" if lang == "hi" else "BREAKING"
    w1 = draw.textbbox((0,0), t1, font=F(28, True, lang=lang))[2]
    draw.text((badge_x + (220 - w1)//2, badge_y + 5), t1, font=F(28, True, lang=lang), fill=C["white"])
    # White Bottom Half
    draw.rectangle([badge_x, badge_y + 45, badge_x + 220, badge_y + 90], fill=C["white"])
    t2 = "न्यूज़" if lang == "hi" else "NEWS"
    w2 = draw.textbbox((0,0), t2, font=F(36, True, lang=lang))[2]
    draw.text((badge_x + (220 - w2)//2, badge_y + 45), t2, font=F(36, True, lang=lang), fill=(0, 0, 0))
    # Live Pill
    draw.rounded_rectangle([badge_x + 130, badge_y + 100, badge_x + 220, badge_y + 135], radius=15, fill=C["red"])
    live_label = "• लाइव" if lang == "hi" else "• LIVE"
    draw.text((badge_x + 145, badge_y + 102), live_label, font=F(22, True, lang=lang), fill=C["white"])

    # Font Awesome Setup
    fa_font = ImageFont.truetype("assets/fa-solid-900.ttf", 45)
    
    # Draw massive centered text: "5 BIG STORIES IN 60 SECONDS"
    title_y = 200
    
    font_5 = F(480, True, impact=True, lang=lang)
    w5 = draw.textbbox((0,0), "5", font=font_5)[2]
    
    big_text = "बड़ी" if lang == "hi" else "BIG"
    font_big = F(140, True, impact=True, lang=lang)
    w_big = draw.textbbox((0,0), big_text, font=font_big)[2]
    
    stories_text = "खबरें" if lang == "hi" else "STORIES"
    font_stories = F(140, True, impact=True, lang=lang)
    w_stories = draw.textbbox((0,0), stories_text, font=font_stories)[2]
    
    gap = 20
    motion_w = 160
    block_width = w5 + gap + max(w_big, w_stories) + motion_w
    start_x = (width - block_width) // 2
    
    # Draw "5"
    draw.text((start_x, title_y - 20), "5", font=font_5, fill=C["white"])
    
    # Draw "BIG"
    right_x = start_x + w5 + gap
    draw.text((right_x, title_y + 40), big_text, font=font_big, fill=C["white"])
    
    # Draw "STORIES"
    draw.text((right_x, title_y + 170), stories_text, font=font_stories, fill=accent_color)
    
    # Motion lines extending from STORIES
    line_x = right_x + w_stories + 40
    line_y_base = title_y + 170
    draw.line([(line_x, line_y_base + 60), (line_x + 160, line_y_base + 60)], fill=C["red"], width=10)
    draw.line([(line_x, line_y_base + 90), (line_x + 200, line_y_base + 90)], fill=C["red"], width=10)
    draw.line([(line_x, line_y_base + 120), (line_x + 180, line_y_base + 120)], fill=C["red"], width=10)
    
    # "IN 60 SECONDS" (Red slanted block)
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
    ], fill=C["red"])
    
    font_60 = F(70, True, impact=True, lang=lang)
    # Text inside block (order changes for clean Hindi grammar)
    if lang == "hi":
        draw.text((block_x + 100, block_y + 10), "60", font=font_60, fill=accent_color)
        draw.text((block_x + 195, block_y + 10), "सेकंड", font=font_60, fill=C["white"])
        draw.text((block_x + 395, block_y + 10), "में", font=font_60, fill=C["white"])
    else:
        draw.text((block_x + 60, block_y + 10), "IN", font=font_60, fill=C["white"])
        draw.text((block_x + 135, block_y + 10), "60", font=font_60, fill=accent_color)
        draw.text((block_x + 235, block_y + 10), "SECONDS", font=font_60, fill=C["white"])
    
    # Divider: FAST . FACTUAL . ESSENTIAL
    div_y = block_y + 130
    
    font_div = F(32, True, lang=lang)
    w_fast = draw.textbbox((0,0), "तेज़" if lang == "hi" else "FAST", font=font_div)[2]
    w_factual = draw.textbbox((0,0), "सटीक" if lang == "hi" else "FACTUAL", font=font_div)[2]
    w_essential = draw.textbbox((0,0), "ज़रूरी" if lang == "hi" else "ESSENTIAL", font=font_div)[2]
    w_dot = draw.textbbox((0,0), ".", font=font_div)[2]
    gap_div = 20
    
    total_div_w = w_fast + gap_div + w_dot + gap_div + w_factual + gap_div + w_dot + gap_div + w_essential
    dx = (width - total_div_w) // 2
    
    draw.text((dx, div_y), "तेज़" if lang == "hi" else "FAST", font=font_div, fill=C["white"])
    dx += w_fast + gap_div
    draw.text((dx, div_y - 6), ".", font=font_div, fill=C["red"])
    dx += w_dot + gap_div
    draw.text((dx, div_y), "सटीक" if lang == "hi" else "FACTUAL", font=font_div, fill=C["white"])
    dx += w_factual + gap_div
    draw.text((dx, div_y - 6), ".", font=font_div, fill=C["red"])
    dx += w_dot + gap_div
    draw.text((dx, div_y), "ज़रूरी" if lang == "hi" else "ESSENTIAL", font=font_div, fill=C["white"])
    
    # Draw exact lines
    draw.line([((width - total_div_w)//2 - 120, div_y + 20), ((width - total_div_w)//2 - 20, div_y + 20)], fill=C["white"], width=3)
    draw.line([(dx + w_essential + 20, div_y + 20), (dx + w_essential + 120, div_y + 20)], fill=C["white"], width=3)
    
    # 5 Circles Row
    circle_y = div_y + 80
    circle_r = 45
    spacing = 180
    start_x = width//2 - int(2 * spacing)
    if lang == "hi":
        labels = ["वैश्विक\nखबरें", "राजनीति\nऔर शासन", "देश की\nअर्थव्यवस्था", "लोग और\nसमाज", "अन्य मुख्य\nखबरें"]
    else:
        labels = ["GLOBAL\nUPDATES", "POLITICS &\nGOVERNANCE", "ECONOMY\nIN FOCUS", "PEOPLE &\nSOCIETY", "MORE STORIES\nINSIDE"]
    icons = ["\uf0ac", "\uf19c", "\uf201", "\uf0c0", "\uf0a1"]
    
    for i in range(5):
        cx = start_x + i * spacing
        draw.ellipse([cx - circle_r, circle_y, cx + circle_r, circle_y + circle_r*2], outline=C["red"], width=6)
        draw.ellipse([cx - circle_r + 4, circle_y + 4, cx + circle_r - 4, circle_y + circle_r*2 - 4], outline=C["white"], width=2)
        
        icon_str = icons[i]
        icon_w = draw.textbbox((0,0), icon_str, font=fa_font)[2]
        draw.text((cx - icon_w//2, circle_y + 20), icon_str, font=fa_font, fill=C["white"])
        
        if i < 4:
            draw.line([(cx + spacing//2, circle_y + 10), (cx + spacing//2, circle_y + 90)], fill=(100, 100, 100, 180), width=2)
            
        lines = labels[i].split('\n')
        for idx, lbl_line in enumerate(lines):
            lw = draw.textbbox((0,0), lbl_line, font=F(18, True, lang=lang))[2]
            draw.text((cx - lw//2, circle_y + 105 + idx*22), lbl_line, font=F(18, True, lang=lang), fill=C["white"])
            
    # Engagement Hook Block: WAIT TILL YOU SEE...
    hook_y = circle_y + 180
    hook_w = 700
    hook_h = 100
    hook_x = (width - hook_w) // 2
    
    draw.rounded_rectangle([hook_x, hook_y, hook_x + hook_w, hook_y + hook_h], radius=15, fill=(10, 11, 16, 200), outline=accent_color, width=4)
    
    fa_clock = "\uf2f2"
    fa_clock_font = ImageFont.truetype("assets/fa-solid-900.ttf", 60)
    draw.text((hook_x + 40, hook_y + 20), fa_clock, font=fa_clock_font, fill=accent_color)
    
    hook_text_1 = translate_to_hindi("WAIT TILL YOU SEE") if lang == "hi" else "WAIT TILL YOU SEE"
    hook_text_2 = translate_to_hindi("THE LAST ONE...") if lang == "hi" else "THE LAST ONE..."
    font_h1 = F(32, True, lang=lang)
    font_h2 = F(36, True, impact=True, lang=lang)
    draw.text((hook_x + 130, hook_y + 15), hook_text_1, font=font_h1, fill=C["white"])
    draw.text((hook_x + 130, hook_y + 50), hook_text_2, font=font_h2, fill=accent_color)
    
    fa_angles = "\uf101"
    draw.text((hook_x + 600, hook_y + 25), fa_angles, font=fa_clock_font, fill=accent_color)

    # Footer Date
    footer_y = 1170
    date_str = datetime.now().strftime('%d %b %Y   |   %H:%M')
    fa_cal = "\uf133"
    cal_w = draw.textbbox((0,0), fa_cal, font=F(24, True, lang=lang))[2]
    footer_label = "अपडेटेड" if lang == "hi" else "UPDATED"
    footer_text = f"{footer_label}: {date_str.upper()}"
    ft_w = draw.textbbox((0,0), footer_text, font=F(24, True, lang=lang))[2]
    total_w = cal_w + 10 + ft_w
    fx = (width - total_w) // 2
    
    fa_small = ImageFont.truetype("assets/fa-solid-900.ttf", 24)
    draw.text((fx, footer_y), fa_cal, font=fa_small, fill=C["red"])
    draw.text((fx + cal_w + 10, footer_y), footer_text, font=F(24, True, lang=lang), fill=(200, 200, 200))
    
    # Premium Swipe Button (Bottom CTA)
    btn_w, btn_h = 600, 75
    btn_x, btn_y = (width - btn_w) // 2, 1220
    draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=40, fill=accent_color)
    
    btn_text = translate_to_hindi("WATCH FULL BREAKDOWN") if lang == "hi" else "WATCH FULL BREAKDOWN"
    btn_font = F(32, True, lang=lang)
    text_w = draw.textbbox((0,0), btn_text, font=btn_font)[2]
    btn_content_w = text_w + 20 + draw.textbbox((0,0), fa_angles, font=btn_font)[2]
    bx = btn_x + (btn_w - btn_content_w) // 2
    
    # Use dark background text on gold button for premium contrast!
    draw.text((bx, btn_y + 20), btn_text, font=btn_font, fill=C["dark_bg"])
    
    fa_mid = ImageFont.truetype("assets/fa-solid-900.ttf", 32)
    draw.text((bx + text_w + 20, btn_y + 20), fa_angles, font=fa_mid, fill=C["dark_bg"])

    canvas.save(path, "JPEG", quality=96)
    return path


def digest_story_slide(article, path, index, total, lang="en"):
    width, height = 1080, 1350
    print(f"    Slide {index + 1} - DIGEST STORY ({lang.upper()})...")
    
    if lang == "hi":
        headline_text = article.get("ai_title_hindi") or article.get("ai_title") or slide_headline(article, max_chars=120)
        summary_text = article.get("ai_summary_hindi") or article.get("ai_summary") or slide_summary(article, max_chars=350)
        label_text = translate_to_hindi(story_label(article))
        handle_text = f"{PAGE_HANDLE}.hindi"
        swipe_text = translate_to_hindi("Swipe for next update →") if index < total else "खबरें समाप्त"
        source_label = "स्रोत"
        highlights_label = "मुख्य झलकियां"
    else:
        headline_text = article.get("ai_title") or slide_headline(article, max_chars=120)
        summary_text = article.get("ai_summary") or slide_summary(article, max_chars=350)
        label_text = story_label(article)
        handle_text = PAGE_HANDLE
        swipe_text = "Swipe for next update →" if index < total else "End of Hourly Digest"
        source_label = "Source"
        highlights_label = "KEY HIGHLIGHTS"
    
    # Base Image (Zoomed to perfectly fill the vertical canvas)
    base_img = get_photo(article, width, height, seed_offset=200 + index * 70, fit=True)
    
    # Cinematic Vignette Overlay (Dark left and bottom for text readability)
    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    # Overall subtle dimming to ensure text pops
    draw_ov.rectangle([0, 0, width, height], fill=(12, 13, 20, 80))
    
    # Heavy left gradient for the massive headline and summary box
    fade_w = int(width * 0.75)
    for x in range(fade_w):
        alpha = int(220 * (1 - (x / fade_w)))
        draw_ov.line([(x, 0), (x, height)], fill=(10, 11, 16, alpha))
        
    # Heavy bottom gradient for the page counter
    fade_h_start = int(height * 0.75)
    for y in range(fade_h_start, height):
        alpha = int(240 * ((y - fade_h_start) / (height - fade_h_start)))
        draw_ov.line([(0, y), (width, y)], fill=(10, 11, 16, alpha))
        
    # Composite vignette overlay onto base image
    canvas = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(canvas)
    
    # Transparent Header
    draw_brand_header(canvas, width, label=label_text, transparent=True)
    draw = ImageDraw.Draw(canvas)
    
    # Accent color based on category
    category_name = article.get("category", "WORLD").upper()
    accent_color = get_category_color(category_name)
    
    # Date & Category Pill
    pill_y = 160
    date_str = article.get("ai_date") or datetime.now().strftime('%d %b %Y')
    draw.text((60, pill_y + 5), date_str.upper(), font=F(28, False, lang=lang), fill=C["offwhite"])
    draw.line([(240, pill_y), (240, pill_y + 40)], fill=(100, 100, 100), width=2)
    
    display_category = translate_to_hindi(category_name) if lang == "hi" else category_name
    cat_w = draw.textbbox((0, 0), display_category, font=F(28, True, lang=lang))[2]
    draw.rounded_rectangle([260, pill_y, 260 + cat_w + 30, pill_y + 40], radius=8, fill=accent_color)
    draw.text((275, pill_y + 5), display_category, font=F(28, True, lang=lang), fill=C["white"])
    
    # Huge Left-Aligned Headline (Mixed case is much more premium!)
    title_y = 230
    title_font = F(72, True, lang=lang)
    title_font_sm = F(54, True, lang=lang)
    
    # Split headline if it has an accent divider
    full_headline = headline_text
    
    # Find separator
    sep = None
    for s in [" — ", " - ", " : ", ": "]:
        if s in full_headline:
            sep = s
            break
            
    if sep:
        part1, part2 = full_headline.split(sep, 1)
        part1 = part1.strip()
        part2 = part2.strip()
        
        # Wrapped title blocks
        wrapped_p1 = textwrap.wrap(part1, width=22)[:2]
        wrapped_p2 = textwrap.wrap(part2, width=28)[:2]
        
        headline_lines = [(line, title_font, C["white"]) for line in wrapped_p1]
        headline_lines.append(("-divider-", None, None))
        headline_lines.extend([(line, title_font_sm, accent_color) for line in wrapped_p2])
    else:
        wrapped_title = textwrap.wrap(full_headline, width=22)[:3]
        headline_lines = [(line, title_font, C["white"] if idx == 0 else accent_color if idx == 1 else C["offwhite"]) for idx, line in enumerate(wrapped_title)]
        
    # Draw frosted glass behind headline lines
    panel_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel_layer)
    _ty = title_y
    for line, font, color in headline_lines:
        if line == "-divider-":
            _ty += 16
            continue
        lw = draw.textbbox((0, 0), line, font=font)[2]
        lh = draw.textbbox((0, 0), line, font=font)[3]
        panel_draw.rounded_rectangle([50, _ty - 4, 50 + lw + 24, _ty + lh + 6], radius=6, fill=(10, 11, 16, 140))
        _ty += lh + 14
        
    canvas = Image.alpha_composite(canvas.convert("RGBA"), panel_layer).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    
    # Draw actual text on top
    _ty = title_y
    for line, font, color in headline_lines:
        if line == "-divider-":
            draw.line([(60, _ty + 6), (380, _ty + 6)], fill=accent_color, width=4)
            _ty += 16
            continue
        # Shadow
        draw.text((62, _ty + 2), line, font=font, fill=(0, 0, 0))
        draw.text((60, _ty), line, font=font, fill=color)
        _ty += draw.textbbox((0, 0), line, font=font)[3] + 14
        
    # Draw vertical accent border along the headline block
    draw.rectangle([44, title_y, 48, _ty - 12], fill=accent_color)
    
    # 7. Summary Intro Paragraph
    summary_y = _ty + 16
    
    if article.get("ai_rewritten"):
        intro_text = summary_text
        if lang == "hi":
            bullets = article.get("ai_highlights_hindi", [])[:3] or article.get("ai_highlights", [])[:3]
        else:
            bullets = article.get("ai_highlights", [])[:3]
    else:
        # Split using Devanagari danda also
        sentences = [s.strip() for s in re.split(r'[.!?।]', summary_text) if len(s.strip()) > 15]
        if len(sentences) > 1:
            intro_text = sentences[0] + ("।" if lang == "hi" else ".")
            bullets = sentences[1:4]
        else:
            clauses = [c.strip() for c in re.split(r'[,;]\s+', summary_text) if len(c.strip()) > 15]
            if len(clauses) > 1:
                intro_text = clauses[0] + ","
                bullets = clauses[1:4]
            else:
                intro_text = "ताज़ा जानकारी:" if lang == "hi" else "Latest developments on this story:"
                bullets = [summary_text]
                
    summary_lines = textwrap.wrap(intro_text, width=44)[:4]
    
    # Frosted glass panel for summary lines
    summary_panel_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    summary_panel_draw = ImageDraw.Draw(summary_panel_layer)
    _sy = summary_y
    for line in summary_lines:
        lw = draw.textbbox((0, 0), line, font=F(36, False, lang=lang))[2]
        lh = draw.textbbox((0, 0), line, font=F(36, False, lang=lang))[3]
        summary_panel_draw.rounded_rectangle([50, _sy - 4, 50 + lw + 24, _sy + lh + 4], radius=6, fill=(10, 11, 16, 130))
        _sy += lh + 12
    canvas = Image.alpha_composite(canvas.convert("RGBA"), summary_panel_layer).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    
    # Draw summary text
    _sy = summary_y
    for line in summary_lines:
        draw.text((61, _sy + 1), line, font=F(36, False, lang=lang), fill=(0, 0, 0))
        draw.text((60, _sy), line, font=F(36, False, lang=lang), fill=C["offwhite"])
        _sy += draw.textbbox((0, 0), line, font=F(36, False, lang=lang))[3] + 12
        
    # 8. Key Highlights Box (Premium and dynamic)
    summary_y = _sy + 30
    box_w = 780
    
    wrapped_bullets_list = []
    box_h = 80
    for bullet in bullets:
        b_text = shorten(bullet, 100)
        wrapped_b = textwrap.wrap(b_text, width=42)
        wrapped_bullets_list.append(wrapped_b)
        box_h += len(wrapped_b) * 42
    box_h += (len(bullets) - 1) * 20 + 20
    
    # Outer highlights box container
    draw.rounded_rectangle([60, summary_y, 60 + box_w, summary_y + box_h], radius=16, fill=(15, 17, 26, 190), outline=(45, 48, 65), width=2)
    
    # Highlights label tag pill
    hl_w = draw.textbbox((0, 0), highlights_label, font=F(26, True, lang=lang))[2]
    draw.rounded_rectangle([60, summary_y, 60 + hl_w + 40, summary_y + 50], radius=12, fill=accent_color)
    draw.text((80, summary_y + 10), highlights_label, font=F(26, True, lang=lang), fill=C["white"])
    
    bullet_y = summary_y + 76
    for idx, wrapped_b in enumerate(wrapped_bullets_list):
        # Bullet dot in accent color
        draw.ellipse([85, bullet_y + 12, 97, bullet_y + 24], fill=accent_color)
        for line in wrapped_b:
            draw.text((120, bullet_y), line, font=F(32, False, lang=lang), fill=C["offwhite"])
            bullet_y += 42
        if idx < len(bullets) - 1:
            draw.line([(80, bullet_y + 8), (60 + box_w - 30, bullet_y + 8)], fill=(45, 48, 65), width=2)
        bullet_y += 20
        
    # 9. Clean transparent footer matching other slides
    footer_y = 1200
    draw.line([(60, footer_y), (width - 60, footer_y)], fill=(45, 48, 65), width=2)
    
    paste_logo(canvas, 60, footer_y + 20, size=60)
    draw = ImageDraw.Draw(canvas)
    draw.text((134, footer_y + 32), handle_text, font=F(32, True, lang=lang), fill=C["white"])
    
    swipe_text = translate_to_hindi("Swipe for next update →") if index < total else ("खबरें समाप्त" if lang == "hi" else "End of Hourly Digest")
    sw_w = draw.textbbox((0, 0), swipe_text, font=F(28, True, lang=lang))[2]
    draw.text((width - 60 - sw_w, footer_y + 34), swipe_text, font=F(28, True, lang=lang), fill=accent_color)
    
    ai_tag = "एआई प्रस्तुति" if lang == "hi" else "AI ASSISTED"
    source_line = f"{source_label}: {display_source(article['source'])}  |  {ai_tag}  |  Slide {index} of {total}"
    draw.text((60, footer_y + 94), source_line.upper(), font=F(24, True, lang=lang), fill=(100, 105, 120))
    
    canvas.save(path, "JPEG", quality=96)
    return path


def create_carousel(article, prefix=None, lang="en"):
    timestamp = datetime.now().strftime("%H%M%S%f")[:10]
    prefix = prefix or f"{article['category'].lower()}_{timestamp}"
    print(f"\n  Story carousel: {article['title'][:55]}... ({lang.upper()})")
    paths = [
        OUTPUT_DIR / f"{prefix}_1_main.jpg",
        OUTPUT_DIR / f"{prefix}_2_facts.jpg",
        OUTPUT_DIR / f"{prefix}_3_visual.jpg",
        OUTPUT_DIR / f"{prefix}_4_cta.jpg",
    ]
    slide1_main(article, str(paths[0]), lang=lang)
    slide2_facts(article, str(paths[1]), lang=lang)
    slide3_visual(article, str(paths[2]), lang=lang)
    slide4_cta(article, str(paths[3]), lang=lang)
    print("  4 slides saved")
    return [str(path) for path in paths]


def create_single(article, prefix=None, lang="en"):
    timestamp = datetime.now().strftime("%H%M%S%f")[:10]
    prefix = prefix or f"{article['category'].lower()}_{timestamp}"
    path = OUTPUT_DIR / f"{prefix}_breaking.jpg"
    print(f"\n  Single post: {article['title'][:55]}... ({lang.upper()})")
    slide1_main(article, str(path), lang=lang)
    print("  Saved")
    return str(path)


def create_digest_carousel(articles, prefix=None, lang="en"):
    timestamp = datetime.now().strftime("%H%M%S%f")[:10]
    prefix = prefix or f"digest_{timestamp}"
    print(f"\n  Hourly digest carousel with {len(articles)} stories ({lang.upper()})")
    paths = [OUTPUT_DIR / f"{prefix}_1_cover.jpg"]
    for index in range(len(articles)):
        paths.append(OUTPUT_DIR / f"{prefix}_{index + 2}_story.jpg")

    digest_cover_slide(articles, str(paths[0]), lang=lang)
    for index, article in enumerate(articles, start=1):
        digest_story_slide(article, str(paths[index]), index, len(articles), lang=lang)

    print(f"  {len(paths)} digest slides saved")
    return [str(path) for path in paths]
