import os
import asyncio
import re
import textwrap
import requests
import socket
from pathlib import Path
from datetime import datetime

# Prevent synchronous network requests (e.g. gTTS or requests) from hanging indefinitely
socket.setdefaulttimeout(15.0)

import numpy as np
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, vfx

from config import VOICE_EN, VOICE_HI, VOICE_RATE, VOICE_PITCH

OUTPUT_DIR = Path("output_posts")
OUTPUT_DIR.mkdir(exist_ok=True)

# High-Retention Pattern Interrupt Intro & Comment-Driving Outro Pools
INTRO_POOL_EN = [
    "Wait, did you hear what just happened today? Here are your top 5 stories.",
    "Hold on, before you scroll — here are the top 5 updates breaking the internet right now.",
    "Stop scrolling! Here is the biggest news roundup you need to hear today.",
    "Here are the five key stories you shouldn't miss right now.",
    "Let's check out the top updates making headlines across the world today."
]

INTRO_POOL_HI = [
    "रुको! क्या आपने आज की यह बड़ी खबर सुनी? चलिए जानते हैं आज की 5 बड़ी खबरें।",
    "स्क्रॉल करने से पहले रुकिए — यहाँ हैं आज की 5 सबसे महत्वपूर्ण खबरें।",
    "खबरदार! आज दुनिया भर में क्या बड़ा हुआ, चलिए 60 सेकंड में जानते हैं।",
    "आज की 5 बड़ी खबरें जो आपको जाननी बेहद ज़रूरी हैं।",
    "नमस्कार, न्यूज़ फ़्लैश फाइव में आपका स्वागत है। चलिए शुरू करते हैं।"
]

OUTRO_POOL_EN = [
    " Which of these 5 stories surprised you the most? Drop your thoughts in the comments below!",
    " What is your take on today's headlines? Comment your opinion right now!",
    " Don't forget to like, comment your thoughts, and follow News Flash 5 for daily updates.",
    " Which update do you think will impact you the most? Let us know below!",
    " Keep yourself ahead of the news — follow @news.flash5 for more."
]

OUTRO_POOL_HI = [
    " इनमें से किस खबर ने आपको सबसे ज्यादा हैरान किया? कमेंट सेक्शन में अपनी राय ज़रूर दें!",
    " आज की इन बड़ी खबरों पर आपकी क्या राय है? कमेंट में बताएं और न्यूज़ फ़्लैश 5 को फॉलो करें!",
    " आपकी इस बारे में क्या सोच है? कमेंट करके हमें बताइए और चैनल को सब्सक्राइब करें!",
    " अगले बड़े अपडेट के लिए न्यूज़ फ़्लैश 5 को फॉलो करना न भूलें।"
]

MUSIC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def check_and_download_bg_music():
    """Ensure assets/music directory exists and download a pool of premium copyright-free tracks."""
    import random
    music_dir = Path("assets/music")
    music_dir.mkdir(parents=True, exist_ok=True)
    
    tracks = {
        "track_1.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "track_2.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "track_3.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "track_4.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "track_5.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3"
    }
    
    downloaded_tracks = []
    for name, url in tracks.items():
        track_path = music_dir / name
        if not track_path.exists():
            print(f"    [Music] Downloading premium track: {name}...")
            try:
                response = requests.get(url, headers=MUSIC_HEADERS, timeout=15)
                response.raise_for_status()
                with open(track_path, "wb") as f:
                    f.write(response.content)
                print(f"    [Music] Successfully saved track: {name}")
            except Exception as e:
                print(f"    [Music] Failed to download {name}: {e}")
        if track_path.exists():
            downloaded_tracks.append(str(track_path))
            
    if downloaded_tracks:
        selected = random.choice(downloaded_tracks)
        print(f"    [Music] Randomly selected background track: {os.path.basename(selected)}")
        return selected
    return None


