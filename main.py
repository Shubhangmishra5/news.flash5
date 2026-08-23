#!/usr/bin/env python3

import json
import os
import sys
import time
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

import schedule

from captions import generate_caption
from config import (
    BREAKING_CHECK_MINS,
    DAILY_SCHEDULE,
    DIGEST_SIZE,
    HOURLY_POST_MINUTE,
)
from fetcher import fetch_breaking, fetch_digest_news, fetch_news, hydrate_articles
from image_maker import create_carousel, create_digest_carousel, create_single
from publisher import post_carousel, post_single, distribute_multi_platform, post_reel
from video_maker import create_reel, create_digest_reel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bot_database.sqlite"

# Set up persistent server logging
logging.basicConfig(
    filename=BASE_DIR / 'bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

posted = set()

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT UNIQUE,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception as e:
        logging.error(f"Database init error: {e}")


def configure_console():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except ValueError:
                pass


def load_posted_state():
    global posted
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT title FROM posted_articles ORDER BY id DESC LIMIT 1000")
            posted = {row[0] for row in cursor.fetchall()}
            logging.info(f"Loaded {len(posted)} past stories from SQLite database.")
    except Exception as exc:
        posted = set()
        logging.error(f"Could not load posted history: {exc}")
        print(f"  Warning: could not load posted history: {exc}")


def save_posted_state():
    # Deprecated in favor of direct DB inserts in mark_posted_titles
    pass


def mark_posted_titles(titles):
    global posted
    titles = list(titles)
    posted.update(titles)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO posted_articles (title) VALUES (?)",
                [(t,) for t in titles]
            )
            # Memory Management: Prune DB to keep only last 1000 records
            conn.execute("""
                DELETE FROM posted_articles 
                WHERE id NOT IN (
                    SELECT id FROM posted_articles ORDER BY id DESC LIMIT 1000
                )
            """)
        logging.info(f"Successfully recorded {len(titles)} new stories into database.")
    except Exception as exc:
        logging.error(f"Database save error: {exc}")


def banner(message):
    width = 62
    line = "=" * width
    print(f"\n{line}")
    print(f"  {message}")
    print(f"  {datetime.now().strftime('%d %b %Y  %H:%M:%S')}")
    print(line)


def build_digest_payload(articles):
    return {
        "type": "digest",
        "title": f"Top {len(articles)} news this hour",
        "category": "DIGEST",
        "source": "Multiple trusted sources",
        "summary": "Hourly India + world digest",
        "articles": articles,
    }


def cleanup_output_folder():
    """Delete files in output_posts older than 10 minutes to prevent storage buildup while avoiding race conditions."""
    folder = Path("output_posts")
    if not folder.exists():
        return
    deleted_count = 0
    now = time.time()
    for file in folder.iterdir():
        try:
            if file.is_file():
                # Only delete files older than 10 minutes (600 seconds)
                if now - file.stat().st_mtime > 600:
                    file.unlink()
                    deleted_count += 1
        except Exception:
            pass
    if deleted_count > 0:
        print(f"\n  [Cleanup] Deleted {deleted_count} old media files from storage.")


