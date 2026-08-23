import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env(name, default=""):
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_int(name, default, minimum=None, maximum=None):
    value = os.getenv(name)
    if value is None or not value.strip():
        result = default
    else:
        try:
            result = int(value.strip())
        except ValueError:
            result = default

    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


PAGE_HANDLE = _env("PAGE_HANDLE", "@news.flash5")
PAGE_NAME = _env("PAGE_NAME", "News Flash 5")
LOGO_PATH = _env("LOGO_PATH", "logo.png")

NEWSAPI_KEY = _env("NEWSAPI_KEY", "YOUR_NEWSAPI_KEY_HERE")
GNEWS_KEY = _env("GNEWS_KEY", "YOUR_GNEWS_KEY_HERE")
PEXELS_KEY = _env("PEXELS_KEY", "YOUR_PEXELS_KEY_HERE")
GROQ_KEY = _env("GROQ_KEY", "YOUR_GROQ_KEY_HERE")
GROQ_MODEL = _env("GROQ_MODEL", "groq/compound-mini")

CLOUDINARY_CLOUD = _env("CLOUDINARY_CLOUD", "YOUR_CLOUD_NAME")
CLOUDINARY_KEY = _env("CLOUDINARY_KEY", "YOUR_API_KEY")
CLOUDINARY_SECRET = _env("CLOUDINARY_SECRET", "YOUR_API_SECRET")

IG_USER_ID = _env("IG_USER_ID", "YOUR_INSTAGRAM_USER_ID")
IG_TOKEN = _env("IG_TOKEN", "YOUR_LONG_LIVED_ACCESS_TOKEN")

# Hindi Platform Keys
IG_USER_ID_HINDI = _env("IG_USER_ID_HINDI", "YOUR_INSTAGRAM_USER_ID_HINDI")
IG_TOKEN_HINDI = _env("IG_TOKEN_HINDI", "YOUR_LONG_LIVED_ACCESS_TOKEN_HINDI")
FB_PAGE_ID_HINDI = _env("FB_PAGE_ID_HINDI", "YOUR_FACEBOOK_PAGE_ID_HINDI")
TELEGRAM_CHAT_ID_HINDI = _env("TELEGRAM_CHAT_ID_HINDI", "YOUR_TELEGRAM_CHAT_ID_HINDI")
DISCORD_WEBHOOK_URL_HINDI = _env("DISCORD_WEBHOOK_URL_HINDI", "YOUR_DISCORD_WEBHOOK_URL_HINDI")

# Voiceover Settings (Edge-TTS)
VOICE_EN = _env("VOICE_EN", "en-US-AndrewNeural")
VOICE_HI = _env("VOICE_HI", "hi-IN-MadhurNeural")
VOICE_RATE = _env("VOICE_RATE", "-1%")
VOICE_PITCH = _env("VOICE_PITCH", "-1Hz")

# Multi-Platform Keys
FB_PAGE_ID = _env("FB_PAGE_ID", "YOUR_FACEBOOK_PAGE_ID")
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
DISCORD_WEBHOOK_URL = _env("DISCORD_WEBHOOK_URL", "YOUR_DISCORD_WEBHOOK_URL")

REDDIT_CLIENT_ID = _env("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _env("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = _env("REDDIT_USERNAME")
REDDIT_PASSWORD = _env("REDDIT_PASSWORD")
REDDIT_SUBREDDIT = _env("REDDIT_SUBREDDIT")

TWITTER_API_KEY = _env("TWITTER_API_KEY", "YOUR_TWITTER_API_KEY")
TWITTER_API_SECRET = _env("TWITTER_API_SECRET", "YOUR_TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = _env("TWITTER_ACCESS_TOKEN", "YOUR_TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = _env("TWITTER_ACCESS_SECRET", "YOUR_TWITTER_ACCESS_SECRET")
ENABLE_TWITTER = _env("ENABLE_TWITTER", "False").lower() == "true"

COLORS = {
    "red": (230, 30, 45),       # Vibrant premium crimson
    "dark_red": (120, 10, 15),   # Muted elegant red
    "maroon": (60, 5, 10),       # Rich deep maroon
    "deep": (15, 15, 25),        # Deep slate/navy
    "white": (255, 255, 255),
    "offwhite": (245, 245, 247), # Modern off-white
    "dark_bg": (10, 11, 16),     # Sleek modern dark background
    "bar": (20, 22, 30),         # Slate grey bar background
    "light_grey": (240, 240, 245),
}

DIGEST_SIZE = _env_int("DIGEST_SIZE", 6, minimum=3, maximum=8)
DIGEST_INDIA_COUNT = _env_int("DIGEST_INDIA_COUNT", 3, minimum=1, maximum=DIGEST_SIZE)
DIGEST_WORLD_COUNT = _env_int("DIGEST_WORLD_COUNT", 3, minimum=1, maximum=DIGEST_SIZE)
HOURLY_POST_MINUTE = _env_int("HOURLY_POST_MINUTE", 5, minimum=0, maximum=59)
BREAKING_CHECK_MINS = _env_int("BREAKING_CHECK_MINS", 30, minimum=15, maximum=120)

# Retained for compatibility with older story-based commands.
DAILY_SCHEDULE = [
    ("07:00", "INDIA", "carousel"),
    ("09:30", "WORLD", "carousel"),
    ("12:00", "BUSINESS", "carousel"),
    ("14:00", "TECH", "carousel"),
    ("16:30", "SPORTS", "carousel"),
    ("19:00", "INDIA", "carousel"),
    ("20:30", "ENTERTAINMENT", "carousel"),
    ("22:00", "WORLD", "carousel"),
]
