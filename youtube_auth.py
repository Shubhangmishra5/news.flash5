import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

# The scope for uploading videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def authenticate():
    use_hindi = "--hindi" in sys.argv
    token_file = "token_hindi.json" if use_hindi else "token.json"
    channel_label = "Hindi" if use_hindi else "English"

    if not os.path.exists("client_secrets.json"):
        print("ERROR: client_secrets.json not found!")
        print("Please download it from the Google Cloud Console and place it in this folder.")
        return

    print(f"Starting YouTube authentication flow for the {channel_label} channel...")
    print("A browser window should open. Please log in with your YouTube channel account.")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
        # We run local server so the browser can redirect back
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            
        print(f"\nSuccess! {token_file} has been created.")
        print(f"NewsFlash5 bot can now automatically upload videos to your {channel_label} YouTube channel.")
    except Exception as e:
        print(f"\nAuthentication failed: {e}")

if __name__ == '__main__':
    authenticate()
