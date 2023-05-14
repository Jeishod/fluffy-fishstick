from aiogram import Bot, Dispatcher


class TGBot:
    bot: Bot
    dp: Dispatcher
    admin_chat_id: int

    def __init__(self, token: str, admin_chat_id: int):
        self.dp = Dispatcher()
        self.bot = Bot(token=token, parse_mode="HTML")
        self.admin_chat_id = admin_chat_id

    async def send_notification(self, text: str):
        await self.bot.send_message(text=text, chat_id=self.admin_chat_id)
