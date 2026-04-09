import urllib.request
import json
import ssl

token = "8633338181:AAGW6OiJIRZVbgd0YxLyRFRk9WC-BdRdRWU"
url = f"https://api.telegram.org/bot{token}/getMe"

try:
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=context) as response:
        data = json.loads(response.read())
        print(f"\n--- INFORMACIÓN DEL BOT ---")
        if data.get("ok"):
            bot = data["result"]
            print(f"Nombre del Bot: {bot.get('first_name')}")
            print(f"Usuario del Bot (buscar en Telegram): @{bot.get('username')}")
        else:
            print("Token inválido!")
except Exception as e:
    print(f"Error: {e}")
