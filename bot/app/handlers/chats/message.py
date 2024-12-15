import logging
import time
import uuid

import asyncio
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callbacks import Confirm, Cancel
from app.utils.db import MongoDbClient

router = Router()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def generate_uid(db):
    while True:
        request_id = str(uuid.uuid4())
        if not await db.requests.find_one({"request_id": request_id}):
            return request_id


async def ensure_user_in_stats(db, group_id, user_id, username):
    await db.stats.update_one(
        {"group_id": group_id, "user_id": user_id},

        {
            "username": username,
            "date_added": time.time(),
        }
        ,
        upsert=True
    )


@router.my_chat_member()
async def bot_added_or_removed(event: ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.status in {"member", "administrator"}:
        await bot.send_message(
            chat_id=event.chat.id,
            text=(
                f"Привет! \nСпасибо за добавление меня в {event.chat.title} 👋\n"
                f"Теперь ты можешь играть в известную всем игру 'Камень-ножницы-бумага' со своими друзьями!\n\n"
                f"Все что нужно, написать команду /play \nответом на сообщение того, кого хочешь вызвать на дуэль!"
            )
        )
        logging.info(f"Бот добавлен в чат {event.chat.title} (ID: {event.chat.id})")
    else:
        logging.info(f"Бот был удалён из чата {event.chat.title} (ID: {event.chat.id})")


@router.message(Command("play"))
async def play_command(message: types.Message, bot: Bot, db: MongoDbClient):
    try:
        if not message.reply_to_message:
            return

        request_id = await generate_uid(db)

        await asyncio.gather(
            ensure_user_in_stats(
                db=db,
                group_id=message.chat.id,
                user_id=message.from_user.id,
                username=message.from_user.first_name
            ),
            ensure_user_in_stats(
                db=db,
                group_id=message.chat.id,
                user_id=message.reply_to_message.from_user.id,
                username=message.reply_to_message.from_user.first_name
            )
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="✅ Принять",
            callback_data=Confirm(request_id=request_id).pack()
        ))
        keyboard.row(InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=Cancel(request_id=request_id).pack()
        ))

        res = await bot.send_message(
            chat_id=message.chat.id,
            text=(
                f"[{message.from_user.first_name}](tg://user?id={message.from_user.id}) вызывает на дуэль "
                f"[{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id})"
                f"\n\n⌛️ У него есть 2 минуты чтобы принять запрос"
            ),
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )

        await db.requests.insert_one({
            "request_id": request_id,
            "sender": message.from_user.id,
            "opponent": message.reply_to_message.from_user.id,
            "group_id": message.chat.id,
            "time_sent": time.time(),
            "message_id": res.message_id,
            "chat_id": message.chat.id
        })

    except Exception as e:
        logging.error(e)
        raise
