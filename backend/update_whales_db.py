import asyncio
from app.engines.tracker.tracker import SmartMoneyTracker

async def main():
    tracker = SmartMoneyTracker()
    await tracker.update_smart_money_list()
    print("Whales updated in database successfully!")

if __name__ == "__main__":
    asyncio.run(main())
