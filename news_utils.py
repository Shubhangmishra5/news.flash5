import re

STOP_WORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and",
    "is", "are", "was", "were", "has", "have", "will", "with",
    "from", "after", "over", "says", "said", "but", "as", "by",
    "its", "be", "this", "that", "into", "amid", "near", "ahead",
}

LOCATION_QUERY_MAP = {
    "india": "india city",
    "delhi": "new delhi skyline",
    "mumbai": "mumbai skyline",
    "kerala": "kerala india",
    "tamil nadu": "tamil nadu india",
    "madurai": "madurai tamil nadu",
    "bengaluru": "bengaluru india",
    "bangalore": "bengaluru india",
    "isro": "isro rocket launch",
    "iran": "iran skyline",
    "israel": "middle east skyline",
    "ukraine": "ukraine city",
    "russia": "moscow skyline",
    "china": "beijing skyline",
    "usa": "washington dc skyline",
    "america": "washington dc skyline",
}

VISUAL_RULES = [
    (["election", "vote", "constituency", "assembly", "parliament", "campaign"], [
        "election campaign india",
        "voting booth india",
        "parliament building",
    ]),
    (["blast", "explosion", "fire", "killed", "crash", "rescue", "emergency"], [
        "emergency response",
        "industrial fire",
        "rescue team",
    ]),
    (["sensex", "nifty", "stock", "market", "economy", "finance", "rbi", "repo"], [
        "stock market india",
        "trading screen",
        "finance office",
    ]),
    (["ai", "technology", "tech", "startup", "software", "digital", "device"], [
        "technology digital",
        "artificial intelligence",
        "modern office tech",
    ]),
    (["iran", "israel", "ukraine", "russia", "china", "usa", "trump", "ceasefire", "war", "missile", "nuclear"], [
        "international diplomacy",
        "world leaders meeting",
        "middle east skyline",
    ]),
    (["space", "moon", "rocket", "nasa", "isro", "science"], [
        "space rocket launch",
        "moon mission",
        "science laboratory",
    ]),
    (["cricket", "ipl", "football", "sports", "stadium", "match"], [
        "cricket stadium",
        "sports action",
        "football stadium",
    ]),
    (["movie", "film", "actor", "actress", "cinema", "bollywood", "celebrity"], [
        "movie theater",
        "film production",
        "bollywood cinema",
    ]),
]

LABEL_RULES = [
    (["election", "vote", "constituency", "assembly", "parliament"], "ELECTION WATCH"),
    (["sensex", "nifty", "stock", "market", "economy", "rbi", "repo"], "MARKET UPDATE"),
    (["blast", "explosion", "fire", "crash", "earthquake", "flood", "cyclone"], "BREAKING ALERT"),
    (["iran", "israel", "ukraine", "russia", "china", "usa", "trump", "war", "ceasefire"], "GLOBAL UPDATE"),
    (["technology", "ai", "startup", "software", "digital"], "TECH WATCH"),
    (["space", "moon", "rocket", "isro", "nasa", "science"], "SCIENCE WATCH"),
    (["cricket", "ipl", "football", "sports"], "SPORTS UPDATE"),
]

SOURCE_ALIASES = {
    "indianexpress.com": "Indian Express",
    "timesofindia.indiatimes.com": "Times of India",
    "economictimes.indiatimes.com": "Economic Times",
    "thehindu.com": "The Hindu",
    "hindustantimes.com": "Hindustan Times",
    "ndtv.com": "NDTV",
    "livemint.com": "Mint",
    "moneycontrol.com": "Moneycontrol",
    "firstpost.com": "Firstpost",
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "cricbuzz.com": "Cricbuzz",
    "financialexpress.com": "Financial Express",
    "inc42.com": "Inc42",
}


def normalize_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _clean_edge_punctuation(text):
    return normalize_whitespace(text).strip(" -|:;,.!?\"'`“”‘’()[]{}")