def mix_background_music(voiceover_clip, bg_music_path):
    """Mix low-volume background music into the main voiceover clip with volume ducking (MoviePy 2.0 compliant)."""
    if not bg_music_path or not os.path.exists(bg_music_path):
        return voiceover_clip
    try:
        bg_audio = AudioFileClip(bg_music_path)
        # Loop background music if it is shorter than the voiceover
        if bg_audio.duration < voiceover_clip.duration:
            loops = int(voiceover_clip.duration / bg_audio.duration) + 1
            from moviepy import concatenate_audioclips
            bg_audio = concatenate_audioclips([bg_audio] * loops)
            
        bg_audio = bg_audio.with_duration(voiceover_clip.duration)
        # Set background volume to a subtle 8% to prevent overpowering the AI voice (MoviePy 2.0 syntax)
        bg_audio = bg_audio.with_volume_scaled(0.08)
        
        mixed = CompositeAudioClip([voiceover_clip, bg_audio])
        return mixed
    except Exception as e:
        print(f"    [Music] Mixing skipped: {e}")
        return voiceover_clip


def parse_srt(srt_content):
    """Extract timings and texts from raw SRT string generated by edge_tts."""
    pattern = re.compile(
        r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.|\n)*?)(?=\n{2}|\Z)'
    )
    
    def parse_time(time_str):
        h, m, s = time_str.split(':')
        s, ms = s.split(',')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
        
    subtitles = []
    for match in pattern.finditer(srt_content):
        subtitles.append({
            "index": int(match.group(1)),
            "start": parse_time(match.group(2)),
            "end": parse_time(match.group(3)),
            "text": match.group(4).strip().replace('\n', ' ')
        })
    return subtitles


