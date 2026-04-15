# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
test_council_key.py - Quick diagnostic for Council API key health.

Run from backend/ directory:
    python test_council_key.py

Exit codes:
    0 = key is valid, Council will work
    1 = key is invalid or missing (all scores stuck at 0.5)
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY     = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
AI_MODEL       = os.getenv("AI_MODEL", "gpt-4o-mini")

print("=" * 60)
print("  PolyMaster -- Council API Key Diagnostic")
print("=" * 60)
print(f"  AI_MODEL           : {AI_MODEL}")

def key_hint(k):
    if not k:
        return "[NOT SET]"
    if len(k) < 12:
        return "[TOO SHORT - likely placeholder]"
    return f"OK  {k[:8]}...{k[-4:]} (len={len(k)})"

print(f"  OPENAI_API_KEY     : {key_hint(OPENAI_KEY)}")
print(f"  OPENROUTER_API_KEY : {key_hint(OPENROUTER_KEY)}")
print()

active_key  = OPENROUTER_KEY or OPENAI_KEY
base_url    = "https://openrouter.ai/api/v1" if OPENROUTER_KEY else None
backend_str = "OpenRouter" if OPENROUTER_KEY else "OpenAI"

if not active_key:
    print("FATAL: No API key configured.")
    print("   Set OPENAI_API_KEY or OPENROUTER_API_KEY in backend/.env")
    sys.exit(1)

print(f"  Active backend     : {backend_str}")
print()

async def test_key():
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=active_key, base_url=base_url)

        print("Step 1: Listing models (cheapest auth check)...")
        models = await client.models.list()
        model_ids = [m.id for m in models.data[:5]]
        print(f"  [OK] Auth success -- sample models: {model_ids}")

        print()
        print(f"Step 2: Sending minimal test prompt to {AI_MODEL}...")
        resp = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": "Reply ONLY with a single float between 0 and 1, e.g. 0.73"}],
            max_tokens=10,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        print(f"  [OK] Model response: '{raw}'")
        print()
        print("=" * 60)
        print("  RESULT: API key is VALID. Council will produce real scores.")
        print("=" * 60)
        return True

    except Exception as e:
        err = str(e)
        print(f"  [FAIL] ERROR: {err[:300]}")
        print()
        print("=" * 60)
        if "401" in err or "incorrect" in err.lower() or "invalid" in err.lower():
            print("  RESULT: API KEY IS INVALID (401)")
            print()
            print("  FIX:")
            print("  1. Get a valid key from https://openrouter.ai/keys")
            print("     OR from https://platform.openai.com/api-keys")
            print("  2. Update backend/.env:")
            print("     OPENROUTER_API_KEY=sk-or-v1-...")
            print("  3. Restart the bot")
        elif "429" in err or "rate" in err.lower():
            print("  RESULT: RATE LIMITED -- Key is valid but quota exceeded.")
            print("  Check your usage/credits at https://openrouter.ai/credits")
        elif "model" in err.lower() and ("not found" in err.lower() or "does not exist" in err.lower()):
            print(f"  RESULT: MODEL '{AI_MODEL}' NOT FOUND on {backend_str}.")
            print("  Check AI_MODEL in .env -- OpenRouter model names differ from OpenAI.")
            print("  Example: AI_MODEL=openai/gpt-4o-mini  (note the 'openai/' prefix)")
        else:
            print(f"  RESULT: UNEXPECTED ERROR -- {err[:150]}")
        print("=" * 60)
        return False

ok = asyncio.run(test_key())
sys.exit(0 if ok else 1)
