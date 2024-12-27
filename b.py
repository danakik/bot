from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackQueryHandler, Application
import sqlite3
from urllib.parse import urlparse
import random

TOKEN = "7691305676:AAEiV9vqm2cqCMq-ZJbxWm_6QtnuvzsaAW0"

def get_db_connection():
    conn = sqlite3.connect('links.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT,
            rating INTEGER,
            tags TEXT
        )
        """)
        conn.commit()

create_table()

def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

async def start(update, context):
    keyboard = [
        [KeyboardButton("➕ Додати")],
        [KeyboardButton("📋 Переглянути")],
        [KeyboardButton("🎲 Шара")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привіт! Виберіть дію:", reply_markup=reply_markup)

async def handle_add(update, context):
    await update.message.reply_text("Введіть дані у форматі: Назва, Посилання, Оцінка, Теги")

async def handle_view(update, context):
    await show_page(update, context, page=1)

async def handle_random(update, context):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, url, rating, tags FROM links")
        rows = cursor.fetchall()
        if rows:
            random_record = random.choice(rows)
            response = f"Назва: {random_record[0]}\nОцінка: {random_record[2]}\nТеги: {random_record[3]}\n\nПосилання: [Тык]({random_record[1]})"
        else:
            response = "База даних пуста."
    await update.message.reply_text(response, parse_mode="Markdown")

async def show_page(update, context, page=1):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, url, rating, tags FROM links LIMIT 5 OFFSET ?", ((page - 1) * 5,))
        rows = cursor.fetchall()
        if rows:
            response = "\n\n".join(
                [f"Назва: {row[0]}\nОцінка: {row[2]}\nТеги: {row[3]}\nПосилання: [Тык]({row[1]})" for row in rows]
            )
        else:
            response = "База даних пуста."
        keyboard = []
        if page > 1:
            keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        cursor.execute("SELECT COUNT(*) FROM links")
        total_records = cursor.fetchone()[0]
        if page * 5 < total_records:
            keyboard.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
        if keyboard:
            reply_markup = InlineKeyboardMarkup([keyboard])
            if update.callback_query:
                await update.callback_query.message.edit_text(response, reply_markup=reply_markup, parse_mode="Markdown")
                await update.callback_query.answer()
            else:
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

async def paginate(update, context):
    query = update.callback_query
    page = int(query.data.split("_")[1])
    await show_page(update, context, page=page)
    await query.answer()

async def add_link(update, context):
    try:
        data = update.message.text.split(",", 3)
        if len(data) == 4:
            name, url, rating, tags = map(str.strip, data)
            rating = int(rating)
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO links (name, url, rating, tags) VALUES (?, ?, ?, ?)", (name, url, rating, tags))
                conn.commit()
            await update.message.reply_text("Ссилка успішно додана!")
        else:
            await update.message.reply_text("Неправильний формат. Використовуйте: Назва, Посилання, Оцінка, Теги")
    except ValueError:
        await update.message.reply_text("Неправильний формат оцінки. Використовуйте ціле число для оцінки.")
    except Exception as e:
        await update.message.reply_text(f"Сталася помилка: {e}")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text("➕ Додати"), handle_add))
    application.add_handler(MessageHandler(filters.Text("📋 Переглянути"), handle_view))
    application.add_handler(MessageHandler(filters.Text("🎲 Шара"), handle_random))
    application.add_handler(MessageHandler(filters.Text(), add_link))
    application.add_handler(CallbackQueryHandler(paginate, pattern=r"^page_\d+$"))
    application.run_polling()

if __name__ == "__main__":
    main()
