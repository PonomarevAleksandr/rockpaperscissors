import logging
import time

from aiogram import Router, Bot
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callbacks import Confirm, Move
from app.utils.db import MongoDbClient

router = Router()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@router.callback_query(Confirm.filter())
async def _(callback_query: CallbackQuery, bot: Bot, db: MongoDbClient, callback_data: Confirm):
    try:
        request_id = callback_data.request_id
        res = await db.requests.find_one({"request_id": request_id})
        opponent = res.opponent
        if callback_query.from_user.id == int(opponent):
            await callback_query.answer("Принять")
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🪨", callback_data=Move(choice="rock",
                                                                           duel_id=request_id).pack()))
            keyboard.add(InlineKeyboardButton(text="✂️", callback_data=Move(choice="scissors",
                                                                           duel_id=request_id).pack()))
            keyboard.add(InlineKeyboardButton(text="📄️", callback_data=Move(choice="paper",
                                                                           duel_id=request_id).pack()))

            await db.duels.insert_one({
                "duel_id": request_id,
                "group_id": res.group_id,
                "opponent": opponent,
                "sender": res.sender,
                "message_id": int(res.message_id),
                "time_start": time.time()
            })
            res = await bot.edit_message_text(text=f"Выберите действие:",
                                              chat_id=res.group_id,
                                              message_id=int(res.message_id),
                                              reply_markup=keyboard.as_markup())
            await db.requests.delete_one({"request_id": request_id})
        else:
            await callback_query.answer(text="Извините, принять предложение должен другой игрок", show_alert=True)
    except Exception as e:
        logging.error(e)

@router.callback_query(Move.filter())
async def _(callback_query: CallbackQuery, bot: Bot, db: MongoDbClient, callback_data: Move):
    duel = await db.duels.find_one({"duel_id": callback_data.duel_id})

    if not duel:
        await callback_query.answer("Дуэль не найдена!", show_alert=True)
        return

    if callback_query.from_user.id not in {duel.sender, duel.opponent}:
        await callback_query.answer("Вы не участник этой дуэли!", show_alert=True)
        return

    if callback_query.from_user.id == duel.sender and duel.sender_choice is not None:
        await callback_query.answer("Вы уже сделали свой выбор!", show_alert=True)
        return

    if callback_query.from_user.id == duel.opponent and duel.opponent_choice is not None:
        await callback_query.answer("Вы уже сделали свой выбор!", show_alert=True)
        return

    update_field = "sender_choice" if callback_query.from_user.id == duel.sender else "opponent_choice"
    await db.duels.update_one(
        {"duel_id": callback_data.duel_id},
        {update_field: callback_data.choice, "last_updated": time.time()}
    )
    await callback_query.answer(f"Вы выбрали: {callback_data.choice}")