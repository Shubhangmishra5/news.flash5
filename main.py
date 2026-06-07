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


def run_story_pipeline(category="WORLD", post_type="carousel", force=False):
    cleanup_output_folder()
    banner(f"STORY MODE | {category} | {post_type.upper()}")

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

    if post_type == "carousel":
        paths = create_carousel(article)
    else:
        paths = [create_single(article)]

    print("\n  Generating caption...")
    caption = generate_caption(article)

    print("\n  Posting...")
    if post_type == "carousel":
        ok = post_carousel(paths, caption)
    else:
        ok = post_single(paths[0], caption)

    if ok:
        mark_posted_titles([article["title"]])
        
    # Attempt cross-platform distribution regardless of IG success (since IG might be disabled for testing)
    distribute_multi_platform(paths if post_type == "carousel" else [paths[0]], caption)

    print(f"\n  Caption preview:\n  {caption[:220]}...")
    return ok


def run_digest_pipeline(force=False):
    cleanup_output_folder()
    banner("HOURLY DIGEST | TOP 5 INDIA + WORLD")
    logging.info("Starting hourly digest pipeline...")

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

    paths = create_digest_carousel(articles)
    caption = generate_caption(build_digest_payload(articles))

    print("\n  Posting digest...")
    ok = post_carousel(paths, caption)
    
    # Generate and post reel
    reel_path = None
    try:
        reel_path = create_digest_reel(articles, paths)
        post_reel(reel_path, caption)
    except Exception as e:
        print(f"  Digest reel skipped: {e}")
    
    # Always save history to prevent duplicate loops
    mark_posted_titles(article["title"] for article in articles)
        
    # Distribute to other platforms (pass reel so Facebook gets the video too)
    distribute_multi_platform(paths, caption, reel_path=reel_path)

    print(f"\n  Caption preview:\n  {caption[:280]}...")
    return ok


def check_breaking():
    cleanup_output_folder()
    print(f"\n  Breaking check [{datetime.now().strftime('%H:%M')}]...")
    for article in fetch_breaking():
        if article["title"] in posted:
            continue

        banner(f"BREAKING ALERT | {article['title'][:48]}")
        article = hydrate_articles([article])[0]
        path = create_single(article)
        caption = generate_caption(article)
        ok = post_single(path, caption)
        
        # Generate and post breaking reel
        try:
            reel_path = create_reel(article, path)
            post_reel(reel_path, caption)
        except Exception as e:
            print(f"  Breaking reel skipped: {e}")
            
        if ok:
            mark_posted_titles([article["title"]])
            
        distribute_multi_platform([path], caption)
        break


def run_test():
    banner("TEST MODE | HOURLY DIGEST SAMPLE")
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

    paths = create_digest_carousel(sample_articles, prefix="sample_digest")
    caption = generate_caption(build_digest_payload(sample_articles))

    banner("TEST COMPLETE")
    print(f"  {len(paths)} images saved to: output_posts/")
    print("\n  Files:")
    for path in paths:
        print(f"    {os.path.basename(path)}")

    folder = os.path.abspath("output_posts")
    print(f"\n  Open folder: {folder}")
    print("\n  Caption preview:")
    print(f"  {caption[:320]}...")


def start_scheduler():
    banner("news.flash5 | 5x daily digest scheduler started")
    
    # Peak Instagram Usage Times (IST)
    peak_times = ["09:00", "12:30", "16:00", "19:30", "22:00"]
    for t in peak_times:
        schedule.every().day.at(t).do(run_digest_pipeline)
    print(f"  Daily digests scheduled at: {', '.join(peak_times)}")

    schedule.every(BREAKING_CHECK_MINS).minutes.do(check_breaking)
    print(f"  Breaking checks every {BREAKING_CHECK_MINS} minutes")
    print("\n  Running... (Press Ctrl+C to stop)\n")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    configure_console()
    load_posted_state()
    args = sys.argv[1:]

    if not args or "--test" in args:
        run_test()
    elif "--schedule" in args:
        start_scheduler()
    elif "--digest" in args or "--once" in args:
        run_digest_pipeline(force="--force" in args)
    elif "--breaking" in args:
        check_breaking()
    elif "--story" in args:
        index = args.index("--story")
        category = args[index + 1].upper() if len(args) > index + 1 else "WORLD"
        run_story_pipeline(category, "carousel", force="--force" in args)
    elif "--single" in args:
        index = args.index("--single")
        category = args[index + 1].upper() if len(args) > index + 1 else "WORLD"
        run_story_pipeline(category, "single", force="--force" in args)
    elif "--legacy-schedule" in args:
        banner("legacy story schedule")
        for schedule_time, category, post_type in DAILY_SCHEDULE:
            schedule.every().day.at(schedule_time).do(run_story_pipeline, category, post_type)
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
