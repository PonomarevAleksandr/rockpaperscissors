__all__ = ("router",)

from aiogram import Router

router = Router()

from .message import router as message_router
from .callback import router as callback_router

router.include_routers(message_router, callback_router)
