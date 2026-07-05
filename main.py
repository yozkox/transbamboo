import os
import logging
import psycopg2
import asyncio
from threading import Thread
from flask import Flask
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

if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не задано! Додайте змінну оточення на Render.")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не задано! Додайте змінну оточення на Render.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ===== FLASK ДЛЯ HEALTH CHECK =====
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Бот працює!"

@flask_app.route('/health')
def health():
    return "OK", 200

# ===== БАЗА ДАНИХ (Supabase PostgreSQL) =====
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS corrections (
                id SERIAL PRIMARY KEY,
                original TEXT,
                wrong TEXT,
                correct TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ Таблиця створена або вже існує в Supabase.")
    except Exception as e:
        logging.error(f"❌ Помилка створення таблиці: {e}")
        raise

def save_correction(original, wrong, correct):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO corrections (original, wrong, correct) VALUES (%s, %s, %s)",
            (original, wrong, correct)
        )
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"💾 Збережено: {original} → {correct}")
        return True
    except Exception as e:
        logging.error(f"❌ Помилка БД: {e}")
        return False

# ===== СТАН FSM =====
class CorrectionStates(StatesGroup):
    waiting_for_correction = State()

# ===== СТВОРЕННЯ БОТА =====
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ===== КОМАНДИ =====
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

@dp.message(Command("corrections"))
async def cmd_corrections(message: types.Message):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT original, wrong, correct FROM corrections ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()

        if not rows:
            await message.answer("📭 База виправлень порожня.")
        else:
            text = "📋 Останні 10 виправлень:\n\n"
            for row in rows:
                text += f"• {row[0]} | {row[1]} → <b>{row[2]}</b>\n"
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"❌ Помилка читання: {e}")
        await message.answer("❌ Не вдалося отримати виправлення.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Операцію скасовано.")

# ===== ОБРОБНИК ПОВІДОМЛЕНЬ =====
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

    reply_lines = [f"📝 {orig} → {trans}" for orig, trans in results]
    reply_text = "\n".join(reply_lines)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Виправити", callback_data="fix")]
        ]
    )

    await state.update_data(last_results=results)
    await message.answer(reply_text, reply_markup=keyboard)

# ===== ОБРОБНИК ВИПРАВЛЕННЯ =====
@dp.callback_query(F.data == "fix")
async def fix_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    results = data.get("last_results", [])
    if not results:
        await callback.message.edit_text("Немає даних для виправлення.")
        return

    lines = "\n".join([f"<b>{i + 1}.</b> {orig} → {trans}" for i, (orig, trans) in enumerate(results)])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_fix")]
        ]
    )

    prompt_text = "✏️ <b>Напишіть правильний варіант.</b>\n\n"
    if len(results) == 1:
        prompt_text += "Просто напишіть правильний варіант (без цифр).\n\n"
    else:
        prompt_text += (
            "Формат: <b>Номер_рядка: виправлення</b>\n"
            "Наприклад:\n1: Кім Су Хьон\n3: Пак Бо Ґом\n\n"
        )

    await callback.message.edit_text(
        f"{prompt_text}<b>Ось ваші результати:</b>\n{lines}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await state.set_state(CorrectionStates.waiting_for_correction)
    await state.update_data(fix_results=results)

@dp.message(StateFilter(CorrectionStates.waiting_for_correction))
async def receive_correction(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    data = await state.get_data()
    results = data.get("fix_results", [])

    if not results:
        await state.clear()
        await message.answer("❌ Дані втрачено. Почніть спочатку.")
        return

    saved = []
    errors = []

    if len(results) == 1 and ":" not in user_input:
        orig, wrong = results[0]
        if save_correction(orig, wrong, user_input):
            saved.append((orig, wrong, user_input))
        else:
            errors.append("Не вдалося зберегти.")
    else:
        for line in user_input.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                errors.append(f"❌ Неправильний формат: '{line}'")
                continue
            try:
                idx_str, correct = line.split(":", 1)
                idx = int(idx_str.strip()) - 1
                correct = correct.strip()
                if idx < 0 or idx >= len(results):
                    errors.append(f"❌ Номер {idx+1} поза межами.")
                    continue
                orig, wrong = results[idx]
                if save_correction(orig, wrong, correct):
                    saved.append((orig, wrong, correct))
                else:
                    errors.append(f"❌ Помилка збереження для '{orig}'.")
            except ValueError:
                errors.append(f"❌ Не число: '{idx_str}'")

    response = ""
    if saved:
        response += "✅ <b>Збережено:</b>\n" + "\n".join(
            f"• {orig}: {wrong} → <b>{corr}</b>" for orig, wrong, corr in saved
        ) + "\n"
    if errors:
        response += "\n⚠️ <b>Помилки:</b>\n" + "\n".join(errors)
    if not response:
        response = "Нічого не змінено."

    await message.answer(response, parse_mode="HTML")
    if saved and not errors:
        await state.clear()

@dp.callback_query(F.data == "cancel_fix")
async def cancel_fix_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Скасовано.")

# ===== ЗАПУСК =====
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

async def start_bot():
    init_db()
    logging.info(f"🚀 Бот запущено з базою Supabase.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