def run_story_pipeline(category="WORLD", post_type="carousel", force=False, lang="both", dry_run=False):
    cleanup_output_folder()
    banner(f"STORY MODE | {category} | {lang.upper()}{' | DRY-RUN' if dry_run else ''}")

    articles = fetch_news(category, limit=5, include_apis=True)
    if not articles:
        print("  No articles found")
        return False

    article = next((item for item in articles if force or item["title"] not in posted), None)
    if not article:
        print("  All recent articles already posted - skipping")
        return False
    article = hydrate_articles([article])[0]

    print(f"\n  Story    : {article['title'][:80]}")
    print(f"  Source   : {article['source']}")
    print(f"  Category : {article['category']}")

    languages = ["en", "hi"] if lang in ("both", "all") else [lang]
    successes = []

    for l in languages:
        if post_type == "carousel":
            paths = create_carousel(article, prefix=f"{article['category'].lower()}_{l}", lang=l)
        else:
            paths = [create_single(article, prefix=f"{article['category'].lower()}_{l}", lang=l)]

        print(f"\n  Generating {l.upper()} caption...")
        caption = generate_caption(article, lang=l)

        if dry_run:
            print(f"\n  [DRY-RUN] Generating story reel locally ({l.upper()})...")
            try:
                reel_path = create_reel(article, paths[0], lang=l)
                print(f"  [DRY-RUN] Story reel saved locally to: {reel_path}")
                successes.append(True)
            except Exception as e:
                print(f"  [DRY-RUN] Story reel generation failed/skipped: {e}")
                successes.append(False)
            print("  [DRY-RUN] Skipping all platform uploads.")
        else:
            print(f"\n  Posting {l.upper()} reel...")
            reel_path = None
            try:
                reel_path = create_reel(article, paths[0], lang=l)
                ok = post_reel(reel_path, caption, lang=l)
                distribute_multi_platform(paths, caption, reel_path=reel_path, lang=l)
                successes.append(ok)
            except Exception as e:
                print(f"  Story reel ({l.upper()}) skipped/failed: {e}")
                successes.append(False)

        print(f"\n  Caption preview ({l.upper()}):\n  {caption[:220]}...")

    if any(successes) and not dry_run:
        mark_posted_titles([article["title"]])

    return any(successes)


def run_digest_pipeline(force=False, lang="both", dry_run=False):
    cleanup_output_folder()
    banner(f"HOURLY DIGEST | TOP 5 INDIA + WORLD | {lang.upper()}{' | DRY-RUN' if dry_run else ''}")
    logging.info(f"Starting hourly digest pipeline ({lang.upper()})...")

    blocked_titles = set() if force else posted
    articles = fetch_digest_news(limit=DIGEST_SIZE, posted_titles=blocked_titles)
    if len(articles) < DIGEST_SIZE:
        print(f"  Warning: Only found {len(articles)} fresh stories for the digest.")

    if len(articles) < 3:
        print("  Not enough stories to build a strong digest")
        logging.warning("Digest failed: Not enough stories found.")
        return False

    print("\n  Selected stories:")
    for index, article in enumerate(articles, start=1):
        print(f"  {index}. [{article['category']}] {article['title'][:85]}")

    articles = hydrate_articles(articles)

    languages = ["en", "hi"] if lang in ("both", "all") else [lang]
    successes = []

    for l in languages:
        print(f"\n--- Processing Digest Reel ({l.upper()}) ---")
        paths = create_digest_carousel(articles, prefix=f"digest_{l}", lang=l)
        caption = generate_caption(build_digest_payload(articles), lang=l)

        if dry_run:
            print(f"\n  [DRY-RUN] Generating digest reel locally ({l.upper()})...")
            reel_path = None
            try:
                reel_path = create_digest_reel(articles, paths, lang=l)
                print(f"  [DRY-RUN] Digest reel saved locally to: {reel_path}")
                successes.append(True)
            except Exception as e:
                print(f"  [DRY-RUN] Digest reel generation failed/skipped: {e}")
                successes.append(False)
            print("  [DRY-RUN] Skipping all platform uploads.")
        else:
            print(f"\n  Posting digest reel ({l.upper()})...")
            reel_path = None
            try:
                reel_path = create_digest_reel(articles, paths, lang=l)
                ok = post_reel(reel_path, caption, lang=l)
                distribute_multi_platform(paths, caption, reel_path=reel_path, lang=l)
                successes.append(ok)
            except Exception as e:
                print(f"  Digest reel ({l.upper()}) skipped/failed: {e}")
                successes.append(False)

        print(f"\n  Caption preview ({l.upper()}):\n  {caption[:280]}...")

    if any(successes) and not dry_run:
        mark_posted_titles(article["title"] for article in articles)

    return any(successes)


