import re
import sys
from html import unescape
from datetime import datetime, timezone, timedelta
from time import mktime

import feedparser
import requests

from config import DIGEST_INDIA_COUNT, DIGEST_WORLD_COUNT, GNEWS_KEY, NEWSAPI_KEY


def _configure_console():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except ValueError:
                pass


_configure_console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

RSS_FEEDS = {
    "INDIA": [
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://indianexpress.com/section/india/feed/",
        "https://www.ndtv.com/rss/2012",
        "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    ],
    "WORLD": [
        "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
        "https://www.thehindu.com/news/international/feeder/default.rss",
        "https://indianexpress.com/section/world/feed/",
        "https://www.firstpost.com/rss/world.xml",
    ],
    "BUSINESS": [
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "https://www.thehindu.com/business/feeder/default.rss",
        "https://www.financialexpress.com/feed/",
        "https://www.moneycontrol.com/rss/latestnews.xml",
        "https://www.livemint.com/rss/news",
    ],
    "TECH": [
        "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
        "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
        "https://www.firstpost.com/rss/tech.xml",
        "https://inc42.com/feed/",
    ],
    "SPORTS": [
        "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
        "https://www.thehindu.com/sport/feeder/default.rss",
        "https://indianexpress.com/section/sports/feed/",
        "https://www.cricbuzz.com/rss-feeds/5/rss.xml",
    ],
    "ENTERTAINMENT": [
        "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms",
        "https://indianexpress.com/section/entertainment/feed/",
        "https://www.firstpost.com/rss/entertainment.xml",
        "https://bollywoodhungama.com/rss/news.xml",
    ],
    "POLITICS": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://indianexpress.com/section/political-pulse/feed/",
        "https://theprint.in/feed/",
    ],
    "SCIENCE": [
        "https://www.thehindu.com/sci-tech/science/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeeds/2886704.cms",
    ],
    "FINANCE": [
        "https://economictimes.indiatimes.com/wealth/rssfeeds/83711893.cms",
        "https://www.moneycontrol.com/rss/cryptocurrency.xml",
        "https://www.livemint.com/rss/money",
    ],
    "STARTUPS": [
        "https://economictimes.indiatimes.com/tech/startups/rssfeeds/101831838.cms",
        "https://yourstory.com/feed",
    ],
    "CRIME": [
        "https://timesofindia.indiatimes.com/rssfeeds/8728059.cms",
        "https://indianexpress.com/section/india/crime/feed/",
    ],
    "EDUCATION": [
        "https://timesofindia.indiatimes.com/rssfeeds/913168846.cms",
        "https://indianexpress.com/section/education/feed/",
    ],
    "CAREERS": [
        "https://economictimes.indiatimes.com/jobs/rssfeeds/107115.cms",
    ],
}

BREAKING_KW = [
    "breaking", "just in", "urgent", "killed", "dead", "dies", "earthquake",
    "explosion", "attack", "blast", "crash", "war", "ceasefire", "arrested",
    "resigned", "wins", "elected", "rbi rate", "repo rate", "sensex crash",
    "modi", "rahul gandhi", "nuclear", "fire", "flood", "storm", "cyclone",
    "verdict", "acquitted", "protest", "riot", "strike", "coup", "missile",
    "trump", "invasion", "terror", "bomb", "shoot", "hostage", "emergency",
]

FAKE_KW = [
    "you won't believe", "shocking!", "omg", "wtf", "100% confirmed",
    "they don't want you", "secret revealed", "mind blowing",
]

BIG_NAMES = [
    "modi", "trump", "rahul gandhi", "elon musk", "rbi", "supreme court",
    "isro", "ipl", "world cup", "pakistan", "china", "usa", "russia", "ukraine",
    "sensex", "nifty", "budget", "election", "parliament", "nasa", "who", "un",
    "imf", "world bank", "g20", "brics", "nato", "israel", "iran", "hamas",
    "putin", "xi jinping", "zelensky", "pope", "king", "queen",
]

TRUSTED = [
    "timesofindia.com", "thehindu.com", "indianexpress.com", "ndtv.com",
    "hindustantimes.com", "economictimes.com", "livemint.com",
    "financialexpress.com", "moneycontrol.com", "firstpost.com",
    "inc42.com", "cricbuzz.com", "bollywoodhungama.com", "theprint.in",
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "news18.com",
]

