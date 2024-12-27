from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackQueryHandler, Application
import sqlite3
from urllib.parse import urlparse
import random

TOKEN = "7691305676:AAEiV9vqm2cqCMq-ZJbxWm_6QtnuvzsaAW0"

# Функція для підключення до бази даних
def get_db_connection():
    conn = sqlite3.connect('links.db')
    conn.row_factory = sqlite3.Row
    return conn

# Функція для створення таблиці в базі даних
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

# Функція для отримання домену з URL
def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

# Обработчик для команды /start
async def start(update, context):
    keyboard = [
        [KeyboardButton("➕ Додати")],
        [KeyboardButton("📋 Переглянути")],
        [KeyboardButton("🎲 Шара")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Привіт! Виберіть дію:", reply_markup=reply_markup)

# Обработчик для кнопки "➕ Додати"
async def handle_add(update, context):
    await update.message.reply_text("Введіть дані у форматі: Назва, Посилання, Оцінка, Теги")

# Обработчик для кнопки "📋 Переглянути"
async def handle_view(update, context):
    await show_page(update, context, page=1)

# Обработчик для кнопки "🎲 Шара" (случайная запись)
async def handle_random(update, context):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, url, rating, tags FROM links")
        rows = cursor.fetchall()

        if rows:
            random_record = random.choice(rows)
            response = f"Назва: {random_record[0]}\nОцінка: {random_record[2]}\nТеги: {random_record[3]}\n\n" \
                       f"Посилання: [Тык]({random_record[1]})"  # Привязка ссылки к тексту
        else:
            response = "База даних пуста."
    
    await update.message.reply_text(response, parse_mode="Markdown")

# Функция для отображения страницы
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

        # Создаем кнопки для навигации
        keyboard = []
        
        # Добавляем кнопку "Назад", если страница больше 1
        if page > 1:
            keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))

        # Проверяем, есть ли еще страницы вперед
        cursor.execute("SELECT COUNT(*) FROM links")
        total_records = cursor.fetchone()[0]
        if page * 5 < total_records:
            keyboard.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))

        # Если есть кнопки, то передаем их в InlineKeyboardMarkup
        if keyboard:
            reply_markup = InlineKeyboardMarkup([keyboard])

            # Если запрос пришел от callback, используем query.message
            if update.callback_query:
                await update.callback_query.message.edit_text(response, reply_markup=reply_markup, parse_mode="Markdown")
                await update.callback_query.answer()
            else:
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

# Обработчик для перехода по страницам
async def paginate(update, context):
    query = update.callback_query
    page = int(query.data.split("_")[1])
    
    # Обновляем сообщение с новой страницей
    await show_page(update, context, page=page)
    await query.answer()

# Обработчик для добавления данных в базу
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

# Основная функция для запуска бота
def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Обработчики для кнопок
    application.add_handler(MessageHandler(filters.Text("➕ Додати"), handle_add))
    application.add_handler(MessageHandler(filters.Text("📋 Переглянути"), handle_view))
    application.add_handler(MessageHandler(filters.Text("🎲 Шара"), handle_random))  # Обработчик для "Шара"
    application.add_handler(MessageHandler(filters.Text(), add_link))  # Обработчик для добавления данных

    # Обработчик для навигации по страницам
    application.add_handler(CallbackQueryHandler(paginate, pattern=r"^page_\d+$"))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
