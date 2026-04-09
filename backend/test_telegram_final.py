import asyncio
from app.core.config import settings
from app.services.telegram_bot import telegram

async def main():
    print(f"Testing Telegram with settings...")
    print(f"Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"Chat ID: {settings.TELEGRAM_ADMIN_CHAT_ID}")
    
    # Force re-init if needed (though it's a singleton)
    telegram.__init__() 
    
    await telegram.notify("🔔 ¡Prueba de Conexión Exitosa!\nPolyMaster ya puede hablar contigo.")
    print("Done. Check your Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
