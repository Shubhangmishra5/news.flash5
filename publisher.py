import os

import requests

from config import (
    CLOUDINARY_CLOUD,
    CLOUDINARY_KEY,
    CLOUDINARY_SECRET,
    IG_TOKEN,
    IG_USER_ID,
    FB_PAGE_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    DISCORD_WEBHOOK_URL,
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    ENABLE_TWITTER,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USERNAME,
    REDDIT_PASSWORD,
    REDDIT_SUBREDDIT,
)

GRAPH = "https://graph.facebook.com/v18.0"
REQUEST_TIMEOUT = 30


def _is_configured(value):
    return bool(value) and "YOUR_" not in value


def _ready():
    required = [
        IG_USER_ID,
        IG_TOKEN,
        CLOUDINARY_CLOUD,
        CLOUDINARY_KEY,
        CLOUDINARY_SECRET,
    ]
    return all(_is_configured(value) for value in required)


def upload(path):
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD,
        api_key=CLOUDINARY_KEY,
        api_secret=CLOUDINARY_SECRET,
    )
    result = cloudinary.uploader.upload(path, folder="newsflash5")
    url = result["secure_url"]
    print(f"    Uploaded {os.path.basename(path)}")
    return url


def post_single(image_path, caption):
    if not _ready():
        print("    Instagram keys not set - skipping post (test mode)")
        return False

    try:
        media_response = requests.post(
            f"{GRAPH}/{IG_USER_ID}/media",
            data={
                "image_url": upload(image_path),
                "caption": caption,
                "access_token": IG_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        )
        media_response.raise_for_status()

        publish_response = requests.post(
            f"{GRAPH}/{IG_USER_ID}/media_publish",
            data={
                "creation_id": media_response.json()["id"],
                "access_token": IG_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        )
        publish_response.raise_for_status()
        print("    Single post is live on Instagram")
        return True
    except Exception as exc:
        print(f"    Post failed: {exc}")
        return False


def post_carousel(image_paths, caption):
    if not _ready():
        print("    Instagram keys not set - skipping post (test mode)")
        return False

    if len(image_paths) < 2:
        return post_single(image_paths[0], caption)

    try:
        child_ids = []
        for image_path in image_paths:
            child_response = requests.post(
                f"{GRAPH}/{IG_USER_ID}/media",
                data={
                    "image_url": upload(image_path),
                    "is_carousel_item": True,
                    "access_token": IG_TOKEN,
                },
                timeout=REQUEST_TIMEOUT,
            )
            child_response.raise_for_status()
            child_ids.append(child_response.json()["id"])

        carousel_response = requests.post(
            f"{GRAPH}/{IG_USER_ID}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": IG_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        )
        carousel_response.raise_for_status()

        publish_response = requests.post(
            f"{GRAPH}/{IG_USER_ID}/media_publish",
            data={
                "creation_id": carousel_response.json()["id"],
                "access_token": IG_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        )
        publish_response.raise_for_status()
        print(f"    Carousel with {len(image_paths)} slides is live on Instagram")
        return True
    except Exception as exc:
        print(f"    Carousel failed: {exc}")
        return False

def upload_video(path):
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD,
        api_key=CLOUDINARY_KEY,
        api_secret=CLOUDINARY_SECRET,
    )
    result = cloudinary.uploader.upload(path, resource_type="video", folder="newsflash5")
    print(f"    Uploaded Video {os.path.basename(path)}")
    return result["secure_url"]

def post_reel(video_path, caption):
    if not _ready():
        print("    Instagram keys not set - skipping reel (test mode)")
        return False
    try:
        import time
        video_url = upload_video(video_path)
        
        # 1. Create Media Container
        create_res = requests.post(
            f"{GRAPH}/{IG_USER_ID}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": IG_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        )
        create_res.raise_for_status()
        container_id = create_res.json()["id"]
        
        # 2. Wait for Processing
        print("    Waiting for Instagram to process the video...")
        is_finished = False
        for i in range(60): # Wait up to 300 seconds (60 * 5s)
            status_res = requests.get(
                f"{GRAPH}/{container_id}?fields=status_code,status,error_description&access_token={IG_TOKEN}",
                timeout=REQUEST_TIMEOUT
            )
            status_data = status_res.json()
            status_code = status_data.get("status_code")
            print(f"    [Instagram] Processing check {i+1}/60: status_code={status_code}, status_data={status_data}")
            
            if status_code == "FINISHED":
                is_finished = True
                break
            elif status_code == "ERROR":
                err_desc = status_data.get("error_description", "Unknown error during video transcoding.")
                raise Exception(f"Instagram transcoding error: {err_desc}")
            
            time.sleep(5)
            
        if not is_finished:
            raise Exception("Instagram video processing timed out (took longer than 300 seconds).")
            
        # 3. Publish
        requests.post(
            f"{GRAPH}/{IG_USER_ID}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": IG_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        ).raise_for_status()
        print(f"    Reel is live on Instagram!")
        return True
    except Exception as exc:
        print(f"    Reel failed: {exc}")
        return False

# --- MULTI-PLATFORM AUTOMATION ---

def _get_page_token():
    """Exchange the system/IG token for a proper Facebook Page Access Token."""
    page_res = requests.get(
        f"{GRAPH}/{FB_PAGE_ID}?fields=access_token&access_token={IG_TOKEN}",
        timeout=REQUEST_TIMEOUT
    ).json()
    return page_res.get("access_token", IG_TOKEN)


def post_to_facebook(image_paths, caption):
    """Post all carousel slides as a Facebook photo album (multi-photo post)."""
    if not _is_configured(FB_PAGE_ID) or not _is_configured(IG_TOKEN):
        return
    try:
        page_token = _get_page_token()

        if len(image_paths) == 1:
            # Single photo post
            response = requests.post(
                f"{GRAPH}/{FB_PAGE_ID}/photos",
                data={"url": upload(image_paths[0]), "message": caption, "access_token": page_token},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            print("    Posted to Facebook Page (single photo).")
        else:
            # Multi-photo post: upload each photo unpublished, then attach all to one post
            photo_ids = []
            for path in image_paths:
                r = requests.post(
                    f"{GRAPH}/{FB_PAGE_ID}/photos",
                    data={
                        "url": upload(path),
                        "published": False,
                        "access_token": page_token,
                    },
                    timeout=REQUEST_TIMEOUT
                )
                r.raise_for_status()
                photo_ids.append({"media_fbid": r.json()["id"]})

            # Publish all at once as a multi-image post
            # Facebook requires indexed form fields: attached_media[0], attached_media[1], ...
            import json as _json
            post_data = {
                "message": caption,
                "access_token": page_token,
            }
            for i, pid in enumerate(photo_ids):
                post_data[f"attached_media[{i}]"] = _json.dumps(pid)

            feed_res = requests.post(
                f"{GRAPH}/{FB_PAGE_ID}/feed",
                data=post_data,
                timeout=REQUEST_TIMEOUT
            )
            feed_res.raise_for_status()
            print(f"    Posted {len(image_paths)}-slide album to Facebook Page.")

    except Exception as exc:
        print(f"    Facebook post failed: {exc}")
        if 'feed_res' in locals():
            print(f"    Facebook Error Details: {feed_res.text}")
        elif 'r' in locals():
            print(f"    Facebook Error Details: {r.text}")


def post_reel_to_facebook(video_path, caption):
    """Post the reel video to the Facebook Page video feed."""
    if not _is_configured(FB_PAGE_ID) or not _is_configured(IG_TOKEN):
        return
    try:
        page_token = _get_page_token()
        video_url = upload_video(video_path)

        response = requests.post(
            f"{GRAPH}/{FB_PAGE_ID}/videos",
            data={
                "file_url": video_url,
                "description": caption,
                "access_token": page_token,
            },
            timeout=60
        )
        response.raise_for_status()
        print("    Reel posted to Facebook Page.")
    except Exception as exc:
        print(f"    Facebook reel post failed: {exc}")
        if 'response' in locals():
            print(f"    Facebook Error Details: {response.text}")


def post_to_youtube(video_path, caption):
    """Post the reel to YouTube Shorts."""
    import os
    import pickle
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    if not os.path.exists("client_secrets.json"):
        print("    YouTube upload skipped: client_secrets.json missing.")
        return

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"    YouTube token refresh failed: {e}")
                print("    [!] Please run `python youtube_auth.py` to re-authenticate YouTube.")
                return
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
                # YouTube authentication needs browser interaction, we assume it's done manually once
                # if token.json doesn't exist, this might block. Provide instruction to run youtube auth script.
                print("    [!] YouTube needs authentication. Run `python youtube_auth.py` first.")
                return
            except Exception as e:
                print(f"    YouTube Auth Error: {e}")
                return

    try:
        youtube = build('youtube', 'v3', credentials=creds)
        
        # Format caption for YouTube (extract title safely)
        valid_lines = [line.strip() for line in caption.split('\n') if line.strip()]
        title = valid_lines[0] if valid_lines else "News Flash 5 Update"
        
        # YouTube title limit is 100 characters. 
        # Leave room for " #shorts #news" (14 chars) -> max 86 chars for base title
        if len(title) > 85:
            title = title[:82] + "..."
        title += " #shorts #news"
            
        desc = caption + "\n\nSubscribe to @news.flash5 for daily updates!"

        # Extract hashtags from the caption dynamically to use as tags
        dynamic_tags = ['news', 'shorts', 'breaking news', 'newsflash5']
        import re as _re
        hashtags_found = _re.findall(r'#(\w+)', caption)
        for tag in hashtags_found:
            tag_lower = tag.lower()
            if tag_lower not in dynamic_tags:
                dynamic_tags.append(tag_lower)
        # Keep the top 15 tags
        dynamic_tags = dynamic_tags[:15]

        body = {
            'snippet': {
                'title': title,
                'description': desc,
                'tags': dynamic_tags,
                'categoryId': '25' # News & Politics
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        print("    Uploading to YouTube Shorts...")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"      Uploaded {int(status.progress() * 100)}%")

        print(f"    Reel posted to YouTube. Video ID: {response.get('id')}")
        
    except Exception as exc:
        print(f"    YouTube post failed: {exc}")


def post_to_telegram(image_paths, caption):
    if not _is_configured(TELEGRAM_BOT_TOKEN) or not _is_configured(TELEGRAM_CHAT_ID):
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"
        media = [{"type": "photo", "media": upload(path)} for path in image_paths[:10]]
        media[0]["caption"] = caption[:1024]
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "media": media}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        print("    Posted to Telegram.")
    except Exception as exc:
        print(f"    Telegram post failed: {exc}")

def post_to_discord(image_paths, caption):
    if not _is_configured(DISCORD_WEBHOOK_URL):
        return
    try:
        files = {f"file{i}": open(path, "rb") for i, path in enumerate(image_paths[:10])}
        requests.post(DISCORD_WEBHOOK_URL, data={"content": caption[:2000]}, files=files, timeout=REQUEST_TIMEOUT)
        print("    Posted to Discord.")
    except Exception as exc:
        print(f"    Discord post failed: {exc}")

def _upload_twitter_video(twitter, video_path):
    import os
    import time
    
    total_bytes = os.path.getsize(video_path)
    
    # 1. INIT
    r = twitter.post("https://upload.twitter.com/1.1/media/upload.json", data={
        "command": "INIT",
        "total_bytes": total_bytes,
        "media_type": "video/mp4",
        "media_category": "tweet_video"
    })
    r.raise_for_status()
    media_id = r.json()["media_id_string"]
    
    # 2. APPEND
    with open(video_path, 'rb') as f:
        segment_id = 0
        while chunk := f.read(4 * 1024 * 1024):  # 4MB chunks
            twitter.post("https://upload.twitter.com/1.1/media/upload.json", data={
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": segment_id
            }, files={"media": chunk})
            segment_id += 1
            
    # 3. FINALIZE
    r = twitter.post("https://upload.twitter.com/1.1/media/upload.json", data={
        "command": "FINALIZE",
        "media_id": media_id
    })
    r.raise_for_status()
    
    # 4. STATUS (wait for processing)
    processing_info = r.json().get("processing_info", {})
    state = processing_info.get("state")
    while state in ("pending", "in_progress"):
        sleep_secs = processing_info.get("check_after_secs", 5)
        print(f"      Twitter video processing... waiting {sleep_secs}s")
        time.sleep(sleep_secs)
        status_r = twitter.get("https://upload.twitter.com/1.1/media/upload.json", params={
            "command": "STATUS",
            "media_id": media_id
        })
        processing_info = status_r.json().get("processing_info", {})
        state = processing_info.get("state")
        if state == "failed":
            raise Exception("Twitter video processing failed.")
            
    return media_id

def post_to_twitter(image_paths, caption, reel_path=None):
    if not ENABLE_TWITTER:
        return
    if not all(_is_configured(k) for k in [TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        return
    try:
        from requests_oauthlib import OAuth1Session
        twitter = OAuth1Session(TWITTER_API_KEY, client_secret=TWITTER_API_SECRET, resource_owner_key=TWITTER_ACCESS_TOKEN, resource_owner_secret=TWITTER_ACCESS_SECRET)
        
        media_ids = []
        if reel_path:
            print("    Uploading video to Twitter (X)...")
            media_ids.append(_upload_twitter_video(twitter, reel_path))
        else:
            for path in image_paths[:4]:
                with open(path, "rb") as f:
                    r = twitter.post("https://upload.twitter.com/1.1/media/upload.json", files={"media": f})
                    
                    if r.status_code != 200 or "media_id_string" not in r.json():
                        raise Exception(f"Failed to upload image. Status: {r.status_code}, Response: {r.text}")
                        
                    media_ids.append(r.json()["media_id_string"])
                
        payload = {"text": caption[:280]}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
            
        r = twitter.post("https://api.twitter.com/2/tweets", json=payload)
        if r.status_code == 402:
            print("    [!] Twitter (X) post skipped: Requires a paid Developer API subscription (402 Payment Required).")
            return
        r.raise_for_status()
        print("    Posted to Twitter (X).")
    except Exception as exc:
        if hasattr(exc, 'response') and exc.response is not None and exc.response.status_code == 402:
            print("    [!] Twitter (X) post skipped: Requires a paid Developer API subscription (402 Payment Required).")
        elif "402" in str(exc):
            print("    [!] Twitter (X) post skipped: Requires a paid Developer API subscription (402 Payment Required).")
        else:
            print(f"    Twitter post failed: {exc}")

def post_to_reddit(image_paths, caption, reel_path=None):
    if not all(_is_configured(k) for k in [REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD]):
        return
    try:
        import praw
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
            user_agent=f"python:newsflash5.bot:v1 (by u/{REDDIT_USERNAME})"
        )
        
        target_subreddit = REDDIT_SUBREDDIT
        if not target_subreddit or target_subreddit.startswith("YOUR_"):
            target_subreddit = f"u_{REDDIT_USERNAME}"
            
        sub = reddit.subreddit(target_subreddit)
        
        valid_lines = [line.strip() for line in caption.split('\n') if line.strip()]
        title = valid_lines[0] if valid_lines else "News Flash 5 Update"
        if len(title) > 290:
            title = title[:287] + "..."
            
        if reel_path:
            sub.submit_video(title, reel_path)
            print(f"    Posted video to Reddit (r/{target_subreddit}).")
        elif len(image_paths) > 1:
            images = [{"image_path": path} for path in image_paths]
            sub.submit_gallery(title, images)
            print(f"    Posted gallery to Reddit (r/{target_subreddit}).")
        elif len(image_paths) == 1:
            sub.submit_image(title, image_paths[0])
            print(f"    Posted image to Reddit (r/{target_subreddit}).")
            
    except Exception as exc:
        print(f"    Reddit post failed: {exc}")


def distribute_multi_platform(image_paths, caption, reel_path=None):
    post_to_facebook(image_paths, caption)
    if reel_path:
        post_reel_to_facebook(reel_path, caption)
        post_to_youtube(reel_path, caption)
    post_to_telegram(image_paths, caption)
    post_to_discord(image_paths, caption)
    post_to_twitter(image_paths, caption, reel_path)
    post_to_reddit(image_paths, caption, reel_path)
