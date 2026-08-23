from config import GROQ_KEY, GROQ_MODEL, PAGE_HANDLE
from news_utils import clean_story_summary, clean_story_title, display_source

HASHTAGS = {
    "INDIA": "#India #IndiaNews #BreakingIndia #IndianNews #NationalNews",
    "WORLD": "#WorldNews #BreakingNews #GlobalNews #International #WorldUpdate",
    "BUSINESS": "#Business #Economy #Finance #StockMarket #Markets",
    "TECH": "#Technology #Tech #AI #Innovation #TechNews",
    "SPORTS": "#Sports #Cricket #Football #SportsNews #TeamIndia",
    "ENTERTAINMENT": "#Entertainment #Movies #Celebrity #FilmNews #Bollywood",
    "POLITICS": "#Politics #Government #Elections #IndiaPolitics #Policy",
    "SCIENCE": "#Science #ISRO #Space #Research #Innovation",
    "FINANCE": "#Finance #Crypto #Investment #Money #Wealth #StockMarket",
    "STARTUPS": "#Startups #Entrepreneur #Founders #StartupIndia #VentureCapital",
    "CRIME": "#CrimeNews #LawAndOrder #Justice #IndiaCrime #Investigation",
    "EDUCATION": "#Education #Students #University #Exams #Career",
    "CAREERS": "#Jobs #Employment #Career #Hiring #Workplace",
    "DIGEST": "#IndiaNews #WorldNews #BreakingNews #TopStories #DailyDigest",
}

COMMON_TAGS = (
    "#NewsFlash5 #LatestNews #NewsUpdate #LiveNews #NewsAlert "
    "#TrendingNow #HeadlineNews #TopNews #IndiaAndWorld #HourlyNews"
)


def generate_caption(payload, lang="en"):
    if lang == "hi":
        if isinstance(payload, dict) and payload.get("type") == "digest":
            return _template_digest_caption_hindi(payload)
        return _template_story_caption_hindi(payload)

    if isinstance(payload, dict) and payload.get("type") == "digest":
        if GROQ_KEY and "YOUR_" not in GROQ_KEY:
            caption = _groq_digest_caption(payload)
            if caption:
                return caption
        return _template_digest_caption(payload)

    if GROQ_KEY and "YOUR_" not in GROQ_KEY:
        caption = _groq_story_caption(payload)
        if caption:
            return caption
    return _template_story_caption(payload)


def _groq_digest_caption(payload):
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_KEY)
        article_lines = "\n".join(
            f"{index}. [{article['category']}] {clean_story_title(article['title'], article.get('source', ''))} - "
            f"{clean_story_summary(article.get('summary', ''), article['title'], article.get('source', ''))[:140]}"
            for index, article in enumerate(payload["articles"], start=1)
        )
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are a professional social media strategist for an Instagram news page.
Your goal is to write a highly engaging, viral-ready Instagram caption for our hourly news digest.

Stories in this digest:
{article_lines}

Write the Instagram caption following these STRICT rules:
1. First line MUST be an attention-grabbing hook (NOT robotic, NO ALL CAPS).
2. Follow with a short engaging explanation of the top stories.
3. List the headlines of the 5 stories clearly so readers know what's in the carousel.
4. End with an engaging question to increase comments and interaction.
5. Add exactly 5–8 relevant hashtags (including #newsflash5).

TONE: Professional but engaging. Easy to understand (like a modern news app).
Do not include any JSON or markdown formatting, just return the raw caption text ready for Instagram.
""",
                }
            ],
            max_tokens=550,
        )
        caption = response.choices[0].message.content.strip()
        print("    AI digest caption generated")
        return caption
    except Exception as exc:
        print(f"    Groq digest error: {exc}")
        return None


def _groq_story_caption(article):
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""
You write Instagram captions for News Flash 5 ({PAGE_HANDLE}).
Headline: {article['title']}
Summary: {article['summary']}
Category: {article['category']}
Source: {display_source(article['source'])}

Write a concise factual caption with:
1. One strong hook line.
2. Two short summary sentences.
3. Source line.
4. Follow CTA.
5. 15-20 relevant hashtags including #newsflash5.
""",
                }
            ],
            max_tokens=350,
        )
        caption = response.choices[0].message.content.strip()
        print("    AI story caption generated")
        return caption
    except Exception as exc:
        print(f"    Groq story error: {exc}")
        return None


