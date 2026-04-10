
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def debug():
    print("--- PolyMaster Environment Diagnostic ---")
    
    # Check .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ ERROR: .env file not found in current directory!")
        return
    
    print(f"✅ Found .env file at: {env_path.absolute()}")
    
    # Load variables manually to test
    load_dotenv(env_path)
    
    # Check RPCs
    alchemy = os.getenv("ALCHEMY_RPC_URL")
    infura = os.getenv("INFURA_RPC_URL")
    polygon_public = os.getenv("POLYGON_RPC_URL")
    
    print("\n--- RPC Configuration ---")
    print(f"Alchemy URL: {'✅ PRESENT' if alchemy else '❌ MISSING (Using public fallback?)'}")
    if alchemy: print(f"  Prefix: {alchemy[:25]}...")
    
    print(f"Infura URL: {'✅ PRESENT' if infura else '❌ MISSING'}")
    if infura: print(f"  Prefix: {infura[:25]}...")
    
    # Check AI
    ai_key = os.getenv("OPENAI_API_KEY")
    ai_base = os.getenv("OPENAI_API_BASE")
    ai_model = os.getenv("AI_MODEL")
    
    print("\n--- AI Configuration (OpenRouter) ---")
    print(f"Base URL: {ai_base}")
    print(f"Model: {ai_model}")
    print(f"API Key: {'✅ PRESENT' if ai_key else '❌ MISSING'}")
    if ai_key: print(f"  Prefix: {ai_key[:10]}...")

    # Check Budget
    weather_budget = os.getenv("WEATHER_MAX_BUDGET")
    print("\n--- Logic Parameters ---")
    print(f"Weather Budget: {weather_budget}")

if __name__ == "__main__":
    debug()
