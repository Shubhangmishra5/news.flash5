# dashboard.py
import os
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from PIL import Image

# Core Engine Imports
from main import run_digest_pipeline, run_story_pipeline
from publisher import distribute_multi_platform
from config import BASE_DIR, PEAK_TIMES

st.set_page_config(
    page_title="NewsFlash5 Control Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Sleek CSS
st.markdown("""
    <style>
        .main {background-color: #0f111a; color: #ffffff;}
        .sidebar .sidebar-content {background-color: #161925;}
        h1, h2, h3 {color: #ff2a5f !important;}
        .stButton>button {
            background-color: #ff2a5f;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 24px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #e01b4c;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ NewsFlash5 | Autonomous Broadcast Center")
st.markdown("---")

# Sidebar - Stats and Info
st.sidebar.image("logo.png", width=120)
st.sidebar.title("System Health")
st.sidebar.success("🟢 Autonomous Engine: ACTIVE")
st.sidebar.info(f"⏰ Peak Digest Times: {', '.join(PEAK_TIMES)}")

# Quick Actions
st.sidebar.subheader("Quick Triggers")
if st.sidebar.button("🚀 Trigger Full Daily Digest"):
    with st.spinner("Executing Full Autonomous News Pipeline..."):
        run_digest_pipeline(force=True)
    st.sidebar.success("Daily Digest Executed Successfully!")

# Tab Navigation
tabs = st.tabs(["📝 Manual Override Console", "📁 Media Vault", "🗄️ Database Explorer", "📜 System Logs"])

# ================= TAB 1: MANUAL OVERRIDE =================
with tabs[0]:
    st.subheader("🔥 Dispatch Custom Breaking News")
    st.write("Type custom updates to instantly compile and broadcast them to all platforms.")
    
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Select News Category", ["BREAKING", "WORLD", "INDIA", "BUSINESS", "TECH", "SPORTS", "ENTERTAINMENT", "SCIENCE"])
        headline = st.text_input("Headline (Max 90 chars)", "BREAKING: Landmark Milestone Achieved!")
        source = st.text_input("Source Attribution", "Official Release")
        
    with col2:
        summary = st.text_area("Bullet Summary (Max 240 chars)", "Autonomous news engine scales operations globally. Multi-platform integration proves 100% robust. Audience engagement trends upward as system deploys real-time updates.")
    
    if st.button("🚨 Broadcast to All Platforms"):
        if not headline or not summary:
            st.error("Please enter a headline and a summary!")
        else:
            with st.spinner("Compiling Media Assets & Dispatching..."):
                try:
                    # Construct article payload
                    custom_article = {
                        "title": headline,
                        "ai_title": headline,
                        "summary": summary,
                        "ai_summary": summary,
                        "category": category.upper(),
                        "source": source,
                        "breaking": True
                    }
                    
                    # Generate the visual assets
                    from image_maker import get_photo
                    
                    # Create custom breaking image
                    canvas = get_photo(custom_article, 1080, 1920)
                    
                    # Render final slide and save
                    from image_maker import OUTPUT_DIR
                    custom_img_path = str(OUTPUT_DIR / f"manual_breaking_{datetime.now().strftime('%H%M%S')}.jpg")
                    canvas.save(custom_img_path)
                    
                    # Generate Reel Video
                    from video_maker import create_reel
                    custom_video_path = create_reel(custom_article, custom_img_path)
                    
                    # Distribute!
                    caption = f"{headline}\n\n{summary}\n\nVia {source} | #NewsFlash5"
                    distribute_multi_platform([custom_img_path], caption, custom_video_path)
                    
                    st.success("🎉 Successfully Published Custom Breaking Update to all social platforms!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Failed to publish custom update: {e}")

# ================= TAB 2: MEDIA VAULT =================
with tabs[1]:
    st.subheader("📁 Live Output Vault")
    st.write("Browse and preview all generated media files locally.")
    
    output_dir = "output_posts"
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        images = [f for f in files if f.endswith(('.jpg', '.png'))]
        videos = [f for f in files if f.endswith('.mp4')]
        
        col_img, col_vid = st.columns(2)
        with col_img:
            st.write("### Latest Image Slides")
            if images:
                selected_img = st.selectbox("Select Image to Preview", images)
                img_path = os.path.join(output_dir, selected_img)
                st.image(img_path, use_column_width=True)
            else:
                st.info("No slide images generated yet.")
                
        with col_vid:
            st.write("### Latest Video Reels")
            if videos:
                selected_vid = st.selectbox("Select Reel to Preview", videos)
                vid_path = os.path.join(output_dir, selected_vid)
                st.video(vid_path)
            else:
                st.info("No video reels generated yet.")
    else:
        st.info("No output directory found yet. Run a pipeline first!")

# ================= TAB 3: DATABASE EXPLORER =================
with tabs[2]:
    st.subheader("🗄️ Posted Article Registry")
    db_path = "bot_database.sqlite"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        try:
            df = pd.read_sql_query("SELECT * FROM posted_articles ORDER BY timestamp DESC", conn)
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.info("Database initialized but empty. Execute your first pipeline run!")
        finally:
            conn.close()
    else:
        st.info("Database file not created yet.")

# ================= TAB 4: SYSTEM LOGS =================
with tabs[3]:
    st.subheader("📜 Real-Time Engine Logs")
    log_file = "bot.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            log_lines = f.readlines()
            
        # Display latest 150 lines
        latest_logs = "".join(log_lines[-150:])
        st.text_area("Engine Activity Stream", latest_logs, height=500)
    else:
        st.info("Log file not created yet.")
