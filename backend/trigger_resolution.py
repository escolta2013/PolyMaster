import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.getcwd())
load_dotenv(".env")

from run_autonomous_loop import OutcomeResolver

async def main():
    print("Starting Outcome Resolution Trigger...")
    resolver = OutcomeResolver()
    # Process several batches if needed to clear the 41 pending trades
    for i in range(3):
        print(f"Batch {i+1}...")
        result = await resolver.resolve_pending()
        print(f"Result: {result}")
        if result["checked"] == 0:
            break

if __name__ == "__main__":
    asyncio.run(main())
