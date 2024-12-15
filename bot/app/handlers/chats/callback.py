import logging
import time

from aiogram import Router, types, Bot
from aiogram.filters import Command, ChatMemberUpdatedFilter, MEMBER
from aiogram.types import InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.db import MongoDbClient
from app.utils.callbacks import Confirm, Cancel, Move

router = Router()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@router.callback_query(Confirm.filter())
async def _(callback_query: CallbackQuery, bot: Bot, db: MongoDbClient, data: Confirm):
    try:
        request_id = data.request_id
        res = await db.requests.find_one({"request_id": request_id})
        opponent = res.opponent
        if callback_query.from_user.id == int(opponent):
            await callback_query.answer("Принять")
            await db.requests.delete_one({"request_id": request_id})

            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🪨", callback_data=Move(choice="rock",
                                                                           user=callback_query.from_user.id).pack()))
            keyboard.add(InlineKeyboardButton(text="✂️", callback_data=Move(choice="scissors",
                                                                           user=callback_query.from_user.id).pack()))
            keyboard.add(InlineKeyboardButton(text="📄️", callback_data=Move(choice="papper",
                                                                           user=callback_query.from_user.id).pack()))

            await db.duels.insert_one({
                "duel_id": request_id,
                "group_id": res.group_id,
                "opponent": opponent,
                "sender": res.sender,
                "time": time.time()
            })
        else:
            await callback_query.answer(text="Извините, принять предложение должен другой игрок", show_alert=True)
    except Exception as e:
        logging.error(e)
