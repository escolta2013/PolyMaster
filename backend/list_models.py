import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json().get("data", [])
        free_models = [m["id"] for m in models if m.get("pricing", {}).get("prompt") == "0"]
        with open("models_list.txt", "w") as f:
            for m in free_models:
                f.write(f"{m}\n")
        print(f"Saved {len(free_models)} free models to models_list.txt")
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    list_models()