DIGEST_BONUS = {
    "INDIA": 35,
    "WORLD": 30,
    "POLITICS": 22,
    "BUSINESS": 16,
    "TECH": 14,
    "SCIENCE": 12,
    "SPORTS": 10,
    "ENTERTAINMENT": 8,
}

INDIA_HINTS = [
    "india", "indian", "delhi", "mumbai", "bengaluru", "bangalore", "chennai",
    "kolkata", "hyderabad", "isro", "rbi", "supreme court", "parliament",
    "loksabha", "rajya sabha", "uttar pradesh", "maharashtra", "tamil nadu",
    "karnataka", "bihar", "gujarat", "punjab", "kerala", "modi", "bjp", "congress",
]


def clean(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


ARTICLE_HEADERS = {
    **HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
METADATA_CACHE = {}


def is_breaking(title):
    lowered = title.lower()
    return any(keyword in lowered for keyword in BREAKING_KW)


def trust_score(article):
    score = 0
    url = (article.get("url") or "").lower()
    title = (article.get("title") or "").lower()
    summary = article.get("summary") or ""
    if any(domain in url for domain in TRUSTED):
        score += 40
    if not any(word in title for word in FAKE_KW):
        score += 30
    if len(summary) > 50:
        score += 20
    if url.startswith("http"):
        score += 10
    return score


def trending_score(article):
    score = 0
    title = (article.get("title") or "").lower()
    for name in BIG_NAMES:
        if name in title:
            score += 20
    if re.search(r"\d+", title):
        score += 10
    if 40 < len(title) < 110:
        score += 10
    if article.get("breaking"):
        score += 50
    if article.get("image"):
        score += 8
    return score


def digest_score(article):
    return trending_score(article) + DIGEST_BONUS.get(article.get("category", ""), 0)


def looks_like_india_story(article):
    haystack = " ".join(
        [
            article.get("title", ""),
            article.get("summary", ""),
        ]
    ).lower()
    return any(hint in haystack for hint in INDIA_HINTS)


def _extract_meta_value(html, keys):
    for key in keys:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(key)}["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(key)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return clean(unescape(match.group(1)))
    return ""


def _enrich_from_article_page(article):
    url = article.get("url", "")
    if not url or not url.startswith("http"):
        return article

    needs_image = not article.get("image")
    needs_summary = len(article.get("summary", "")) < 80
    if not needs_image and not needs_summary:
        return article

    if url not in METADATA_CACHE:
        try:
            response = requests.get(url, headers=ARTICLE_HEADERS, timeout=8)
            response.raise_for_status()
            page = response.text[:250000]
            METADATA_CACHE[url] = {
                "image": _extract_meta_value(page, ["og:image", "twitter:image"]),
                "summary": _extract_meta_value(page, ["og:description", "description", "twitter:description"]),
            }
        except Exception:
            METADATA_CACHE[url] = {}

    metadata = METADATA_CACHE.get(url, {})
    if needs_image and metadata.get("image", "").startswith("http"):
        article["image"] = metadata["image"]
    if needs_summary and len(metadata.get("summary", "")) >= 40:
        article["summary"] = metadata["summary"][:320]
    return article


def _ai_rewrite_article(article):
    from config import GROQ_KEY
    if not GROQ_KEY or "YOUR_" in GROQ_KEY:
        return article
        
    try:
        from groq import Groq
        import json
        client = Groq(api_key=GROQ_KEY)
        
        prompt = f"""
You are an elite news editor at a top-tier viral media brand (like NowThis, AajTak, Pubity).
Your job is to transform raw news into highly engaging, scroll-stopping Instagram content.

Raw News:
Headline: {article.get('title')}
Summary: {article.get('summary')}
Category: {article.get('category')}

Rewrite into a STRICT JSON object using these exact rules:

1. "headline": CRITICAL RULE — Write a highly informative 2-PART HEADLINE separated by " — ".
   Part 1 (before " — "): 4-8 words. The WHAT. Must include specific names, places, or numbers (no clickbait mystery). (e.g. "RBI KEEPS REPO RATE AT 6.5%")
   Part 2 (after " — "): 4-8 words. The WHY/IMPACT. Specific context. (e.g. "Home loan EMIs won't change this year")
   Total max 16 words. Factual, highly informative. Never use "This man" or "Here's why".
   Example good headlines:
   - "ISRO CHANDRAYAAN-4 LAUNCHES TODAY — India targets rare dark side moon sample"
   - "APPLE SALES DROP 10% IN CHINA — iPhone loses ground to Huawei's new tech"
   - "BCCI ANNOUNCES T20 WORLD CUP SQUAD — Rohit Sharma returns as captain"

2. "hook": 5-8 words. Scroll-stopper for the cover slide. Creates curiosity or urgency. (e.g. "Nobody saw this coming today")
3. "summary": 2-3 sentences. Clear, factual, non-technical. Tells the story concisely.
4. "highlights": Exactly 3 bullet points. Each adds NEW information, context, or key numbers.
5. "category": One of: Politics, Tech, Business, Sports, World, India, Entertainment, Science.
6. "cta": "Follow @news.flash5 for more updates."
7. "date": Today's date in DD Mon YYYY format.
8. "reel_script": 15-20 second spoken script. Short punchy lines. Hook → Facts → Impact → Close.

TONE: Credible, urgent, informative. NO exaggeration. NO clickbait lies. Factually accurate.
Return ONLY a valid JSON object with keys: headline, hook, summary, highlights, category, cta, date, reel_script.
"""
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=600
        )
        data = json.loads(response.choices[0].message.content)
        
        article["ai_rewritten"] = True
        article["ai_title"] = data.get("headline", article["title"])
        article["ai_hook"] = data.get("hook", "")
        article["ai_summary"] = data.get("summary", article["summary"])
        article["ai_highlights"] = data.get("highlights", [])
        
        # Save Carousel & Reel Data for potential future pipeline usage
        article["ai_carousel"] = [
            data.get("slide_1", ""),
            data.get("slide_2", ""),
            data.get("slide_3", ""),
            data.get("slide_4", ""),
            data.get("slide_5", ""),
        ]
        article["ai_caption"] = data.get("caption", "")
        article["ai_reel_script"] = data.get("reel_script", "")
        
        article["ai_cta"] = data.get("cta", "Follow @news.flash5 for more updates")
        article["ai_date"] = data.get("date", "")
        return article
    except Exception as exc:
        print(f"    AI Rewrite Error: {exc}")
        return article

def hydrate_articles(articles):
    enriched = []
    for article in articles:
        art = _enrich_from_article_page(article)
        art = _ai_rewrite_article(art)
        enriched.append(art)
    return enriched


def dedup_and_rank(articles, score_fn=trending_score):
    stop_words = {
        "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "is",
        "are", "was", "were", "has", "have", "will", "with", "from", "after",
    }

    def keywords(title):
        return {
            word.lower()
            for word in re.findall(r"\b[a-zA-Z]{4,}\b", title)
            if word.lower() not in stop_words
        }

    seen_sets = []
    unique = []
    for article in articles:
        current_words = keywords(article["title"])
        if current_words and any(len(current_words & previous) >= 4 for previous in seen_sets):
            continue
        seen_sets.append(current_words)
        unique.append(article)

    for index, article in enumerate(unique):
        article_words = keywords(article["title"])
        unique[index]["source_count"] = sum(
            1 for other in unique if len(article_words & keywords(other["title"])) >= 3
        )

    unique.sort(key=lambda item: -score_fn(item))
    return unique


def is_recent(pub_date_str, pub_parsed=None, max_hours=6):
    try:
        now = datetime.now(timezone.utc)
        pub_time = None
        if pub_parsed:
            pub_time = datetime.fromtimestamp(mktime(pub_parsed), timezone.utc)
        elif pub_date_str:
            pub_time = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            if pub_time.tzinfo is None:
                pub_time = pub_time.replace(tzinfo=timezone.utc)
                
        if pub_time:
            diff = now - pub_time
            # Bypass filter if system clock is mocked (diff > 30 days or negative)
            if diff < timedelta(0) or diff > timedelta(days=30):
                return True
            return diff <= timedelta(hours=max_hours)
    except Exception:
        pass
    return True


def _newsapi(category, max_hours=6):
    if not NEWSAPI_KEY or "YOUR_" in NEWSAPI_KEY:
        return []

    query_map = {
        "INDIA": "India breaking news",
        "WORLD": "world breaking news",
        "BUSINESS": "global markets economy finance",
        "TECH": "technology AI startup",
        "SPORTS": "cricket football sports",
        "ENTERTAINMENT": "movies celebrities entertainment",
        "POLITICS": "India politics government",
        "SCIENCE": "science space research",
        "FINANCE": "cryptocurrency bitcoin investment money",
        "STARTUPS": "startups founders venture capital",
        "CRIME": "crime investigation law",
        "EDUCATION": "students education university exams",
        "CAREERS": "jobs hiring employees labour",
    }

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query_map.get(category, "India"),
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 15,
                "apiKey": NEWSAPI_KEY,
            },
            timeout=10,
        )
        response.raise_for_status()
        out = []
        for article in response.json().get("articles", []):
            title = article.get("title", "")
            if not title or "[Removed]" in title:
                continue
            if not is_recent(article.get("publishedAt"), max_hours=max_hours):
                continue
            out.append(
                {
                    "title": title,
                    "summary": article.get("description") or "",
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", "NewsAPI"),
                    "image": article.get("urlToImage"),
                    "category": category,
                    "breaking": is_breaking(title),
                    "source_count": 1,
                    "method": "newsapi",
                }
            )
        print(f"    NewsAPI -> {len(out)} articles")
        return out
    except Exception as exc:
        print(f"    NewsAPI error: {exc}")
        return []