def check_breaking(lang="both", dry_run=False):
    cleanup_output_folder()
    print(f"\n  Breaking check [{datetime.now().strftime('%H:%M')}]...")
    for article in fetch_breaking():
        if article["title"] in posted:
            continue

        banner(f"BREAKING ALERT | {article['title'][:48]}")
        article = hydrate_articles([article])[0]

        languages = ["en", "hi"] if lang in ("both", "all") else [lang]
        successes = []

        for l in languages:
            path = create_single(article, prefix=f"{article['category'].lower()}_{l}", lang=l)
            caption = generate_caption(article, lang=l)

            if dry_run:
                print(f"\n  [DRY-RUN] Generating breaking reel locally ({l.upper()})...")
                try:
                    reel_path = create_reel(article, path, lang=l)
                    print(f"  [DRY-RUN] Breaking reel saved locally to: {reel_path}")
                    successes.append(True)
                except Exception as e:
                    print(f"  [DRY-RUN] Breaking reel generation failed/skipped: {e}")
                    successes.append(False)
                print("  [DRY-RUN] Skipping all platform uploads.")
            else:
                try:
                    reel_path = create_reel(article, path, lang=l)
                    ok = post_reel(reel_path, caption, lang=l)
                    distribute_multi_platform([path], caption, reel_path=reel_path, lang=l)
                    successes.append(ok)
                except Exception as e:
                    print(f"  Breaking reel ({l.upper()}) skipped/failed: {e}")
                    successes.append(False)

        if any(successes) and not dry_run:
            mark_posted_titles([article["title"]])

        break


