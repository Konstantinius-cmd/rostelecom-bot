from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import re
import json

BOT_TOKEN = "7792379435:AAG0cvZ4zyQNjW76Ktigui2UUBOzYSozcn0"
ADMIN_ID = 911720830

user_states = {}

# Проверки
def is_valid_phone(phone: str) -> bool:
    clean = re.sub(r"[^\d]", "", phone)
    return len(clean) == 11 and clean.startswith(("7", "8"))

def is_valid_fio(text: str) -> bool:
    return all(char.isalpha() or char.isspace() for char in text) and len(text.strip().split()) >= 2

def is_valid_address(text: str) -> bool:
    return len(text.strip().split()) >= 2

# Старт / главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🚀 Открыть WebApp", web_app=WebAppInfo(url="https://konstantinius-cmd.github.io/rostelecom-webapp/"))],
        [KeyboardButton("🔁 Перезапустить")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
        await query.message.reply_text("🔁 Ввод данных сброшен. Вы можете начать заново. Нажмите /start.")
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

# Обработка WebApp данных
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔥 ПОЛУЧЕНЫ ДАННЫЕ ИЗ WEBAPP!")
    print(update.effective_message.web_app_data.data)  # отладка
    data = update.effective_message.web_app_data.data
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
        print("❌ Ошибка:", e)
        await update.message.reply_text("❌ Ошибка при обработке данных из WebApp.")

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if text == "🔁 Перезапустить":
        await start(update, context)
        return

    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if state["step"] == 1:
        if not is_valid_fio(text):
            await update.message.reply_text("❗ Пожалуйста, введите корректное ФИО (только буквы, минимум 2 слова).")
            return
        state["data"]["ФИО"] = text
        state["step"] = 2
        await update.message.reply_text("Введите адрес (город, улица, дом, квартира):", reply_markup=back_cancel_markup())

    elif state["step"] == 2:
        if not is_valid_address(text):
            await update.message.reply_text("❗ Пожалуйста, введите корректный адрес (например: г. Сыктывкар, ул. Ленина, д. 1, кв. 2).")
            return
        state["data"]["Адрес"] = text
        state["step"] = 3
        await update.message.reply_text("Введите номер телефона:", reply_markup=back_cancel_markup())

    elif state["step"] == 3:
        if not is_valid_phone(text):
            await update.message.reply_text("❗ Пожалуйста, введите корректный номер телефона (11 цифр, начиная с 7 или 8).")
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

# Кнопки "Назад" и "Изменить данные"
def cancel_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Изменить данные", callback_data="cancel")]])

def back_cancel_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Назад", callback_data="back"),
        InlineKeyboardButton("🔁 Изменить данные", callback_data="cancel")
    ]])

# Для отладки всего подряд (по желанию)
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

    print("Бот запущен...")
    app.run_polling()
