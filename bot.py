from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from dotenv import load_dotenv
import os
import re
import json

# Загрузка переменных из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_states = {}

# Валидация
def is_valid_phone(phone: str) -> bool:
    clean = re.sub(r"[^\d]", "", phone)
    return len(clean) == 11 and clean.startswith(("7", "8"))

def is_valid_fio(text: str) -> bool:
    return all(char.isalpha() or char.isspace() for char in text) and len(text.strip().split()) >= 2

def is_valid_address(text: str) -> bool:
    return len(text.strip().split()) >= 2

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Открыть WebApp", web_app=WebAppInfo(url="https://konstantinius-cmd.github.io/rostelecom-webapp/"))],
        [InlineKeyboardButton("🔁 Перезапустить", callback_data="restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Здравствуйте! Чем я могу помочь?", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Здравствуйте! Чем я могу помочь?", reply_markup=reply_markup)

# Обработка inline-кнопок (если будут)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "restart":
        await start(update, context)
    elif query.data == "cancel":
        user_states.pop(chat_id, None)
        await query.message.reply_text("🔁 Ввод данных сброшен. Нажмите /start, чтобы начать заново.")
    elif query.data == "back":
        if chat_id not in user_states:
            return
        step = user_states[chat_id]["step"]
        if step == 2:
            user_states[chat_id]["step"] = 1
            await query.message.reply_text("Введите ваше ФИО:", reply_markup=cancel_markup())
        elif step == 3:
            user_states[chat_id]["step"] = 2
            await query.message.reply_text("Введите адрес (город, улица, дом, квартира):", reply_markup=back_cancel_markup())

# Сообщения от пользователя
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if text.lower() == "/cancel":
        user_states.pop(chat_id, None)
        await update.message.reply_text("🔁 Ввод данных сброшен. Нажмите /start, чтобы начать заново.")
        return

    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if state["step"] == 1:
        if not is_valid_fio(text):
            await update.message.reply_text("❗ Введите корректное ФИО (только буквы, минимум 2 слова).")
            return
        state["data"]["ФИО"] = text
        state["step"] = 2
        await update.message.reply_text("Введите адрес (город, улица, дом, квартира):", reply_markup=back_cancel_markup())

    elif state["step"] == 2:
        if not is_valid_address(text):
            await update.message.reply_text("❗ Введите корректный адрес.")
            return
        state["data"]["Адрес"] = text
        state["step"] = 3
        await update.message.reply_text("Введите номер телефона:", reply_markup=back_cancel_markup())

    elif state["step"] == 3:
        if not is_valid_phone(text):
            await update.message.reply_text("❗ Введите номер телефона (11 цифр, начиная с 7 или 8).")
            return
        state["data"]["Телефон"] = text
        info = state["data"]
        message = (
            "📥 Новая заявка на подключение:\n\n"
            f"👤 ФИО: {info['ФИО']}\n"
            f"🏠 Адрес: {info['Адрес']}\n"
            f"📞 Телефон: {info['Телефон']}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
        await update.message.reply_text("✅ Спасибо! Заявка отправлена специалисту.")
        user_states.pop(chat_id, None)

# Обработка WebApp данных
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔥 ПОЛУЧЕНЫ ДАННЫЕ ИЗ WEBAPP!")
    data = update.effective_message.web_app_data.data
    print(f"Данные от WebApp: {data}")  # Выводим данные для отладки

    try:
        parsed = json.loads(data)
        action = parsed.get("action")

        if action == "connect_service":
            chat_id = update.message.chat_id
            user_states[chat_id] = {"step": 1, "data": {}}
            await update.message.reply_text(
                "Вы выбрали подключение услуги. Введите ваше ФИО:",
                reply_markup=cancel_markup()
            )

        elif action == "info":
            await update.message.reply_text(f"ℹ️ {parsed.get('message')}")
        else:
            await update.message.reply_text("❗ Неизвестный тип действия из WebApp.")
    except Exception as e:
        print(f"Ошибка при обработке данных: {e}")
        await update.message.reply_text("❌ Ошибка при обработке данных из WebApp.")

# Кнопки управления
def cancel_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Изменить данные", callback_data="cancel")]])

def back_cancel_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Назад", callback_data="back"),
            InlineKeyboardButton("🔁 Изменить данные", callback_data="cancel")
        ]
    ])

# Для отладки всех сообщений (временно)
async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🪵 [debug] update:")
    print(update)

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # временный отладочный хендлер
    app.add_handler(MessageHandler(filters.ALL, debug_all))

    print("Бот запущен...")
    app.run_polling()
