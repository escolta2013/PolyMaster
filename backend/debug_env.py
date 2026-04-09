import os
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), ".env")
print(f"Checking for .env at: {env_path}")
print(f"Exists: {os.path.exists(env_path)}")

load_dotenv(env_path)
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

print(f"Loaded Token: {token[:10] if token else 'NONE'}...")
print(f"Loaded Chat ID: {chat_id}")
