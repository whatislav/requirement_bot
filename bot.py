import asyncio
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import database as db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# You can export BOT_TOKEN=... or replace the placeholder below.
TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
if TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    raise RuntimeError(
        "Please set the BOT_TOKEN environment variable or edit bot.py with your token."
    )

# Ensure voices directory exists (makes it easier for users to notice missing files)
Path("voices").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------


class Form(StatesGroup):
    waiting_resume = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def build_vacancies_keyboard() -> InlineKeyboardMarkup:
    """Create an inline keyboard with currently available vacancies."""
    vacancies = await db.get_available()
    buttons = [
        InlineKeyboardButton(text=title, callback_data=f"vac_{vac_id}")
        for vac_id, title in vacancies
    ]

    # If everything is taken, show a single disabled button
    if not buttons:
        buttons = [InlineKeyboardButton(text="Все вакансии заняты", callback_data="none")]

    # Arrange buttons in rows of 2 for better UX
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Bot & Dispatcher setup
# ---------------------------------------------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Show the main menu with available vacancies."""
    keyboard = await build_vacancies_keyboard()
    await message.answer(
        "Вы сотрудник кадрового агентства, выбирете вакансию", reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("vac_"))
async def on_vacancy_selected(callback: types.CallbackQuery, state: FSMContext):
    vac_id = int(callback.data.split("_", 1)[1])

    # Try to reserve the vacancy atomically
    info = await db.take_vacancy(vac_id)
    if info is None:
        await callback.answer("К сожалению, вакансия уже недоступна", show_alert=True)
        keyboard = await build_vacancies_keyboard()
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        return

    # Acknowledge button press (no popup needed)
    await callback.answer()

    # Refresh the menu in the original message so the button disappears for everyone
    keyboard = await build_vacancies_keyboard()
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    # 2. Greeting text
    await callback.message.answer(
        "Добрый день! В агентство поступил запрос от компании-работодателя"
    )

    # 3. Voice message corresponding to the vacancy number
    voice_path = info[2]
    if os.path.exists(voice_path):
        await callback.message.answer_voice(types.FSInputFile(voice_path))
    else:
        await callback.message.answer(
            f"(Отсутствует голосовое сообщение для {info[1]} — файл {voice_path} не найден)"
        )

    # 4. Prompt to upload CV
    await callback.message.answer("Вы можете загрузить резюме")

    # Set FSM state
    await state.set_state(Form.waiting_resume)
    await state.update_data(vacancy_id=info[0])


@dp.message(Form.waiting_resume, F.document)
async def on_resume_received(message: types.Message, state: FSMContext):
    # 6. Employer response
    await message.answer(
        "Ответ работодателя: Спасибо большое! Вы отличная команда! Ваш кандидат принят на работу!"
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Startup routine
# ---------------------------------------------------------------------------


async def main():
    # Prepare database
    await db.init_db()

    # Launch polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main()) 