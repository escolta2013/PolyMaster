import asyncio
from dotenv import load_dotenv
load_dotenv(".env")
from run_autonomous_loop import OutcomeResolver

async def main():
    res = OutcomeResolver()
    out = await res.resolve_pending()
    print("Resolved:", out)

if __name__ == "__main__":
    asyncio.run(main())