def _template_digest_caption(payload):
    lines = [
        "TOP 5 NEWS THIS HOUR",
        "",
        "India + world stories picked for speed, relevance, and interaction.",
        "",
    ]
    categories = set()
    for index, article in enumerate(payload["articles"], start=1):
        title = clean_story_title(article["title"], article.get("source", ""))
        lines.append(f"{index}. {title} ({display_source(article['source'])})")
        categories.add(article.get("category", "WORLD").upper())

    # Build dynamic hashtags based on article categories
    dynamic_tags_list = []
    for cat in categories:
        if cat in HASHTAGS:
            dynamic_tags_list.extend(HASHTAGS[cat].split())
            
    unique_tags = []
    for tag in dynamic_tags_list:
        if tag not in unique_tags:
            unique_tags.append(tag)
            
    for tag in HASHTAGS["DIGEST"].split() + COMMON_TAGS.split():
        if tag not in unique_tags:
            unique_tags.append(tag)
            
    tags_str = " ".join(unique_tags[:15])

    lines.extend(
        [
            "",
            "💬 Which of these 5 stories is the most important to you? Let us know in the comments below! 👇",
            "",
            f"Follow {PAGE_HANDLE} for hourly India + international updates, fast explainers, and breaking alerts.",
            "",
            tags_str,
        ]
    )
    return "\n".join(lines)


def _template_story_caption(article):
    category = article.get("category", "WORLD")
    tags = HASHTAGS.get(category, "") + " " + COMMON_TAGS
    title = clean_story_title(article["title"], article.get("source", ""))
    summary = clean_story_summary(article.get("summary", ""), article["title"], article.get("source", ""))
    return (
        f"{title.upper()[:90]}\n\n"
        f"{summary[:240]}\n\n"
        f"Source: {display_source(article['source'])}\n"
        f"Follow {PAGE_HANDLE} for hourly India + world news updates.\n\n"
        f"💬 What are your thoughts on this? Let us know in the comments below! 👇\n\n"
        f"{tags}"
    )


def _template_digest_caption_hindi(payload):
    from image_maker import translate_to_hindi
    lines = [
        "इस घंटे की 5 बड़ी खबरें",
        "",
        "देश और दुनिया की ताज़ा एवं सटीक खबरें सबसे पहले।",
        "",
    ]
    for index, article in enumerate(payload["articles"], start=1):
        title = article.get("ai_title_hindi") or clean_story_title(article["title"], article.get("source", ""))
        source = translate_to_hindi(display_source(article.get('source', '')))
        lines.append(f"{index}. {title} ({source})")

    hindi_tags = "#हिंदीसमाचार #ताज़ाखबर #बड़ीखबरें #समाचार #NewsInHindi #HindiNews #newsflash5 #DailyDigest"
    lines.extend(
        [
            "",
            "💬 इन 5 खबरों में से आपको कौन सी खबर सबसे महत्वपूर्ण लगी? नीचे कमेंट में अपनी राय बताएं! 👇",
            "",
            "ताज़ा और सटीक खबरों के लिए @news.flash5.hindi को फॉलो करें।",
            "",
            hindi_tags,
        ]
    )
    return "\n".join(lines)


def _template_story_caption_hindi(article):
    from image_maker import translate_to_hindi
    title = article.get("ai_title_hindi") or clean_story_title(article["title"], article.get("source", ""))
    summary = article.get("ai_summary_hindi") or clean_story_summary(article.get("summary", ""), article["title"], article.get("source", ""))
    source = translate_to_hindi(display_source(article.get('source', '')))
    
    highlights_lines = ""
    bullets = article.get("ai_highlights_hindi", [])
    if bullets:
        highlights_lines = "\n" + "\n".join(f"• {b}" for b in bullets) + "\n"
        
    hindi_tags = "#हिंदीसमाचार #ताज़ाखबर #बड़ीखबर #समाचार #NewsInHindi #HindiNews #newsflash5"
    
    return (
        f"{title.upper()}\n\n"
        f"{summary}\n"
        f"{highlights_lines}\n"
        f"स्रोत: {source}\n"
        f"ताज़ा और सटीक खबरों के लिए @news.flash5.hindi को फॉलो करें।\n\n"
        f"💬 इस खबर पर आपकी क्या राय है? नीचे कमेंट में बताएं! 👇\n\n"
        f"{hindi_tags}"
    )