def _gnews(category, max_hours=6):
    if not GNEWS_KEY or "YOUR_" in GNEWS_KEY:
        return []

    topic_map = {
        "INDIA": "nation",
        "WORLD": "world",
        "BUSINESS": "business",
        "TECH": "technology",
        "SPORTS": "sports",
        "ENTERTAINMENT": "entertainment",
        "SCIENCE": "science",
        "POLITICS": "nation",
        "FINANCE": "business",
        "STARTUPS": "business",
        "CRIME": "nation",
        "EDUCATION": "nation",
        "CAREERS": "business",
    }

    country = "in" if category == "INDIA" else None

    try:
        params = {
            "topic": topic_map.get(category, "world"),
            "lang": "en",
            "max": 10,
            "apikey": GNEWS_KEY,
        }
        if country:
            params["country"] = country
        response = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        out = []
        for article in response.json().get("articles", []):
            title = article.get("title", "")
            if not title:
                continue
            if not is_recent(article.get("publishedAt"), max_hours=max_hours):
                continue
            out.append(
                {
                    "title": title,
                    "summary": article.get("description") or "",
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", "GNews"),
                    "image": article.get("image"),
                    "category": category,
                    "breaking": is_breaking(title),
                    "source_count": 1,
                    "method": "gnews",
                }
            )
        print(f"    GNews   -> {len(out)} articles")
        return out
    except Exception as exc:
        print(f"    GNews error: {exc}")
        return []


