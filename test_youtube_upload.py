import os
import sys
from publisher import post_to_youtube

def test_upload():
    print("=== YouTube Shorts Upload Test ===")
    
    # Check if secrets exist locally
    if not os.path.exists("client_secrets.json"):
        print("ERROR: client_secrets.json is missing in this folder.")
        print("Please download your client secrets JSON from Google Cloud Console.")
        return

    if not os.path.exists("token.json"):
        print("ERROR: token.json is missing in this folder.")
        print("Please run 'python youtube_auth.py' first to authenticate.")
        return

    # Check for any MP4 video file in the current directory or output_posts
    video_path = None
    
    # Check output_posts first
    if os.path.exists("output_posts"):
        videos = [os.path.join("output_posts", f) for f in os.listdir("output_posts") if f.endswith(".mp4")]
        if videos:
            video_path = videos[0]
            
    # Check root folder
    if not video_path:
        videos = [f for f in os.listdir(".") if f.endswith(".mp4")]
        if videos:
            video_path = videos[0]

    if not video_path:
        print("\n[!] No test MP4 video found.")
        print("Please render a test video first (e.g., by running 'python main.py')")
        print("or copy any small .mp4 video file to this folder and rename it to 'test.mp4'.")
        return

    print(f"\nUsing test video: {video_path}")
    print("Uploading video to YouTube...")
    post_to_youtube(video_path, "Test YouTube Upload #shorts #newsflash5\n\nChecking if it uploads to the correct channel.")
    print("\nCheck finished. If the upload succeeded, check your YouTube Studio content page.")

if __name__ == "__main__":
    test_upload()
