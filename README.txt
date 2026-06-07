╔══════════════════════════════════════════════════════════════╗
║           news.flash5  —  Complete Setup Guide              ║
║      Auto News Post Generator for Instagram & More          ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WHAT THIS DOES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ Fetches real, verified breaking news every 10 minutes
  ✅ Creates beautiful 4-slide carousel posts automatically
  ✅ Posts to Instagram 8 times per day with zero manual work
  ✅ Covers India, World, Business, Tech, Sports, Entertainment
  ✅ Uses your news.flash5 logo and brand colors on every post
  ✅ AI-written captions with hashtags
  ✅ Smart backgrounds matching each news story
  ✅ 100% FREE — zero monthly cost

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PROJECT FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  newsflash5/
  ├── main.py          ← START HERE — master runner
  ├── config.py        ← ALL your API keys go here
  ├── fetcher.py       ← Fetches news (RSS + NewsAPI + GNews)
  ├── image_maker.py   ← Creates 4 carousel slide images
  ├── captions.py      ← AI-written Instagram captions
  ├── publisher.py     ← Posts to Instagram automatically
  ├── requirements.txt ← Python libraries list
  ├── logo.png         ← Your logo (already included)
  └── output_posts/    ← Generated images saved here

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 1 — INSTALL PYTHON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Go to: https://python.org/downloads
  2. Download Python 3.11 or newer
  3. During install: ✅ CHECK "Add Python to PATH"
  4. Click Install Now

  Verify it worked — open CMD and type:
    python --version
  Should show: Python 3.11.x  ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 2 — INSTALL LIBRARIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Open CMD, go to your project folder, then run:

    pip install -r requirements.txt

  Wait for all libraries to install (~2 minutes). ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 3 — TEST IT (NO API KEYS NEEDED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Run this FIRST to make sure everything works:

    python main.py

  This will:
  → Create 6 sample news carousels (24 images total)
  → Save them to the output_posts/ folder
  → NO internet posting yet — just local images

  Open output_posts/ folder to see your posts! ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 4 — GET YOUR FREE API KEYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  You need 6 API keys total. All free. Takes ~30 minutes.

  ┌─────────────────────────────────────────────────────────┐
  │  KEY 1: NEWSAPI  (for real news articles)               │
  ├─────────────────────────────────────────────────────────┤
  │  Website : https://newsapi.org                          │
  │  Steps   :                                              │
  │    1. Click "Get API Key"                               │
  │    2. Sign up with email                                │
  │    3. Verify your email                                 │
  │    4. Dashboard shows your API key                      │
  │    5. Copy it (looks like: abc123def456...)             │
  │  Free    : 100 requests/day (you need ~30/day) ✅       │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  KEY 2: GNEWS  (Google News trending stories)           │
  ├─────────────────────────────────────────────────────────┤
  │  Website : https://gnews.io                             │
  │  Steps   :                                              │
  │    1. Click "Get Free API Key"                          │
  │    2. Sign up with email                                │
  │    3. Dashboard → copy your token                       │
  │  Free    : 100 requests/day ✅                          │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  KEY 3: PEXELS  (news background photos)                │
  ├─────────────────────────────────────────────────────────┤
  │  Website : https://www.pexels.com/api/                  │
  │  Steps   :                                              │
  │    1. Click "Get Started"                               │
  │    2. Create free account                               │
  │    3. Go to "Your API Key" section                      │
  │    4. Copy your API key                                 │
  │  Free    : 200 requests/hour ✅                         │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  KEY 4: GROQ  (AI captions — uses LLaMA AI)             │
  ├─────────────────────────────────────────────────────────┤
  │  Website : https://console.groq.com                     │
  │  Steps   :                                              │
  │    1. Sign up (can use Google account)                  │
  │    2. Click "API Keys" in left menu                     │
  │    3. Click "Create API Key"                            │
  │    4. Copy it (starts with: gsk_...)                    │
  │  Free    : 14,400 requests/day ✅                       │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  KEYS 5+6+7: CLOUDINARY  (image hosting for Instagram)  │
  ├─────────────────────────────────────────────────────────┤
  │  Website : https://cloudinary.com                       │
  │  Steps   :                                              │
  │    1. Click "Sign Up for Free"                          │
  │    2. Complete registration                             │
  │    3. Go to Dashboard (main page after login)           │
  │    4. You will see 3 values right on the screen:        │
  │       • Cloud Name   (e.g. dxyz123abc)                  │
  │       • API Key      (e.g. 123456789012345)             │
  │       • API Secret   (e.g. abc-XYZsecret123)            │
  │    5. Copy all 3                                        │
  │  Free    : 25 GB storage/month ✅                       │
  └─────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 5 — GET INSTAGRAM API KEYS (Most Important)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  This allows the bot to post directly to @news.flash5.

  PART A — Switch Instagram to Business Account:
    1. Open Instagram app
    2. Go to your Profile
    3. Tap ☰ (top right) → Settings
    4. Account → Switch to Professional Account
    5. Choose "Business" (not Creator)
    6. Category: "News & Media Website"
    7. Done ✅

  PART B — Create Facebook Page:
    1. Go to facebook.com
    2. Click "Pages" → "Create new Page"
    3. Name it "news.flash5" or "News Flash 5"
    4. Category: News/Media
    5. Done ✅

  PART C — Link Instagram to Facebook Page:
    1. In Instagram → Settings → Account
    2. Linked Accounts → Facebook
    3. Select your "news.flash5" Facebook Page
    4. Done ✅

  PART D — Create Developer App:
    1. Go to: https://developers.facebook.com
    2. Sign in with your Facebook account
    3. Click "My Apps" → "Create App"
    4. App Type: choose "Business"
    5. App Name: anything (e.g. "newsflash5bot")
    6. Click "Create App"
    7. On next page, find "Instagram Graph API"
    8. Click "Set Up" next to it
    9. Done ✅

  PART E — Get Your Access Token:
    1. Go to: https://developers.facebook.com/tools/explorer/
    2. Select your app from dropdown (top right)
    3. Click "Generate Access Token"
    4. Log in to Facebook when prompted
    5. Check these permissions:
       ✅ instagram_basic
       ✅ instagram_content_publish
       ✅ pages_read_engagement
    6. Click "Generate Access Token" button
    7. Copy the long token shown

  PART F — Make Token Long-Lived (60 days):
    Open this URL in your browser (fill in your values):

    https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_TOKEN

    Where to find App ID and Secret:
    → developers.facebook.com → Your App → Settings → Basic

    Copy the longer token from the result. ✅

  PART G — Get Your Instagram User ID:
    Open this URL in browser (replace YOUR_LONG_TOKEN):

    https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_LONG_TOKEN

    You'll see JSON. Find the "id" of your news.flash5 page.
    Then open this URL (replace PAGE_ID):

    https://graph.facebook.com/v18.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_LONG_TOKEN

    The "id" inside "instagram_business_account" is your IG User ID ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 6 — FILL IN config.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Open config.py in any text editor (Notepad works).
  Replace every "YOUR_..." value:

    NEWSAPI_KEY  = "paste your NewsAPI key here"
    GNEWS_KEY    = "paste your GNews token here"
    PEXELS_KEY   = "paste your Pexels key here"
    GROQ_KEY     = "paste your Groq key here"

    CLOUDINARY_CLOUD  = "paste your cloud name"
    CLOUDINARY_KEY    = "paste your API key"
    CLOUDINARY_SECRET = "paste your API secret"

    IG_USER_ID = "paste your Instagram user ID"
    IG_TOKEN   = "paste your long-lived access token"

  Save the file. ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 7 — TEST WITH REAL NEWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Test news fetching (no Instagram posting yet):

    python main.py --test

  Post one real news carousel to Instagram NOW:

    python main.py --once INDIA

  Check and post breaking news right now:

    python main.py --breaking

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 8 — RUN 24/7 ON YOUR PC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Keep CMD open and run:

    python main.py --schedule

  This will post 8 times daily automatically:
    07:00 → India news carousel
    09:30 → World news carousel
    12:00 → Business news carousel
    14:00 → Tech news carousel
    16:30 → Sports news carousel
    19:00 → India news carousel
    20:30 → Entertainment carousel
    22:00 → World news carousel
  + Breaking news check every 10 minutes

  ⚠️  This requires your PC to stay ON and CMD to stay open.
     For 24/7 without your PC → see Step 9.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 9 — DEPLOY 24/7 FREE ON RAILWAY (Recommended)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Railway runs your bot 24/7 even when your PC is off. FREE.

  1. Create account at: https://github.com  (if you don't have one)

  2. Create account at: https://railway.app
     Sign up with GitHub

  3. Create a new GitHub Repository:
     → github.com → New Repository
     → Name: "newsflash5"
     → Public → Create

  4. Upload your project files to GitHub:
     → Go to your new repo
     → Click "uploading an existing file"
     → Drag ALL files from your newsflash5 folder
     → Including logo.png
     → Do NOT upload the output_posts/ folder
     → Click "Commit changes"

  5. In Railway:
     → New Project → Deploy from GitHub repo
     → Select your newsflash5 repo
     → It will start deploying

  6. Add your API keys as Environment Variables in Railway:
     → Go to your project → Variables tab
     → Add each key from config.py:
       NEWSAPI_KEY = your_key
       GNEWS_KEY = your_key
       PEXELS_KEY = your_key
       GROQ_KEY = your_key
       CLOUDINARY_CLOUD = your_cloud
       CLOUDINARY_KEY = your_key
       CLOUDINARY_SECRET = your_secret
       IG_USER_ID = your_id
       IG_TOKEN = your_token

  7. Add a Procfile (create this file in your project):
     → Create file called: Procfile (no extension)
     → Content: worker: python main.py --schedule

  8. Deploy! Your bot now runs 24/7 for free. ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ALL COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  python main.py                  → test mode, saves images locally
  python main.py --test           → same as above
  python main.py --schedule       → run 24/7 auto-poster
  python main.py --once INDIA     → post one INDIA carousel right now
  python main.py --once WORLD     → post one WORLD carousel right now
  python main.py --once BUSINESS  → post one BUSINESS carousel now
  python main.py --once TECH      → post one TECH carousel now
  python main.py --once SPORTS    → post one SPORTS carousel now
  python main.py --breaking       → check & post breaking news now
  python main.py --single INDIA   → post just 1 image (not carousel)

  Test news fetcher separately:
  python fetcher.py               → shows latest news from all sources

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  THE 4-SLIDE CAROUSEL (Your Biggest Advantage)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Every news story = 4 Instagram slides:

  Slide 1 — MAIN BREAKING POST
    • Your approved design
    • BREAKING!! + headline + news photo + summary
    • Gets attention in the feed

  Slide 2 — KEY FACTS
    • 4 numbered facts from the story
    • People SAVE this slide (saves = huge algorithm boost)
    • Dark background, numbered bullet points

  Slide 3 — VISUAL STORY
    • Full-bleed photo with pull quote overlay
    • Most shareable slide — looks premium
    • Drives shares and reposts

  Slide 4 — FOLLOW CTA
    • Your logo big + follow call to action
    • Bell icon reminder to turn on notifications
    • Grows followers with every post

  WHY CAROUSEL?
  Instagram carousels get 3x more reach than single images.
  RVCJ and StartupbyDOC post single images.
  You post 4 slides = algorithm loves you = more followers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW NEWS IS FETCHED & VERIFIED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Method 1: NewsAPI (newsapi.org)
    → 80,000+ sources worldwide
    → Reuters, AP, BBC, NDTV, Economic Times
    → Sorted by publishedAt — LATEST FIRST
    → Also provides real news photo

  Method 2: GNews (gnews.io)
    → Google News — what's TRENDING right now
    → country=in → India-focused
    → Also provides real news photo

  Method 3: RSS Feeds (free, unlimited)
    → Times of India, The Hindu, Indian Express
    → NDTV, Cricbuzz, Bollywood Hungama, and more
    → Runs alongside API methods as backup

  All 3 combined → duplicates removed → ranked by:
    • Is it breaking? (+50 points)
    • Does it mention Modi/Trump/RBI/ISRO? (+20 each)
    • Covered by 2+ sources? (+30)
    • Is it from trusted domain? (+40)
    → Highest score = most important = posts first

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FREE API SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Service         Website                 Free Limit    Setup
  ──────────────────────────────────────────────────────────
  NewsAPI         newsapi.org             100/day       2 min
  GNews           gnews.io                100/day       2 min
  Pexels          pexels.com/api          200/hour      2 min
  Groq            console.groq.com        14,400/day    2 min
  Cloudinary      cloudinary.com          25 GB/month   3 min
  Instagram API   developers.facebook.com Unlimited     20 min
  RSS Feeds       (built-in)              Unlimited     0 min
  Railway hosting railway.app             $5 credit     5 min
  ──────────────────────────────────────────────────────────
  TOTAL MONTHLY COST:  ₹0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WHERE TO POST (Besides Instagram)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Instagram     → Primary platform (auto-posting via API)
  2. Threads       → Auto-syncs with Instagram (zero effort)
  3. Twitter/X     → Same image + headline (manual, 1 tap)
  4. WhatsApp Ch.  → Share from Instagram (1 tap)
  5. Telegram Ch.  → Paste image + caption (1 tap)
  6. Facebook Page → Share from Instagram (auto or 1 tap)
  7. YouTube Short → Add TTS voice, post as 60-sec Short
  8. ShareChat     → Huge Hindi audience in India
  9. Moj / Josh    → Hindi-speaking Tier 2/3 India
  10. Dailyhunt    → News app, direct publisher payments

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  REVENUE TIMELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Month 1-2   2K-5K followers     ₹0 (building audience)
  Month 3-4   10K-20K followers   ₹3,000-8,000 (affiliate links)
  Month 5-6   30K-50K followers   ₹15,000-30,000 (sponsored posts)
  Month 8-10  75K-1L followers    ₹40,000-80,000/month
  Month 12+   2L+ followers       ₹1,00,000+/month

  How to earn:
  1. Sponsored posts (brands pay you to post about them)
  2. Affiliate links in bio (Groww, Zerodha, news apps)
  3. Telegram paid channel (subscribers pay monthly)
  4. YouTube Shorts ad revenue (same content = extra income)
  5. Sell the automation tool to other news pages (SaaS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Problem: "ModuleNotFoundError"
  Fix    : Run → pip install -r requirements.txt

  Problem: Images look dark / no photo
  Fix    : Add your Pexels key in config.py

  Problem: Instagram 400 error
  Fix    : Your token expired → regenerate in Graph API Explorer
           Tokens last 60 days, regenerate before they expire

  Problem: "No articles found"
  Fix    : Add NewsAPI or GNews key in config.py
           RSS feeds sometimes need real browser — API keys fix this

  Problem: Cloudinary upload fails
  Fix    : Check all 3 Cloudinary values in config.py are correct

  Problem: "Permission denied" on Instagram
  Fix    : Make sure you added instagram_content_publish permission
           when generating your access token

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  QUICK START (Summary)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1.  Install Python from python.org ✅
  2.  Open CMD in project folder ✅
  3.  Run: pip install -r requirements.txt ✅
  4.  Run: python main.py → see sample posts in output_posts/ ✅
  5.  Get NewsAPI key (2 min) → newsapi.org ✅
  6.  Get GNews key  (2 min) → gnews.io ✅
  7.  Get Pexels key (2 min) → pexels.com/api ✅
  8.  Get Groq key   (2 min) → console.groq.com ✅
  9.  Get Cloudinary (3 min) → cloudinary.com ✅
  10. Setup Instagram API (20 min) → developers.facebook.com ✅
  11. Fill all keys in config.py ✅
  12. Run: python main.py --once INDIA → first real post! ✅
  13. Run: python main.py --schedule  → runs 24/7 ✅
  14. Deploy to Railway for 24/7 without your PC ✅

  Total setup time: ~45 minutes
  After that: ZERO manual work. Bot posts 8x/day forever.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Built for @news.flash5  |  news.flash5 on Instagram
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
