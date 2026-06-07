import os
from publisher import post_to_twitter

dummy_img = "test_twitter.jpg"
with open(dummy_img, "wb") as f:
    f.write(b"dummy image content just to test twitter api keys")
    
print("Testing twitter post...")
try:
    post_to_twitter([dummy_img], "Testing Twitter API Keys for NewsFlash5!")
finally:
    if os.path.exists(dummy_img):
        os.remove(dummy_img)
