import asyncio
import httpx
import os
from dotenv import load_dotenv

async def verify_openrouter():
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    model = os.getenv("AI_MODEL", "google/gemma-4-31b-it:free")
    
    print(f"--- Verifying OpenRouter Connection ---")
    print(f"Model: {model}")
    print(f"Base URL: {api_base}")
    print(f"Key ends in: ...{api_key[-4:] if api_key else 'None'}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Respond with 'CONNECTION_OK' if you can read this."}
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"\n[SUCCESS] Response: {content}")
                print("\nOpenRouter is working correctly!")
            else:
                print(f"\n[ERROR] Status Code: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"\n[EXCEPTION] Failed to connect: {str(e)}")

async def verify_gamma():
    print(f"\n--- Verifying Polymarket Gamma API (Keyset) ---")
    url = "https://gamma-api.polymarket.com/markets/keyset"
    params = {"limit": 1, "active": True}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if "markets" in data:
                    print(f"[SUCCESS] Gamma API keyset structure confirmed. Found {len(data['markets'])} markets.")
                else:
                    print(f"[WARNING] Gamma API returned 200 but 'markets' key is missing.")
            else:
                print(f"[ERROR] Gamma API Status: {response.status_code}")
        except Exception as e:
            print(f"[EXCEPTION] Gamma API failure: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_openrouter())
    asyncio.run(verify_gamma())