def _compare_text(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def smart_trim(text, max_chars):
    text = normalize_whitespace(text)
    if len(text) <= max_chars:
        return _clean_edge_punctuation(text)

    clipped = text[: max_chars + 1]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    clipped = clipped.rstrip(" -|:;,.!?\"'`“”‘’([{")
    return _clean_edge_punctuation(clipped) + "..."


def display_source(source):
    source = normalize_whitespace(source)
    if not source:
        return "Trusted source"

    lowered = source.lower()
    for domain, label in SOURCE_ALIASES.items():
        if domain in lowered:
            return label

    cleaned = re.sub(r"^https?://", "", lowered).split("/")[0]
    cleaned = cleaned.replace("www.", "").replace("feeds.", "")
    cleaned = re.sub(r"\.(com|co\.uk|co\.in|in|org|net)$", "", cleaned)
    words = [word for word in re.split(r"[.\-]+", cleaned) if word]
    if not words:
        return source
    return " ".join(word.upper() if len(word) <= 3 else word.capitalize() for word in words)


def clean_story_title(title, source=""):
    title = normalize_whitespace(re.sub(r"<[^>]+>", "", title or ""))
    title = re.sub(r"\s+\|\s+[^|]+(?:\|\s*[\d./-]+)?$", "", title).strip()
    title = re.sub(r"\s*\|\s*[\d./-]+$", "", title).strip()
    title = re.sub(r"\s*\(\w+\)\s*$", "", title).strip()
    if source:
        escaped = re.escape(source.strip())
        title = re.sub(rf"\s*[-|]\s*{escaped}\s*$", "", title, flags=re.IGNORECASE).strip()
    return _clean_edge_punctuation(title)


def clean_story_summary(summary, title="", source=""):
    summary = normalize_whitespace(re.sub(r"<[^>]+>", "", summary or ""))
    summary = re.sub(r"Read more.*$", "", summary, flags=re.IGNORECASE).strip()
    if source:
        summary = re.sub(rf"\s*[-|]\s*{re.escape(source)}\s*$", "", summary, flags=re.IGNORECASE).strip()
    title = clean_story_title(title, source)
    if len(summary) >= 25 and _compare_text(summary) != _compare_text(title):
        return summary

    if ":" in title:
        left, right = [part.strip() for part in title.split(":", 1)]
        if right:
            return f"{left} update: {right}."
    if title:
        return f"More verified details are emerging from {display_source(source)}."
    return summary or "Latest update from trusted sources."


def _keyword_terms(text):
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def build_visual_queries(article):
    title = clean_story_title(article.get("title", ""), article.get("source", ""))
    summary = clean_story_summary(article.get("summary", ""), title, article.get("source", ""))
    category = (article.get("category") or "WORLD").upper()
    haystack = f"{title} {summary}".lower()
    queries = []

    for phrase, mapped in LOCATION_QUERY_MAP.items():
        if phrase in haystack:
            queries.append(mapped)

    for keywords, mapped_queries in VISUAL_RULES:
        if any(keyword in haystack for keyword in keywords):
            queries.extend(mapped_queries)

    keyword_query = " ".join(_keyword_terms(title)[:4]).strip()
    if keyword_query:
        queries.append(keyword_query)

    category_defaults = {
        "INDIA": ["india city", "india parliament"],
        "WORLD": ["world politics", "international news"],
        "BUSINESS": ["stock market", "finance office"],
        "TECH": ["technology digital", "modern office tech"],
        "SPORTS": ["sports action", "cricket stadium"],
        "ENTERTAINMENT": ["movie theater", "concert stage"],
        "POLITICS": ["parliament building", "government meeting"],
        "SCIENCE": ["science laboratory", "space rocket launch"],
    }
    queries.extend(category_defaults.get(category, [category.lower(), "news background"]))

    deduped = []
    seen = set()
    for query in queries:
        normalized = normalize_whitespace(query.lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(query)
    return deduped[:8]


def story_label(article):
    title = clean_story_title(article.get("title", ""), article.get("source", ""))
    summary = clean_story_summary(article.get("summary", ""), title, article.get("source", ""))
    haystack = f"{title} {summary}".lower()
    for keywords, label in LABEL_RULES:
        if any(keyword in haystack for keyword in keywords):
            return label
    return f"{(article.get('category') or 'NEWS').upper()} UPDATE"


def slide_headline(article, max_chars=120):
    title = clean_story_title(article.get("title", ""), article.get("source", ""))
    return smart_trim(title, max_chars)


def slide_summary(article, max_chars=170):
    summary = clean_story_summary(article.get("summary", ""), article.get("title", ""), article.get("source", ""))
    return smart_trim(summary, max_chars)
