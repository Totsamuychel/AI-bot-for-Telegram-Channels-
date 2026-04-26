import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from admin_bot.config import TOKEN, ADMIN_IDS
from admin_bot.database import init_db, async_session, BotSetting, get_bot_setting

# Logging setup
logging.basicConfig(level=logging.INFO)

# Router/Bot init
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Filters
class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message | types.CallbackQuery) -> bool:
        user_id = message.from_user.id
        return user_id in ADMIN_IDS

# States
class BotStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_prompt = State()

# Keyboards
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подключить канал", callback_data="set_channel")],
        [InlineKeyboardButton(text="🧠 Настроить нейронку", callback_data="set_prompt")],
        [InlineKeyboardButton(text="📊 Статистика / Настройки", callback_data="stats")]
    ])



# Handlers
@dp.message(Command("start"), AdminFilter())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в Admin Bot системы n8n!\nВыберите действие:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "stats", AdminFilter())
async def cq_stats(callback: types.CallbackQuery):
    async with async_session() as session:
        settings = await get_bot_setting(session)
        channel = settings.channel_id if settings.channel_id else "Не задан"
        prompt = settings.prompt if settings.prompt else "Не задан"
    text = f"⚙️ Текущие настройки:\n📢 Канал: {channel}\n🧠 Промпт: {prompt}"
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "set_channel", AdminFilter())
async def cq_set_channel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Пожалуйста, перешлите любое сообщение из вашего канала (я должен быть там администратором), либо отправьте его ID (например, -100...)."
    )
    await state.set_state(BotStates.waiting_for_channel)
    await callback.answer()

@dp.message(BotStates.waiting_for_channel, AdminFilter())
async def process_channel(message: types.Message, state: FSMContext):
    channel_id = None
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        channel_id = message.forward_from_chat.id
    else:
        try:
            channel_id = int(message.text)
        except (ValueError, TypeError):
            await message.answer("Не удалось определить ID канала. Попробуйте еще раз.")
            return

    async with async_session() as session:
        settings = await get_bot_setting(session)
        settings.channel_id = channel_id
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Канал успешно сохранен (ID: {channel_id}).", reply_markup=get_main_menu())

@dp.callback_query(F.data == "set_prompt", AdminFilter())
async def cq_set_prompt(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправьте мне системный промпт или тему для автопостинга:")
    await state.set_state(BotStates.waiting_for_prompt)
    await callback.answer()

@dp.message(BotStates.waiting_for_prompt, AdminFilter())
async def process_prompt(message: types.Message, state: FSMContext):
    async with async_session() as session:
        settings = await get_bot_setting(session)
        settings.prompt = message.text
        await session.commit()

    await state.clear()
    await message.answer("✅ Промпт успешно сохранен.", reply_markup=get_main_menu())

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
