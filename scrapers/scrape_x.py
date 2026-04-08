import tweepy
import os
from dotenv import load_dotenv

load_dotenv()

BEARER = os.getenv("X_BEARER_TOKEN")

client = tweepy.Client(
    bearer_token=BEARER,
    wait_on_rate_limit=True
)

try:
    # اختبار lookup مستخدم عام
    user = client.get_user(username="TwitterDev")
    print("✅ Bearer works")
    print("User ID:", user.data.id)

except Exception as e:
    print("❌ Failed")
    print(e)