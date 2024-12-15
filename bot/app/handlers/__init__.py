__all__ = ("router",)

from aiogram import Router

router = Router()


from .chats import router as chats_router

router.include_routers(chats_router)
