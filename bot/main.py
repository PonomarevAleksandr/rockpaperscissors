import asyncio
import logging

import os


from aiogram import Dispatcher, types, F, Router, Bot

from app.utils.middlewares import UserMiddleware
from app.utils.db import db
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
from dotenv import load_dotenv

from app.utils.middlewares import DataBaseMiddleware
from app.utils.middlewares import ThrottlingMiddleware

from app.handlers import router as main_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


async def main():
    session = AiohttpSession()
    bot_settings = {"session": session, "parse_mode": "HTML"}
    bot = Bot(token=os.getenv("BOT_TOKEN"), **bot_settings)
    dp = Dispatcher()

    dp.message.middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(DataBaseMiddleware(db=db))
    dp.message.outer_middleware(UserMiddleware())
    # ---
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(DataBaseMiddleware(db=db))
    dp.callback_query.outer_middleware(UserMiddleware())

    dp.include_router(main_router)

    await dp.start_polling(bot)
    try:
        logger.info("Bot is polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error("An error occurred: %s", e)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
