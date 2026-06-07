import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The scope for uploading videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def authenticate():
    if not os.path.exists("client_secrets.json"):
        print("ERROR: client_secrets.json not found!")
        print("Please download it from the Google Cloud Console and place it in this folder.")
        return

    print("Starting YouTube authentication flow...")
    print("A browser window should open. Please log in with your YouTube channel account.")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
        # We run local server so the browser can redirect back
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        print("\nSuccess! token.json has been created.")
        print("NewsFlash5 bot can now automatically upload videos to your YouTube channel.")
    except Exception as e:
        print(f"\nAuthentication failed: {e}")

if __name__ == '__main__':
    authenticate()
