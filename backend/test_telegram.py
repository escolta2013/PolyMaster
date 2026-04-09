import asyncio
import os
from aiogram import Bot

async def main():
    token = "8633338181:AAGW6OiJIRZVbgd0YxLyRFRk9WC-BdRdRWU"
    chat_id = "1211629223"
    print(f"Testing bot with Token={token[:10]}... ChatID={chat_id}")
    try:
        bot = Bot(token=token)
        message = await bot.send_message(chat_id=chat_id, text="Hello from PolyMaster Test!")
        print(f"Success! Message sent: {message.message_id}")
    except Exception as e:
        print(f"Failed to send message: {type(e).__name__} - {str(e)}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