def run_test(lang="en"):
    banner(f"TEST MODE | HOURLY DIGEST SAMPLE | {lang.upper()}")
    
    if lang == "hi":
        sample_articles = [
            {
                "title": "India launches record-breaking moon mission with new rover system",
                "ai_title_hindi": "भारत का चंद्र मिशन — नए रोवर सिस्टम के साथ रिकॉर्ड उड़ान",
                "summary": "ISRO launched a new lunar mission with a rover system designed to map water ice, test autonomous navigation, and support future crewed exploration plans.",
                "ai_summary_hindi": "इसरो ने एक नया चंद्र मिशन सफलतापूर्वक लॉन्च किया है। इसका उद्देश्य चंद्रमा के ध्रुवीय क्षेत्रों में पानी और बर्फ का मानचित्रण करना है।",
                "ai_highlights_hindi": [
                    "इसरो का अब तक का सबसे महत्वाकांक्षी चंद्र मिशन सफलतापूर्वक लॉन्च किया गया।",
                    "नया स्वायत्त रोवर पानी की खोज और नेविगेशन का परीक्षण करेगा।",
                    "यह मिशन भविष्य के मानवयुक्त अंतरिक्ष अभियानों की नींव रखेगा।"
                ],
                "source": "NDTV",
                "category": "INDIA",
                "breaking": True,
                "image": None,
            },
            {
                "title": "Global oil markets jump after fresh pressure in West Asia shipping routes",
                "ai_title_hindi": "कच्चे तेल की कीमतें उछलीं — लाल सागर मार्ग पर बढ़ा तनाव",
                "summary": "Oil prices climbed after supply concerns intensified around major shipping routes, pushing global markets to watch energy and inflation risks more closely.",
                "ai_summary_hindi": "पश्चिम एशिया के प्रमुख समुद्री मार्गों पर नया तनाव बढ़ने से वैश्विक बाजार में ईंधन की आपूर्ति को लेकर चिंताएं बढ़ गई हैं।",
                "ai_highlights_hindi": [
                    "प्रमुख व्यापार मार्गों पर सुरक्षा दबाव के कारण कच्चे तेल में उछाल आया।",
                    "वैश्विक बाजार में ऊर्जा संकट और मुद्रास्फीति के खतरे बढ़े।",
                    "विश्लेषकों का मानना है कि दरें अभी और अस्थिर रह सकती हैं।"
                ],
                "source": "Reuters",
                "category": "WORLD",
                "breaking": True,
                "image": None,
            },
            {
                "title": "RBI signals credit support focus as banks prepare for stronger loan demand",
                "ai_title_hindi": "आरबीआई ने दिए संकेत — होम लोन और क्रेडिट सहायता पर विशेष ध्यान",
                "summary": "Indian lenders are preparing for higher retail and business credit demand after the central bank signaled support for stable liquidity and credit growth.",
                "ai_summary_hindi": "भारतीय रिज़र्व बैंक (आरबीआई) ने स्थिर नकदी और ऋण वृद्धि का समर्थन करने का संकेत दिया है। बैंकों को ऋण मांग बढ़ने की उम्मीद है।",
                "ai_highlights_hindi": [
                    "आरबीआई स्थिर नकदी दरों और आसान ऋण नीतियों का समर्थन करेगा।",
                    "निजी और सरकारी बैंक लोन प्रक्रियाओं को आसान बना रहे हैं।",
                    "इस फैसले से घरेलू ग्राहकों को बड़ी राहत मिलने की उम्मीद है।"
                ],
                "source": "Economic Times",
                "category": "BUSINESS",
                "breaking": False,
                "image": None,
            },
            {
                "title": "Apple and Google both push new AI assistant features across core devices",
                "ai_title_hindi": "गूगल और एप्पल में जंग — दोनों कंपनियों ने पेश किए नए एआई फीचर्स",
                "summary": "Fresh AI assistant features are expanding across consumer devices, with both companies racing to improve search, voice control, and on-device productivity.",
                "ai_summary_hindi": "दोनों प्रमुख टेक कंपनियों ने अपने ऑपरेटिंग सिस्टम में नए जनरेटिव एआई सहायकों को जोड़ा है। इससे मोबाइल प्रोडक्टिविटी बढ़ेगी।",
                "ai_highlights_hindi": [
                    "गूगल और एप्पल ने नए एआई पावर्ड सर्च फीचर्स जारी किए हैं।",
                    "ऑन-डिवाइस प्रोडक्टिविटी और वॉयस कंट्रोल में होगा बड़ा सुधार।",
                    "यह तकनीक सामान्य यूज़र्स के रोज़मर्रा के कामों को आसान बनाएगी।"
                ],
                "source": "TechCrunch",
                "category": "TECH",
                "breaking": False,
                "image": None,
            },
            {
                "title": "India and world cricket audiences surge ahead of major tournament weekend",
                "ai_title_hindi": "क्रिकेट का रोमांच बढ़ा — वीकेंड मैचों को लेकर दर्शकों में भारी उत्साह",
                "summary": "Audience demand is rising sharply as major cricket fixtures approach, giving sports platforms and broadcasters a strong engagement boost this weekend.",
                "ai_summary_hindi": "इस वीकेंड होने वाले महत्वपूर्ण मैचों से पहले क्रिकेट दर्शकों की संख्या में भारी उछाल दर्ज किया गया है। ब्रॉडकास्टर्स की रिकॉर्ड कमाई हुई।",
                "ai_highlights_hindi": [
                    "वीकेंड टूर्नामेंट से पहले डिजिटल स्ट्रीमिंग प्लेटफॉर्म्स पर ट्रैफ़िक बढ़ा।",
                    "भारत और वैश्विक दर्शकों के बीच व्यूअरशिप ने नए रिकॉर्ड बनाए।",
                    "विज्ञापनदाताओं के लिए यह वीकेंड काफी महत्वपूर्ण साबित होगा।"
                ],
                "source": "Cricbuzz",
                "category": "SPORTS",
                "breaking": False,
                "image": None,
            },
        ]
    else:
        sample_articles = [
            {
                "title": "India launches record-breaking moon mission with new rover system",
                "summary": "ISRO launched a new lunar mission with a rover system designed to map water ice, test autonomous navigation, and support future crewed exploration plans.",
                "source": "NDTV",
                "category": "INDIA",
                "breaking": True,
                "image": None,
            },
            {
                "title": "Global oil markets jump after fresh pressure in West Asia shipping routes",
                "summary": "Oil prices climbed after supply concerns intensified around major shipping routes, pushing global markets to watch energy and inflation risks more closely.",
                "source": "Reuters",
                "category": "WORLD",
                "breaking": True,
                "image": None,
            },
            {
                "title": "RBI signals credit support focus as banks prepare for stronger loan demand",
                "summary": "Indian lenders are preparing for higher retail and business credit demand after the central bank signaled support for stable liquidity and credit growth.",
                "source": "Economic Times",
                "category": "BUSINESS",
                "breaking": False,
                "image": None,
            },
            {
                "title": "Apple and Google both push new AI assistant features across core devices",
                "summary": "Fresh AI assistant features are expanding across consumer devices, with both companies racing to improve search, voice control, and on-device productivity.",
                "source": "TechCrunch",
                "category": "TECH",
                "breaking": False,
                "image": None,
            },
            {
                "title": "India and world cricket audiences surge ahead of major tournament weekend",
                "summary": "Audience demand is rising sharply as major cricket fixtures approach, giving sports platforms and broadcasters a strong engagement boost this weekend.",
                "source": "Cricbuzz",
                "category": "SPORTS",
                "breaking": False,
                "image": None,
            },
        ]

    paths = create_digest_carousel(sample_articles, prefix="sample_digest", lang=lang)
    caption = generate_caption(build_digest_payload(sample_articles), lang=lang)

    banner("TEST COMPLETE")
    print(f"  {len(paths)} images saved to: output_posts/")
    print("\n  Files:")
    for path in paths:
        print(f"    {os.path.basename(path)}")

    folder = os.path.abspath("output_posts")
    print(f"\n  Open folder: {folder}")
    print("\n  Caption preview:")
    print(f"  {caption[:320]}...")


