import time
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict

from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from typing import Any, Awaitable, Callable, Dict
from cachetools import TTLCache
from app.models.user import User
from motor.motor_asyncio import AsyncIOMotorClient

class UserMiddleware(BaseMiddleware):

    def __init__(self) -> None:
        pass

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        if not hasattr(event, 'from_user'):
            return

        user = await data['db'].users.find_one(f={'id': event.from_user.id})

        if isinstance(event, Message):

            if user is None:
                if hasattr(event, 'text'):

                    new_user = event.from_user.model_dump()
                    new_user['created_at'] = int(time.time())
                    new_user['updated_at'] = int(time.time())

                    try:
                        if 'rl' in event.text:
                            new_user['refer_id'] = int(event.text.replace('rl', ''))
                    except:  # noqa
                        ...

                    user = User(**new_user)
                    await data['db'].users.insert_one(user.model_dump())

            else:
                if user.blocked_at is not None:
                    await data['db'].users.update_one({'chat_id': event.from_user.id}, {'blocked_at': None})

        if user.updated_at < time.time() - 300:
            await data['db'].users.update_one({'chat_id': event.from_user.id}, event.from_user.model_dump())

        data['user'] = user
        return await handler(event, data)

caches = {
    "default": TTLCache(maxsize=10_000, ttl=0.1)
}


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:

        if event.from_user.id in caches['default']:
            return
        else:
            caches['default'][event.from_user.id] = None
        return await handler(event, data)


class DataBaseMiddleware(BaseMiddleware):
    def __init__(self, db: AsyncIOMotorClient):
        super().__init__()
        self.db = db

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db
        return await handler(event, data)

