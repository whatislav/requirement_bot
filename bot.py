import asyncio
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import database as db

# ---------------------------------------------------------------------------
# Configuration
ADMIN_IDS = {430378049, 732877680}  # Telegram user IDs allowed to use admin commands
# ---------------------------------------------------------------------------
# You can export BOT_TOKEN=... or replace the placeholder below.
TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
if TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    raise RuntimeError(
        "Please set the BOT_TOKEN environment variable or edit bot.py with your token."
    )

# Ensure voices directory exists (makes it easier for users to notice missing files)
Path("voices").mkdir(exist_ok=True)
# Directory to store uploaded voice resumes
Path("uploads").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------


class Form(StatesGroup):
    waiting_resume = State()


class VoiceUpdate(StatesGroup):
    waiting_voice = State()


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
        "Вы сотрудник кадрового агентства, выберите вакансию", reply_markup=keyboard
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

    # Подтверждаем нажатие
    await callback.answer()

    # (Кнопки больше не скрываются, поэтому не обновляем клавиатуру)

    # 2. Greeting text
    await callback.message.answer(
        "Добрый день! В агентство поступил запрос от компании-работодателя"
    )

    # 3. Voice message corresponding to the vacancy number
    voice_ref = info[2]
    try:
        if os.path.exists(voice_ref):
            await callback.message.answer_voice(types.FSInputFile(voice_ref))
        else:
            await callback.message.answer_voice(voice_ref)
    except Exception:
        await callback.message.answer(
            f"(Не удалось отправить голосовое сообщение для {info[1]})"
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


@dp.message(Command("setvoice"))
async def cmd_set_voice(message: types.Message, state: FSMContext):
    """Admin command to start voice replacement workflow: /setvoice <vacancy_id>"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для этой команды.")
        return

    # Expect argument like /setvoice 3
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /setvoice <ID вакансии>")
        return

    vac_id = int(parts[1])
    if vac_id not in range(1, 6):
        await message.answer("ID вакансии должен быть от 1 до 5")
        return

    await state.set_state(VoiceUpdate.waiting_voice)
    await state.update_data(vacancy_id=vac_id)
    await message.answer(f"Отправьте новое голосовое сообщение для вакансии {vac_id}")


@dp.message(VoiceUpdate.waiting_voice, F.voice | F.document)
async def on_new_voice(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для этой команды.")
        return

    data = await state.get_data()
    vac_id = data.get("vacancy_id")

    # Case 1: admin sent a native voice message
    if message.voice:
        file_id = message.voice.file_id
        await db.update_voice_path(vac_id, file_id)
        await message.answer(f"Голосовое сообщение для вакансии {vac_id} обновлено ✅")
        await state.clear()
        return

    # Case 2: admin sent an .ogg file as document
    doc = message.document
    if not doc or not (doc.file_name or "").lower().endswith(".ogg"):
        await message.answer("Пожалуйста, отправьте голосовое сообщение или .ogg файл.")
        return

    # Download the document locally
    file_info = await message.bot.get_file(doc.file_id)
    local_path = Path("uploads") / f"vac{vac_id}_{doc.file_unique_id}.ogg"
    await message.bot.download_file(file_info.file_path, destination=local_path)

    # Save into voices directory with standard naming
    voices_dst = Path("voices") / f"voice{vac_id}.ogg"
    local_path.replace(voices_dst)

    await db.update_voice_path(vac_id, str(voices_dst))
    await message.answer(f"Файл .ogg получен и установлен для вакансии {vac_id} ✅")
    await state.clear()


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    # Allow only predefined admin IDs
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для этой команды.")
        return
    """Admin command to reset vacancy availability."""
    await db.reset_vacancies()
    keyboard = await build_vacancies_keyboard()
    await message.answer("Все вакансии сброшены и снова доступны", reply_markup=keyboard)

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