def start_scheduler(lang="both", dry_run=False):
    banner(f"news.flash5 | 5x daily digest scheduler started | {lang.upper()}{' | DRY-RUN' if dry_run else ''}")
    
    # Peak Instagram Usage Times (IST)
    peak_times = ["09:00", "12:30", "16:00", "19:30", "22:00"]
    for t in peak_times:
        schedule.every().day.at(t).do(run_digest_pipeline, lang=lang, dry_run=dry_run)
    print(f"  Daily digests scheduled at: {', '.join(peak_times)}")

    schedule.every(BREAKING_CHECK_MINS).minutes.do(check_breaking, lang=lang, dry_run=dry_run)
    print(f"  Breaking checks every {BREAKING_CHECK_MINS} minutes")
    print("\n  Running... (Press Ctrl+C to stop)\n")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    configure_console()
    load_posted_state()
    args = sys.argv[1:]

    lang = "both"
    if "--lang" in args:
        idx = args.index("--lang")
        if len(args) > idx + 1:
            lang = args[idx + 1].lower()

    dry_run = "--dry-run" in args

    if not args or "--test" in args:
        run_test(lang=lang)
    elif "--schedule" in args:
        start_scheduler(lang=lang, dry_run=dry_run)
    elif "--digest" in args or "--once" in args:
        run_digest_pipeline(force="--force" in args, lang=lang, dry_run=dry_run)
    elif "--breaking" in args:
        check_breaking(lang=lang, dry_run=dry_run)
    elif "--story" in args:
        index = args.index("--story")
        category = args[index + 1].upper() if len(args) > index + 1 else "WORLD"
        run_story_pipeline(category, "carousel", force="--force" in args, lang=lang, dry_run=dry_run)
    elif "--single" in args:
        index = args.index("--single")
        category = args[index + 1].upper() if len(args) > index + 1 else "WORLD"
        run_story_pipeline(category, "single", force="--force" in args, lang=lang, dry_run=dry_run)
    elif "--legacy-schedule" in args:
        banner(f"legacy story schedule | {lang.upper()}{' | DRY-RUN' if dry_run else ''}")
        for schedule_time, category, post_type in DAILY_SCHEDULE:
            schedule.every().day.at(schedule_time).do(run_story_pipeline, category, post_type, lang=lang, dry_run=dry_run)
            print(f"  {schedule_time} -> {category} ({post_type})")
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        print("Commands:")
        print("  python main.py                -> test the hourly digest layout")
        print("  python main.py --digest       -> post one hourly digest now")
        print("  python main.py --schedule     -> run hourly digest scheduler")
        print("  python main.py --story INDIA  -> post one story carousel now")
        print("  python main.py --single WORLD -> post one single-image story")
        print("  python main.py --breaking     -> post one breaking alert if found")
        print("  python main.py --digest --force -> ignore posted history once")
        print("Options:")
        print("  --lang hi                     -> run the pipeline in Hindi")
        print("  --dry-run                     -> run pipeline locally without uploading")

