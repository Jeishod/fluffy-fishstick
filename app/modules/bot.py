from aiogram import Bot, Dispatcher, Router
from aiogram.types import BotCommand
from loguru import logger as LOGGER

from app.db.crud_triggers import KucoinTriggersManager
from app.modules.bot_router import router
from app.modules.cache import Cache


class TGBot:
    bot: Bot
    dp: Dispatcher
    bot_router: Router
    admin_chat_id: int

    def __init__(self, token: str, admin_chat_id: int, cache: Cache, db_triggers: KucoinTriggersManager):
        self.dp = Dispatcher(cache=cache, db_triggers=db_triggers)
        self.dp.include_router(router)
        self.bot = Bot(token=token, parse_mode="HTML")
        self.admin_chat_id = admin_chat_id

    async def start(self):
        LOGGER.debug("[BOT] Starting...")
        await self.dp.start_polling(self.bot, handle_signals=False)

    async def stop(self):
        LOGGER.debug("[BOT] Stopping...")
        await self.dp.stop_polling()

    async def prestart(self):
        await self.set_commands()
        await self.delete_webhook()
        await self.send_notification(text="WOAAA, HELLO DUDE!!1")

    async def delete_webhook(self) -> None:
        await self.bot.delete_webhook(drop_pending_updates=True)

    async def send_notification(self, text: str):
        await self.bot.send_message(text=text, chat_id=self.admin_chat_id)
        LOGGER.debug(f"[BOT] Notification sent: {text}")

    async def set_commands(self) -> None:
        commands = [
            BotCommand(command="start", description="В начало"),
            # BotCommand(command="get_status", description="Список триггеров"),
        ]
        await self.bot.set_my_commands(commands)