def _rss(category, max_hours=6):
    feeds = RSS_FEEDS.get(category, [])
    seen_titles = set()
    out = []

    for url in feeds:
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            for entry in feed.entries[:15]:
                if not is_recent(entry.get("published"), entry.get("published_parsed"), max_hours=max_hours):
                    continue
                title = clean(entry.get("title", ""))
                if not title or title in seen_titles or len(title) < 15:
                    continue
                seen_titles.add(title)
                summary = clean(entry.get("summary", ""))[:320]
                source = url.split("/")[2].replace("www.", "").replace("feeds.", "")
                image = None
                for marker in ["media_content", "media_thumbnail"]:
                    media = entry.get(marker, [{}])
                    if media and isinstance(media, list) and media[0].get("url"):
                        image = media[0]["url"]
                        break

                article = {
                    "title": title,
                    "summary": summary,
                    "url": entry.get("link", ""),
                    "source": source,
                    "image": image,
                    "category": category,
                    "breaking": is_breaking(title),
                    "source_count": 1,
                    "method": "rss",
                }
                if trust_score(article) >= 50:
                    out.append(article)
        except Exception as exc:
            print(f"    RSS error ({url[:40]}): {exc}")

    print(f"    RSS     -> {len(out)} articles")
    return out


def fetch_news(category="WORLD", limit=5, include_apis=True, max_hours=6):
    print(f"\n  Fetching {category} (last {max_hours}h)...")
    articles = _rss(category, max_hours=max_hours)
    if include_apis:
        articles = _newsapi(category, max_hours=max_hours) + _gnews(category, max_hours=max_hours) + articles
    result = dedup_and_rank(articles, score_fn=trending_score)
    print(f"  Returning top {min(limit, len(result))} of {len(result)} stories")
    return result[:limit]


