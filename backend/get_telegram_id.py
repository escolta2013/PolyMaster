import urllib.request
import json
import ssl

token = "8633338181:AAGW6OiJIRZVbgd0YxLyRFRk9WC-BdRdRWU"
url = f"https://api.telegram.org/bot{token}/getUpdates"

try:
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=context) as response:
        data = json.loads(response.read())
        
        has_message = False
        print("--- RESULTADOS DE TELEGRAM ---")
        if not data.get("ok"):
            print(f"Error fetching updates: {data}")
        elif not data.get("result"):
            print("No new messages found. Did you send a message recently?")
        else:
            for item in data["result"]:
                if "message" in item:
                    has_message = True
                    msg = item["message"]
                    chat = msg.get("chat", {})
                    chat_id = chat.get("id")
                    username = chat.get("username", "No username")
                    first_name = chat.get("first_name", "No name")
                    text = msg.get("text", "")
                    print(f"Encontré un mensaje de '{first_name}' (@{username}) que dice: '{text}'")
                    print(f"TU CHAT_ID REAL ES: {chat_id}")
            if not has_message:
                print(f"Updates found but no messages. Data: {data}")
except Exception as e:
    print(f"HTTP Error: {e}")
