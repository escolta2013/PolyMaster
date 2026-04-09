import asyncio
import httpx

async def main():
    token = "8633338181:AAGW6OiJIRZVbgd0YxLyRFRk9WC-BdRdRWU"
    # This is what the user said is the ID
    chat_id = "8633338181" 
    
    # Also try the one we saw in early logs just in case
    old_chat_id = "1211629223"

    print(f"Testing with Token={token[:10]}...")
    
    async with httpx.AsyncClient() as client:
        # Try new ID
        try:
            print(f"Attempting to send to NEW ID: {chat_id}")
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = await client.post(url, json={"chat_id": chat_id, "text": "Prueba con ID 8633338181"})
            print(f"Result for {chat_id}: {resp.status_code} - {resp.json().get('description', 'OK')}")
        except Exception as e:
            print(f"Error {chat_id}: {e}")

        # Try old ID
        try:
            print(f"\nAttempting to send to OLD ID: {old_chat_id}")
            resp = await client.post(url, json={"chat_id": old_chat_id, "text": "Prueba con ID 1211629223"})
            print(f"Result for {old_chat_id}: {resp.status_code} - {resp.json().get('description', 'OK')}")
        except Exception as e:
            print(f"Error {old_chat_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
