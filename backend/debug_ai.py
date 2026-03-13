import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_models():
    client = AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )
    models = [
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "google/gemini-2.0-flash-lite-preview-02-05",
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-2.0-flash-lite-001"
    ]
    
    with open("debug_output.txt", "w") as f:
        for model in models:
            f.write(f"\n--- Testing model: {model} ---\n")
            try:
                completion = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Say hello world"}]
                )
                f.write(f"SUCCESS: {completion.choices[0].message.content}\n")
            except Exception as e:
                f.write(f"FAILED: {e}\n")
                if hasattr(e, 'response'):
                    f.write(f"Raw response: {e.response.text}\n")
    print("Results written to debug_output.txt")

if __name__ == "__main__":
    asyncio.run(test_models())