def _is_similar(title, title_set):
    stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "is", "are", "was", "were", "has", "have", "will", "with", "from", "after"}
    def get_kw(t):
        return {w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", t) if w.lower() not in stop_words}
    
    title_kw = get_kw(title)
    if not title_kw: return title in title_set
    
    for seen_title in title_set:
        if title == seen_title: return True
        seen_kw = get_kw(seen_title)
        if len(title_kw & seen_kw) >= 4:
            return True
    return False

def _pick_articles(pool, count, selected_titles, blocked_titles):
    picked = []
    for article in dedup_and_rank(pool, score_fn=digest_score):
        title = article["title"]
        if _is_similar(title, selected_titles) or _is_similar(title, blocked_titles):
            continue
        selected_titles.add(title)
        picked.append(article)
        if len(picked) >= count:
            break
    return picked


def _pick_with_fallback(primary_pool, fallback_pool, count, selected_titles, blocked_titles):
    picked = _pick_articles(primary_pool, count, selected_titles, blocked_titles)
    if len(picked) < count:
        picked.extend(
            _pick_articles(
                fallback_pool,
                count - len(picked),
                selected_titles,
                blocked_titles,
            )
        )
    return picked


def fetch_digest_news(limit=5, posted_titles=None):
    import random
    posted_titles = set(posted_titles or set())
    limit = max(5, limit) # User requested exactly 5 unique news items per post
    selected_titles = set()

    # Exhaustive list of ALL requested categories
    ALL_CATEGORIES = [
        "INDIA", "WORLD", "BUSINESS", "TECH", "SPORTS",
        "WAR", "CRICKET", "IPL", "INFLATION", "LIFESTYLE", "FRAUD", "ECOSYSTEM", 
        "REGIONAL", "ECONOMY", "TRADE", "CURRENT AFFAIRS", "INNOVATION",
        "POLITICS", "STARTUPS", "MARKETS", "CRYPTO", "AI", "SCIENCE", "SPACE", 
        "DEFENCE", "ENVIRONMENT", "CLIMATE", "ENERGY", "HEALTH", "EDUCATION", 
        "ENTERTAINMENT", "BOLLYWOOD", "HOLLYWOOD", "CELEBRITY", "SOCIAL MEDIA", 
        "INTERNET", "GAMING", "AUTOMOBILE", "REAL ESTATE", "LAW & POLICY", 
        "GLOBAL CONFLICTS", "ELECTIONS"
    ]
    
    # Shuffle to ensure maximum diversity across the 5 daily posts (25 total)
    random.shuffle(ALL_CATEGORIES)
    
    selected = []
    
    # 1. Fetch exactly 1 story from 5 different unique categories
    for category in ALL_CATEGORIES:
        # Fetch stories for this category
        cat_pool = fetch_news(category, limit=6, include_apis=True)
        cat_pool = dedup_and_rank(cat_pool, score_fn=trending_score)
        
        # Pick 1 unique story
        cat_selected = _pick_articles(cat_pool, 1, selected_titles, posted_titles)
        if cat_selected:
            cat_selected[0]["category"] = category
            selected.extend(cat_selected)
            
        if len(selected) >= limit:
            break

    # 2. Safety fallback: fetch a massive generic pool but STRICTLY respect history
    if len(selected) < limit:
        print("    Not enough recent stories found. Expanding search to last 12 hours...")
        fallback_pool = []
        for cat in ["INDIA", "WORLD", "BUSINESS", "TECH", "SPORTS", "ENTERTAINMENT"]:
            fallback_pool.extend(fetch_news(cat, limit=15, include_apis=True, max_hours=12))
        
        ranked_all = dedup_and_rank(fallback_pool, score_fn=trending_score)
        remaining = limit - len(selected)
        selected.extend(_pick_articles(ranked_all, remaining, selected_titles, posted_titles))
        
    final_articles = selected[:limit]
    print(f"  Digest selection -> {len(final_articles)} stories")
    return final_articles


def fetch_breaking():
    out = []
    for category in ["INDIA", "WORLD", "POLITICS"]:
        for article in fetch_news(category, limit=5, include_apis=False):
            if article["breaking"]:
                out.append(article)
    out = dedup_and_rank(out, score_fn=trending_score)
    return out[:3]


if __name__ == "__main__":
    digest = fetch_digest_news(limit=5, posted_titles=set())
    print("\nDIGEST:")
    for index, article in enumerate(digest, start=1):
        print(f"  {index}. [{article['category']}] {article['title']}")
