import logging
import time
import uuid

import asyncio
from random import choice

from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callbacks import Confirm, Cancel, Move
from app.utils.db import MongoDbClient
from app.utils.db import raw_db

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
    try:
        if event.new_chat_member.status in {"member", "administrator"}:
            await bot.send_message(
                chat_id=event.chat.id,
                text=(
                    f"Привет! \nСпасибо за добавление меня в {event.chat.title} 👋\n"
                    f"Теперь ты можешь играть в известную всем игру 'Камень-ножницы-бумага' со своими друзьями!\n\n"
                    f"Все что нужно, написать команду \n/play ответом на сообщение того, кого хочешь вызвать на дуэль!"
                )
            )
            logging.info(f"Бот добавлен в чат {event.chat.title} (ID: {event.chat.id})")
            await raw_db["groups"].insert_one({
                "group_id": event.chat.id,
                "group_name": event.chat.title,
                "date_added": time.time(),
            })
        else:
            logging.info(f"Бот был удалён из чата {event.chat.title} (ID: {event.chat.id})")
            await raw_db["groups"].delete_one({"group_id": event.chat.id})
            await raw_db["duels"].delete_many({"group_id": event.chat.id})
            await raw_db["stats"].delete_many({"group_id": event.chat.id})
            await raw_db["requests"].delete_many({"group_id": event.chat.id})
    except Exception as e:
        logging.error(e)



@router.message(Command("play"))
async def play_command(message: types.Message, bot: Bot, db: MongoDbClient):
    try:
        if not message.reply_to_message:
            logging.info("Сообщение небыло ответом")
            return
        if message.reply_to_message.from_user.id == 7771313796:  # ID бота
            logging.info("Бот принимает участие в дуэли")
            bot_choice = choice(["rock", "paper", "scissors"])
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
                    user_id=7771313796,
                    username="🤖 Бот"
                )
            )
            duel_id = await generate_uid(db)
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🪨", callback_data=Move(choice="rock",
                                                                           duel_id=duel_id).pack()))
            keyboard.add(InlineKeyboardButton(text="✂️", callback_data=Move(choice="scissors",
                                                                           duel_id=duel_id).pack()))
            keyboard.add(InlineKeyboardButton(text="📄️", callback_data=Move(choice="paper",
                                                                           duel_id=duel_id).pack()))
            res = await bot.send_message(
                chat_id=message.chat.id,
                text=(
                    f"🤖 Бот принимает вызов!\n"
                    f"[{message.from_user.first_name}](tg://user?id={message.from_user.id}) против 🤖 Бота.\n\n"
                    f"⌛️ Выберите ваш ход!"
                ),
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            await db.duels.insert_one({
                "duel_id": duel_id,
                "group_id": message.chat.id,
                "sender": message.from_user.id,
                "opponent": 7771313796,
                "message_id": res.message_id,
                "time_start": time.time(),
                "last_updated": time.time(),
                "opponent_choice": bot_choice
            })
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
