import os
import logging
import psycopg2
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from translit import transliterate

# ===== НАЛАШТУВАННЯ =====
TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not TOKEN or not DATABASE_URL:
    raise ValueError("❌ TELEGRAM_TOKEN або DATABASE_URL не задано! Перевірте змінні оточення.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ===== СТАН FSM =====
class CorrectionStates(StatesGroup):
    waiting_for_correction = State()


# ===== РОБОТА З БД (POSTGRESQL) =====
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corrections (
            id SERIAL PRIMARY KEY,
            original TEXT,
            wrong TEXT,
            correct TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def save_correction(original, wrong, correct):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO corrections (original, wrong, correct) VALUES (%s, %s, %s)",
                       (original, wrong, correct))
        conn.commit()
        cursor.close()
        conn.close()
        logging.info(f"💾 Виправлення збережено в БД: {original} → {correct}")
        return True
    except Exception as e:
        logging.error(f"❌ Помилка БД: {e}")
        return False


# ===== СТВОРЕННЯ БОТА =====
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ===== КОМАНДА /START =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привіт! Я транслітерую корейські імена з латиниці в українську.\n"
        "Надішли мені текст (кожне ім'я з нового рядка), і я поверну результат.\n"
        "Якщо результат неправильний — натисни кнопку 'Виправити' під відповіддю.\n\n"
        "Команди:\n"
        "/start — показати це повідомлення\n"
        "/corrections — показати збережені виправлення\n"
        "/cancel — скасувати поточну операцію"
    )


# ===== КОМАНДА /CORRECTIONS =====
@dp.message(Command("corrections"))
async def cmd_corrections(message: types.Message):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT original, wrong, correct FROM corrections ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await message.answer("📭 База виправлень порожня.")
        else:
            text = "📋 Останні 10 виправлень:\n\n"
            for row in rows:
                text += f"• {row[0]} | {row[1]} → <b>{row[2]}</b>\n"
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"❌ Помилка при читанні з БД: {e}")
        await message.answer("❌ Не вдалося отримати виправлення з бази даних.")


# ===== ОБРОБНИК ТЕКСТОВИХ ПОВІДОМЛЕНЬ =====
@dp.message(~StateFilter(CorrectionStates.waiting_for_correction))
async def handle_message(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Будь ласка, введіть текст.")
        return

    lines = text.splitlines()
    results = []
    for line in lines:
        line = line.strip()
        if line:
            result = transliterate(line)
            results.append((line, result))

    if not results:
        await message.answer("Немає тексту для перекладу.")
        return

    reply_lines = []
    for orig, trans in results:
        reply_lines.append(f"📝 {orig} → {trans}")
    reply_text = "\n".join(reply_lines)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Виправити", callback_data="fix")]
        ]
    )

    await state.update_data(last_results=results)
    await message.answer(reply_text, reply_markup=keyboard)


# ===== ОБРОБНИК НАТИСКАННЯ КНОПКИ "ВИПРАВИТИ" =====
@dp.callback_query(F.data == "fix")
async def fix_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    results = data.get("last_results", [])
    if not results:
        await callback.message.edit_text("Немає даних для виправлення. Надішліть текст ще раз.")
        return

    lines = "\n".join([f"<b>{i + 1}.</b> {orig} → {trans}" for i, (orig, trans) in enumerate(results)])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_fix")]
        ]
    )

    prompt_text = "✏️ <b>Напишіть правильний варіант.</b>\n\n"
    if len(results) == 1:
        prompt_text += "Оскільки ім'я лише одне, просто напишіть правильний варіант (без цифр).\n\n"
    else:
        prompt_text += (
            "Формат:\n<b>Номер_рядка: виправлення</b>\n"
            "<i>(можна виправити кілька одразу, кожне з нового рядка)</i>\n\n"
            "Наприклад:\n1: Кім Су Хьон\n3: Пак Бо Ґом\n\n"
        )

    await callback.message.edit_text(
        f"{prompt_text}<b>Ось ваші результати:</b>\n{lines}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await state.set_state(CorrectionStates.waiting_for_correction)
    await state.update_data(fix_results=results)


# ===== ОБРОБНИК ОТРИМАННЯ ВИПРАВЛЕННЯ =====
@dp.message(StateFilter(CorrectionStates.waiting_for_correction))
async def receive_correction(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    data = await state.get_data()
    results = data.get("fix_results", [])

    if not Outer_results := results:
        await state.clear()
        await message.answer("❌ Немає даних для виправлення. Почніть спочатку.")
        return

    saved_corrections = []
    errors = []

    # 1. Логіка для ОДНОГО результату (без "1:")
    if len(results) == 1 and ":" not in user_input:
        orig, wrong = results[0]
        correction = user_input
        if save_correction(orig, wrong, correction):
            saved_corrections.append((orig, wrong, correction))
        else:
            errors.append("Не вдалося зберегти у базу даних.")

    # 2. Логіка для БАГАТЬОХ результатів або явного використання "Номер:"
    else:
        lines = user_input.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                errors.append(f"❌ Неправильний формат у '{line}'. Використовуйте 'Номер: виправлення'.")
                continue

            try:
                idx = int(parts[0].strip()) - 1
                correction = parts[1].strip()

                if idx < 0 or idx >= len(results):
                    errors.append(f"❌ Номер {idx + 1} поза межами (всього {len(results)}).")
                    continue

                orig, wrong = results[idx]
                if save_correction(orig, wrong, correction):
                    saved_corrections.append((orig, wrong, correction))
                else:
                    errors.append(f"❌ Помилка збереження для '{orig}'.")
            except ValueError:
                errors.append(f"❌ '{parts[0]}' не є числом у рядку '{line}'.")

    # Формуємо відповідь користувачу
    response_text = ""
    if saved_corrections:
        response_text += "✅ <b>Виправлення збережено:</b>\n"
        for orig, wrong, correct in saved_corrections:
            response_text += f"• <i>{orig}</i>: {wrong} → <b>{correct}</b>\n"

    if errors:
        response_text += "\n⚠️ <b>Помилки:</b>\n" + "\n".join(errors)

    if not response_text:
        response_text = "Нічого не було змінено. Перевірте формат."

    await message.answer(response_text, parse_mode="HTML")
    
    # Якщо все пройшло успішно і без помилок — закриваємо стан FSM
    if saved_corrections and not errors:
        await message.answer("🔄 Надсилай наступне ім'я.")
        await state.clear()


# ===== ОБРОБНИК СКАСУВАННЯ (через інлайн-кнопку) =====
@dp.callback_query(F.data == "cancel_fix")
async def cancel_fix_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Операцію скасовано.")


# ===== ОБРОБНИК КОМАНДИ /CANCEL =====
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Операцію скасовано.")


# ===== ЗАПУСК БОТА =====
async def main():
    init_db()  # Створення таблиці в Supabase, якщо її немає
    logging.info("🚀 Бот запускається з хмарною базою PostgreSQL...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
