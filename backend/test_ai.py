import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_model():
    client = AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )
    model = os.getenv("AI_MODEL")
    print(f"Testing model: {model}")
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, reasoning test. [Reasoning] | [FinalConfidence]"}]
        )
        print(f"Response: {completion.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_model())
