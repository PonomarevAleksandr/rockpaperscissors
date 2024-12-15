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

async def determine_winner(choice1: str, choice2: str) -> int:
    try:
        outcomes = {
            "rock": {"scissors": "win", "paper": "lose", "rock": "draw"},
            "paper": {"rock": "win", "scissors": "lose", "paper": "draw"},
            "scissors": {"paper": "win", "rock": "lose", "scissors": "draw"},
        }
        result = outcomes[choice1][choice2]
        if result == "win":
            return 1
        elif result == "lose":
            return 2
        else:
            return 3
    except KeyError as e:
        logging.error(f"Ошибка определения победителя: {e}")
        return 0  # Код для непредвиденного результата


async def update_stats(group_id: int, user_id: int, result: str):
    try:
        increment_fields = {
            "games_played": 1,
            "wins": 1 if result == "win" else 0,
            "losses": 1 if result == "lose" else 0,
            "draws": 1 if result == "draw" else 0,
        }
        await db['stats'].update_one(
            {"group_id": group_id, "user_id": user_id},
            {"$inc": increment_fields},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Ошибка обновления статистики для пользователя {user_id} в группе {group_id}: {e}")


async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))

    async def worker():
        async def check_requests():
            while True:
                try:
                    current_time = time.time()
                    requests = await db.requests.find({}).to_list(length=None)

                    for request in requests:
                        try:
                            time_sent = request.get('time_sent')
                            if time_sent and current_time - time_sent > 120:
                                await db.requests.delete_one({'_id': request['_id']})
                                await bot.edit_message_text(chat_id=request['chat_id'], message_id=request['message_id'],
                                                            text="Игра не состоялась (игрок не принял предложение)")
                                logging.info(f"Удалено предложение: {request}")
                        except Exception as e:
                            logging.error(f"Ошибка обработки запроса {request}: {e}")

                    await asyncio.sleep(10)
                except Exception as e:
                    logging.error(f"Ошибка в check_requests: {e}")

        async def check_duels():
            while True:
                try:
                    current_time = time.time()

                    duels = await db["duels"].find({
                        "sender_choice": {"$ne": None},
                        "opponent_choice": {"$ne": None}
                    }).to_list(length=None)

                    for duel in duels:
                        try:
                            if duel.get("sender_choice") and duel.get("opponent_choice"):
                                result = await determine_winner(duel["sender_choice"], duel["opponent_choice"])

                                sender_stats = await db.stats.find_one(
                                    {"group_id": duel["group_id"], "user_id": duel["sender"]})
                                opponent_stats = await db.stats.find_one(
                                    {"group_id": duel["group_id"], "user_id": duel["opponent"]})

                                sender_name = f"[{sender_stats['username']}](tg://user?id={duel['sender']})" \
                                    if sender_stats else "Игрок 1"
                                opponent_name = f"[{opponent_stats['username']}](tg://user?id={duel['opponent']})" \
                                    if opponent_stats else "Игрок 2"

                                if result == 1:
                                    update_stats_tasks = [
                                        update_stats(duel["group_id"], duel["sender"], "win"),
                                        update_stats(duel["group_id"], duel["opponent"], "lose"),
                                    ]
                                    result_text = f"{sender_name} победил!"

                                elif result == 2:
                                    update_stats_tasks = [
                                        update_stats(duel["group_id"], duel["sender"], "lose"),
                                        update_stats(duel["group_id"], duel["opponent"], "win"),
                                    ]
                                    result_text = f"{opponent_name} победил!"

                                else:
                                    update_stats_tasks = [
                                        update_stats(duel["group_id"], duel["sender"], "draw"),
                                        update_stats(duel["group_id"], duel["opponent"], "draw"),
                                    ]
                                    result_text = "Ничья!"

                                await asyncio.gather(*update_stats_tasks)

                                choices_emoji = {
                                    "rock": "🪨",
                                    "paper": "📄️",
                                    "scissors": "✂️️",
                                }

                                await bot.edit_message_text(
                                    chat_id=duel["group_id"],
                                    message_id=duel["message_id"],
                                    text=(
                                        f"💬 Игра завершена!\n\n"
                                        f"🙎‍♂️ {sender_name} выбрал: {choices_emoji.get(duel['sender_choice'], duel['sender_choice'])}\n"
                                        f"🙎‍♂️ {opponent_name} выбрал: {choices_emoji.get(duel['opponent_choice'], duel['opponent_choice'])}\n\n"
                                        f"⚔️ Результат: {result_text}"
                                    ),
                                    parse_mode="Markdown"
                                )

                                await db.duels.delete_one({"duel_id": duel["duel_id"]})
                                logging.info(f"Дуэль завершена и удалена: {duel}")

                            elif current_time - duel["time_start"] > 300:  # 5 минут
                                await bot.edit_message_text(
                                    chat_id=duel["group_id"],
                                    message_id=duel["message_id"],
                                    text=(
                                        f"Игра завершена! Один из участников не сделал выбор вовремя.\n"
                                        f"Дуэль между игроками {duel['sender']} и {duel['opponent']} отменена."
                                    )
                                )

                                await db.duels.delete_one({"duel_id": duel["duel_id"]})
                                logging.info(f"Просроченная дуэль удалена: {duel}")

                        except Exception as e:
                            logging.error(f"Ошибка обработки дуэли {duel}: {e}")

                    await asyncio.sleep(5)
                except Exception as e:
                    logging.error(f"Ошибка в check_duels: {e}")

        await asyncio.gather(
            check_requests(),
            check_duels(),
        )
    try:
        await worker()
    except Exception as e:
        logging.critical(f"Ошибка в main worker: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Ошибка запуска main: {e}")
