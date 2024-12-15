import asyncio
import logging
import os
import time

from aiogram import Bot
from dotenv import load_dotenv
from app.utils.db import raw_db as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))

    async def worker():
        async def check_requests():
            while True:
                current_time = time.time()
                requests = await db.requests.find({}).to_list(length=None)

                for request in requests:
                    time_sent = request.get('time_sent')
                    if time_sent and current_time - time_sent > 120:
                        await db.requests.delete_one({'_id': request['_id']})
                        await bot.edit_message_text(chat_id=request['chat_id'], message_id=request['message_id'],
                                                    text="Игра не состоялась (игрок не принял предложение)")
                        logging.info(f"Удалено предложение: {request}")

                await asyncio.sleep(10)

        await check_requests()
    await worker()


if __name__ == "__main__":
    asyncio.run(main())
