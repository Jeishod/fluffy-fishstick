from aiogram import Router
from aiogram.filters import Command, Text
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from jinja2 import Template
from loguru import logger as LOGGER

from app.db.crud_triggers import KucoinTriggersManager
from app.managers import triggers_manager
from app.modules.cache import Cache


triggers_message_template = Template(
    source="""
{% for trigger in all_triggers %}
✅<b>{{ trigger.from_symbol }}-{{ trigger.to_symbol }}</b>
triggering count: <b>{{ trigger.transactions_max_count }}</b>
current count: <b>{{ trigger.current_count }}</b>
period, sec: <b>{{ trigger.period_seconds }}</b>
side: <b>{{ trigger.side }}</b>
all transactions count: <b>{{ trigger.transactions_count }}</b>
{% endfor %}
""",
)


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = [
        [KeyboardButton(text="Список триггеров"), KeyboardButton(text="Ничего")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Выбери чо хочешь")
    await message.answer("Чо хотим?", reply_markup=keyboard)


@router.message(Text("Список триггеров"))
async def handle_triggers_list(
    message: Message,
    db_triggers: KucoinTriggersManager,
    cache: Cache,
):
    LOGGER.debug("[BOT] Triggers statuses requested")
    all_triggers = await triggers_manager.get_all(db_triggers=db_triggers, cache=cache)
    if not all_triggers:
        filled_triggers_list_template = "There is no active triggers."
    else:
        filled_triggers_list_template = triggers_message_template.render(all_triggers=all_triggers)

    await message.reply(text=filled_triggers_list_template)


@router.message(Text("Ничего"))
async def handle_nothing(message: Message):
    await message.reply("Ну и ладно, пака!👋")