def overlay_subtitles(video_clip, srt_content):
    """Draw captions onto video frames dynamically using PIL to bypass ImageMagick dependency."""
    subtitles = parse_srt(srt_content)
    if not subtitles:
        return video_clip

    # Pre-load best available system bold font
    font = None
    font_paths = [
        "assets/fonts/Roboto-Bold.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            font = ImageFont.truetype(path, 72)
            break
    if not font:
        font = ImageFont.load_default()

    def add_subtitles_to_frame(frame, t):
        # Find active caption at time t
        active_text = ""
        for sub in subtitles:
            if sub["start"] <= t <= sub["end"]:
                active_text = sub["text"]
                break
                
        if not active_text:
            return frame

        # Convert numpy array frame to PIL
        img = Image.fromarray(frame)
        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Wrap text perfectly for vertical width
        wrapped_lines = textwrap.wrap(active_text, width=24)
        
        # Center subtitles near bottom (safe zone y = 1320)
        y_start = 1320
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            x_coord = (w - line_w) // 2

            # Black heavy outline/drop shadow for maximum readability
            shadow_offset = 4
            for dx in [-shadow_offset, 0, shadow_offset]:
                for dy in [-shadow_offset, 0, shadow_offset]:
                    draw.text((x_coord + dx, y_start + dy), line, font=font, fill=(0, 0, 0))

            # Draw gorgeous bright yellow subtitle text
            draw.text((x_coord, y_start), line, font=font, fill=(255, 235, 59))
            y_start += line_h + 15

        return np.array(img)

    return video_clip.transform(lambda gf, t: add_subtitles_to_frame(gf(t), t))


def overlay_progress_bar(video_clip, height=8, color=(230, 30, 45)):
    """Draw a thin, sleek animated progress bar across the top of the video canvas."""
    total_duration = video_clip.duration
    def add_bar_to_frame(frame, t):
        if total_duration <= 0:
            return frame
        progress = min(max(t / total_duration, 0.0), 1.0)
        img = Image.fromarray(frame)
        draw = ImageDraw.Draw(img)
        w, h = img.size
        bar_w = int(progress * w)
        if bar_w > 0:
            draw.rectangle([0, 0, bar_w, height], fill=color)
            draw.rectangle([0, height, bar_w, height + 2], fill=(180, 20, 35))
        return np.array(img)

    return video_clip.transform(lambda gf, t: add_bar_to_frame(gf(t), t))


def _generate_mock_srt(text, audio_path):
    """Generate simple word-timed SRT subtitles based on audio duration for fallback TTS."""
    try:
        from moviepy import AudioFileClip
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close() # Close to release file descriptor
    except Exception:
        duration = 5.0 # Fallback default
        
    words = text.split()
    if not words:
        return ""
        
    total_words = len(words)
    time_per_word = duration / total_words
    
    # Group words into chunks of 4 words for comfortable reading
    chunk_size = 4
    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    
    lines = []
    start_time = 0.0
    for idx, chunk in enumerate(chunks, start=1):
        chunk_text = " ".join(chunk)
        chunk_duration = len(chunk) * time_per_word
        end_time = min(duration, start_time + chunk_duration)
        
        # Format SRT time: HH:MM:SS,mmm
        def fmt(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            
        lines.append(f"{idx}\n{fmt(start_time)} --> {fmt(end_time)}\n{chunk_text}\n")
        start_time = end_time
        
    return "\n".join(lines)


async def generate_voiceover(text, output_audio_path, lang="en"):
    """Generate professional AI voiceover and return the raw SRT subtitle content with natural human news anchor cadence."""
    print(f"    Generating AI Voiceover & Subtitles ({lang.upper()})...")
    
    # Normalize text for ultra-natural news anchor pronunciation & breathing pauses
    clean_text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    if lang == "hi":
        clean_text = clean_text.replace("%", " प्रतिशत ").replace("&", " और ").replace("  ", " ")
        # Ensure Devanagari danda / full stop has a slight pause
        clean_text = clean_text.replace("।", "। ")
    else:
        clean_text = clean_text.replace("%", " percent ").replace("&", " and ").replace("  ", " ")
        clean_text = clean_text.replace(" - ", ", ").replace(" -- ", ", ")

    try:
        if lang == "hi":
            voice = VOICE_HI
        else:
            voice = VOICE_EN
            
        communicate = edge_tts.Communicate(clean_text, voice, rate=VOICE_RATE, pitch=VOICE_PITCH)
        submaker = edge_tts.SubMaker()
        
        async def _stream_tts():
            with open(output_audio_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)
                        
        await asyncio.wait_for(_stream_tts(), timeout=25.0)
        
        # Verify that the audio file was written and is not empty or too small
        if not os.path.exists(output_audio_path) or os.path.getsize(output_audio_path) < 1000:
            raise ValueError("Generated audio file is empty or too small")
                    
        srt_content = submaker.get_srt()
        if not srt_content or len(srt_content.strip()) < 10:
            print("    [Warning] Empty or short subtitles from edge-tts. Generating mock subtitles.")
            srt_content = _generate_mock_srt(text, output_audio_path)
        return output_audio_path, srt_content
    except Exception as exc:
        print(f"    [Warning] Edge-TTS failed: {exc}. Falling back to gTTS (Google TTS)...")
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='hi' if lang == 'hi' else 'en', tld='co.in' if lang == 'hi' else 'com')
            tts.save(output_audio_path)
            
            # Since gTTS doesn't generate timestamps, we generate mock SRT captions based on duration
            srt_content = _generate_mock_srt(text, output_audio_path)
            return output_audio_path, srt_content
        except Exception as fallback_exc:
            print(f"    [Error] Fallback gTTS also failed: {fallback_exc}")
            raise exc


def generate_video(image_path, audio_path, srt_content, output_video_path, bg_music_path=None):
    """Render a single cinematic, zoomed video reel with captions and low background music."""
    print("    Rendering Video Reel...")
    audio_clip = AudioFileClip(audio_path)
    
    # 1. Mix background music into main voiceover
    audio_clip = mix_background_music(audio_clip, bg_music_path)
    duration = audio_clip.duration
    
    # 2. Add cinematic zoom-in effect (Ken Burns)
    image_clip = ImageClip(image_path).with_duration(duration)
    # Slow scale up from 1.0 to 1.06
    zoomed_clip = image_clip.resized(lambda t: 1.0 + (0.06 * (t / duration)))
    
    # 3. Add dynamic text subtitles
    captioned_clip = overlay_subtitles(zoomed_clip, srt_content)
    
    # 4. Pad the 1080x1350 clip into a standard 1080x1920 (9:16) Reels canvas
    from moviepy import ColorClip, CompositeVideoClip
    background = ColorClip(size=(1080, 1920), color=(12, 5, 8)).with_duration(duration)
    padded_clip = CompositeVideoClip([background, captioned_clip.with_position("center")])
    
    video = padded_clip.with_audio(audio_clip)
    
    video.write_videofile(
        output_video_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        ffmpeg_params=[
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "medium",
            "-metadata", "comment=AI Generated News Narration & Visual Format",
            "-metadata", "artist=News Flash 5"
        ]
    )
    
    if os.path.exists(audio_path):
        os.remove(audio_path)
        
    print(f"    Reel successfully rendered: {output_video_path}")
    return output_video_path


def create_reel(article, image_path, lang="en"):
    """Autopilot single reel generation with all V2.0 premium enhancements."""
    if lang == "hi":
        script = article.get("ai_reel_script_hindi", "")
        if not script:
            script = f"{article.get('ai_title_hindi', '')}। और जानकारी के लिए न्यूज़ फ़्लैश 5 को फॉलो करें।"
    else:
        script = article.get("ai_reel_script", "")
        if not script:
            script = f"{article.get('ai_title', '')}. {article.get('ai_summary', '')} Follow News Flash 5 for updates."
        
    filename = os.path.basename(image_path).replace(".jpg", "")
    audio_path = str(OUTPUT_DIR / f"{filename}_{lang}_audio.mp3")
    video_path = str(OUTPUT_DIR / f"{filename}_{lang}_reel.mp4")
    
    bg_music_path = check_and_download_bg_music()
    audio_path, srt_content = asyncio.run(generate_voiceover(script, audio_path, lang=lang))
    
    final_video = generate_video(image_path, audio_path, srt_content, video_path, bg_music_path)
    return final_video


def create_digest_reel(articles, image_paths, lang="en"):
    """Stitch 5 distinct news slides with dynamic zooms, crossfade transitions, background music, and subtitles."""
    import random
    print(f"\n  Generating Digest Video Reel ({lang.upper()})...")
    bg_music_path = check_and_download_bg_music()
    
    video_clips = []
    temp_audio_files = []
    
    # 1. Slide 1 (Cover)
    if lang == "hi":
        cover_script = random.choice(INTRO_POOL_HI)
    else:
        cover_script = random.choice(INTRO_POOL_EN)
    cover_audio_path = str(OUTPUT_DIR / f"temp_cover_audio_{lang}.mp3")
    cover_audio_path, cover_srt = asyncio.run(generate_voiceover(cover_script, cover_audio_path, lang=lang))
    temp_audio_files.append(cover_audio_path)
    
    cover_audio = AudioFileClip(cover_audio_path)
    cover_clip = ImageClip(image_paths[0]).with_duration(cover_audio.duration).with_audio(cover_audio)
    # Add simple zoom & subtitles
    cover_clip = cover_clip.resized(lambda t: 1.0 + (0.06 * (t / cover_audio.duration)))
    cover_clip = overlay_subtitles(cover_clip, cover_srt)
    video_clips.append(cover_clip)
    
    # Imports inside for safety/cleanliness
    from image_maker import translate_to_hindi
    
    # 2. Slides 2-6 (Stories)
    for i, article in enumerate(articles):
        if lang == "hi":
            script = article.get('ai_voiceover_hindi')
            if not script or len(script.strip()) < 5:
                category = translate_to_hindi(article.get('category', 'News'))
                headline = article.get('ai_title_hindi', article.get('title', ''))
                script = f"{category} में, {headline}।"
            
            if i == len(articles) - 1:
                script += random.choice(OUTRO_POOL_HI)
        else:
            script = article.get('ai_voiceover')
            if not script or len(script.strip()) < 5:
                category = article.get('category', 'News').capitalize()
                headline = article.get('ai_title', article.get('title', ''))
                script = f"In {category}, {headline}."
            
            if i == len(articles) - 1:
                script += random.choice(OUTRO_POOL_EN)
            
        audio_path = str(OUTPUT_DIR / f"temp_story_{lang}_{i}_audio.mp3")
        audio_path, story_srt = asyncio.run(generate_voiceover(script, audio_path, lang=lang))
        temp_audio_files.append(audio_path)
        
        audio = AudioFileClip(audio_path)
        img_clip = ImageClip(image_paths[i+1]).with_duration(audio.duration).with_audio(audio)
        
        # Apply Ken Burns Zoom & Subtitles to this slide
        img_clip = img_clip.resized(lambda t: 1.0 + (0.06 * (t / audio.duration)))
        img_clip = overlay_subtitles(img_clip, story_srt)
        
        # Smooth crossfade transition between news slides (MoviePy 2.0 style)
        img_clip = img_clip.with_effects([vfx.CrossFadeIn(0.4)])
        video_clips.append(img_clip)
        
    # 3. Stitch them all together with transitions
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 4. Apply background music to the entire combined video
    final_audio = final_video.audio
    mixed_audio = mix_background_music(final_audio, bg_music_path)
    final_video = final_video.with_audio(mixed_audio)
    
    # 5. Fit/Pad the 1080x1350 video onto a 1080x1920 (9:16) Reels canvas
    from moviepy import ColorClip, CompositeVideoClip
    background = ColorClip(size=(1080, 1920), color=(12, 5, 8)).with_duration(final_video.duration)
    final_video_padded = CompositeVideoClip([background, final_video.with_position("center")]).with_audio(mixed_audio)
    
    video_path = str(OUTPUT_DIR / f"digest_reel_{lang}_{datetime.now().strftime('%H%M%S')}.mp4")
    
    final_video_padded.write_videofile(
        video_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="10000k",
        ffmpeg_params=[
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "medium",
            "-metadata", "comment=AI Generated News Narration & Visual Format",
            "-metadata", "artist=News Flash 5"
        ]
    )
    
    # Cleanup temporary audio files
    for p in temp_audio_files:
        if os.path.exists(p):
            os.remove(p)
            
    print(f"    Digest Reel successfully rendered: {video_path}")
    return video_path


def create_reel(article, image_path, lang="en"):
    """Autopilot single reel generation with all V2.0 premium enhancements."""
    if lang == "hi":
        script = article.get("ai_reel_script_hindi", "")
        if not script:
            script = f"{article.get('ai_title_hindi', '')}। और जानकारी के लिए न्यूज़ फ़्लैश 5 को फॉलो करें।"
    else:
        script = article.get("ai_reel_script", "")
        if not script:
            script = f"{article.get('ai_title', '')}. {article.get('ai_summary', '')} Follow News Flash 5 for updates."
        
    filename = os.path.basename(image_path).replace(".jpg", "")
    audio_path = str(OUTPUT_DIR / f"{filename}_{lang}_audio.mp3")
    video_path = str(OUTPUT_DIR / f"{filename}_{lang}_reel.mp4")
    
    bg_music_path = check_and_download_bg_music()
    audio_path, srt_content = asyncio.run(generate_voiceover(script, audio_path, lang=lang))
    
    final_video = generate_video(image_path, audio_path, srt_content, video_path, bg_music_path)
    return final_video


def create_digest_reel(articles, image_paths, lang="en"):
    """Stitch 5 distinct news slides with dynamic zooms, crossfade transitions, background music, and subtitles."""
    import random
    print(f"\n  Generating Digest Video Reel ({lang.upper()})...")
    bg_music_path = check_and_download_bg_music()
    
    video_clips = []
    temp_audio_files = []
    
    # 1. Slide 1 (Cover)
    if lang == "hi":
        cover_script = random.choice(INTRO_POOL_HI)
    else:
        cover_script = random.choice(INTRO_POOL_EN)
    cover_audio_path = str(OUTPUT_DIR / f"temp_cover_audio_{lang}.mp3")
    cover_audio_path, cover_srt = asyncio.run(generate_voiceover(cover_script, cover_audio_path, lang=lang))
    temp_audio_files.append(cover_audio_path)
    
    cover_audio = AudioFileClip(cover_audio_path)
    cover_clip = ImageClip(image_paths[0]).with_duration(cover_audio.duration).with_audio(cover_audio)
    # Add simple zoom & subtitles
    cover_clip = cover_clip.resized(lambda t: 1.0 + (0.06 * (t / cover_audio.duration)))
    cover_clip = overlay_subtitles(cover_clip, cover_srt)
    video_clips.append(cover_clip)
    
    # Imports inside for safety/cleanliness
    from image_maker import translate_to_hindi
    
    # 2. Slides 2-6 (Stories)
    for i, article in enumerate(articles):
        if lang == "hi":
            script = article.get('ai_voiceover_hindi')
            if not script or len(script.strip()) < 5:
                category = translate_to_hindi(article.get('category', 'News'))
                headline = article.get('ai_title_hindi', article.get('title', ''))
                script = f"{category} में, {headline}।"
            
            if i == len(articles) - 1:
                script += random.choice(OUTRO_POOL_HI)
        else:
            script = article.get('ai_voiceover')
            if not script or len(script.strip()) < 5:
                category = article.get('category', 'News').capitalize()
                headline = article.get('ai_title', article.get('title', ''))
                script = f"In {category}, {headline}."
            
            if i == len(articles) - 1:
                script += random.choice(OUTRO_POOL_EN)
            
        audio_path = str(OUTPUT_DIR / f"temp_story_{lang}_{i}_audio.mp3")
        audio_path, story_srt = asyncio.run(generate_voiceover(script, audio_path, lang=lang))
        temp_audio_files.append(audio_path)
        
        audio = AudioFileClip(audio_path)
        img_clip = ImageClip(image_paths[i+1]).with_duration(audio.duration).with_audio(audio)
        
        # Apply alternating Ken Burns Zoom & Subtitles to this slide for unique motion signature
        if i % 2 == 0:
            img_clip = img_clip.resized(lambda t: 1.0 + (0.06 * (t / audio.duration)))
        else:
            img_clip = img_clip.resized(lambda t: 1.06 - (0.06 * (t / audio.duration)))
            
        img_clip = overlay_subtitles(img_clip, story_srt)
        
        # Smooth crossfade transition between news slides (MoviePy 2.0 style)
        img_clip = img_clip.with_effects([vfx.CrossFadeIn(0.4)])
        video_clips.append(img_clip)
        
    # 3. Stitch them all together with transitions
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 4. Apply background music to the entire combined video
    final_audio = final_video.audio
    mixed_audio = mix_background_music(final_audio, bg_music_path)
    final_video = final_video.with_audio(mixed_audio)
    
    # 5. Fit/Pad the 1080x1350 video onto a 1080x1920 (9:16) Reels canvas
    from moviepy import ColorClip, CompositeVideoClip
    background = ColorClip(size=(1080, 1920), color=(12, 5, 8)).with_duration(final_video.duration)
    final_video_padded = CompositeVideoClip([background, final_video.with_position("center")]).with_audio(mixed_audio)
    
    # 6. Apply thin progress bar across top edge
    final_video_padded = overlay_progress_bar(final_video_padded, height=8, color=(230, 30, 45))
    
    video_path = str(OUTPUT_DIR / f"digest_reel_{lang}_{datetime.now().strftime('%H%M%S')}.mp4")
    
    final_video_padded.write_videofile(
        video_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        ffmpeg_params=[
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "medium",
            "-metadata", "comment=AI Generated News Narration & Visual Format",
            "-metadata", "artist=News Flash 5"
        ]
    )
    
    # Cleanup temporary audio files
    for p in temp_audio_files:
        if os.path.exists(p):
            os.remove(p)
            
    print(f"    Digest Reel successfully rendered: {video_path}")
    return video_path


if __name__ == "__main__":
    print("Video Maker ready!")
