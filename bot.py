import re  # Добавляем импорт для регулярных выражений
from dotenv import load_dotenv
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

user_states = {}

# Проверка телефона
def is_valid_phone(phone: str) -> bool:
    clean = re.sub(r"[^\d]", "", phone)
    return len(clean) == 11 and clean.startswith(("7", "8"))

# Проверка ФИО
def is_valid_fio(text: str) -> bool:
    return all(char.isalpha() or char.isspace() for char in text) and len(text.strip().split()) >= 2

# Проверка адреса
def is_valid_address(text: str) -> bool:
    return len(text.strip().split()) >= 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📡 Подключение новых услуг", callback_data="new_service")],
        [InlineKeyboardButton("💳 Смена тарифа", callback_data="change_tariff")],
        [InlineKeyboardButton("🛠 Технические неполадки", callback_data="issues")],
        [InlineKeyboardButton("🔁 Перезапустить", callback_data="restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Здравствуйте! Чем я могу помочь?", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Здравствуйте! Чем я могу помочь?", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "new_service":
        user_states[chat_id] = {"step": 1, "data": {}}
        # Добавляем выбор услуги
        keyboard = [
            [InlineKeyboardButton("🌐 Интернет", callback_data="service_internet")],
            [InlineKeyboardButton("📺 Интернет с телевидением", callback_data="service_internet_tv")],
            [InlineKeyboardButton("🌐📺 Интернет, телевидение и сим-карта", callback_data="service_internet_tv_sim")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Что вы хотите подключить?", reply_markup=reply_markup)

    elif query.data == "service_internet":
        user_states[chat_id]["data"]["Услуга"] = "Интернет"
        await query.message.reply_text("Вы выбрали подключение Интернета. Введите ваше ФИО:")
        user_states[chat_id]["step"] = 2
        await query.message.reply_text("Введите ваше ФИО:")

    elif query.data == "service_internet_tv":
        user_states[chat_id]["data"]["Услуга"] = "Интернет с телевидением"
        await query.message.reply_text("Вы выбрали подключение Интернета с телевидением. Введите ваше ФИО:")
        user_states[chat_id]["step"] = 2
        await query.message.reply_text("Введите ваше ФИО:")

    elif query.data == "service_internet_tv_sim":
        user_states[chat_id]["data"]["Услуга"] = "Интернет, телевидение и сим-карта"
        await query.message.reply_text("Вы выбрали подключение Интернета, телевидения и сим-карты. Введите ваше ФИО:")
        user_states[chat_id]["step"] = 2
        await query.message.reply_text("Введите ваше ФИО:")

    # Если другие кнопки, например для смены тарифа или технических неполадок
    elif query.data == "change_tariff":
        await query.message.reply_text(
            "Если вы уже пользуетесь услугами компании Ростелеком и хотите сменить тариф — обратитесь по номеру горячей линии: 8 800 100 08 00",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="restart")]]),
        )
    elif query.data == "issues":
        await query.message.reply_text(
            "Для решения технических проблем посетите https://komi.rt.ru/care или позвоните: 8 800 100 08 00",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="restart")]]),
        )
    elif query.data == "restart":
        await start(update, context)
    elif query.data == "cancel":
        user_states.pop(chat_id, None)
        await query.message.reply_text(
            "🔁 Ввод данных сброшен. Вы можете начать заново, если допустили ошибку. Нажмите /start.")
    elif query.data == "back":
        if chat_id not in user_states:
            return

        state = user_states[chat_id]
        step = state.get("step")

        if step == 2:
            state["step"] = 1
            await query.message.reply_text("Введите ваше ФИО:", reply_markup=cancel_markup())
        elif step == 3:
            state["step"] = 2
            await query.message.reply_text("Введите адрес (город, улица, дом, квартира):",
                                           reply_markup=back_cancel_markup())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if text.lower() == "/cancel":
        user_states.pop(chat_id, None)
        await update.message.reply_text(
            "🔁 Ввод данных сброшен. Вы можете начать заново, если допустили ошибку. Нажмите /start.")
        return

    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if state["step"] == 2:
        if not is_valid_fio(text):
            await update.message.reply_text(
                "❗ Пожалуйста, введите корректное ФИО (минимум имя и фамилия, только буквы).")
            return

        state["data"]["ФИО"] = text
        state["step"] = 3
        await update.message.reply_text(
            "Введите адрес (город, улица, дом, квартира):",
            reply_markup=back_cancel_markup()
        )
    elif state["step"] == 3:
        if not is_valid_address(text):
            await update.message.reply_text(
                "❗ Пожалуйста, введите корректный адрес (например: г. Сыктывкар, ул. Ленина, д. 1, кв. 2).")
            return

        state["data"]["Адрес"] = text
        state["step"] = 4
        await update.message.reply_text(
            "Введите номер телефона:",
            reply_markup=back_cancel_markup()
        )
    elif state["step"] == 4:
        if not is_valid_phone(text):
            await update.message.reply_text(
                "❗ Пожалуйста, введите корректный номер телефона (начиная с 7 или 8, 11 цифр).")
            return

        state["data"]["Телефон"] = text

        # Информация по заявке
        info = state["data"]
        message = (
            "📥 Новая заявка на подключение:\n\n"
            f"👤 ФИО: {info['ФИО']}\n"
            f"🏠 Адрес: {info['Адрес']}\n"
            f"📞 Телефон: {info['Телефон']}\n"
            f"🛠 Услуга: {info['Услуга']}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
        await update.message.reply_text(
            "✅ Спасибо! Заявка отправлена специалисту. В скором времни с вами свяжется наш менеджер!")
        user_states.pop(chat_id, None)


# Кнопка "Изменить данные"
def cancel_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Изменить данные", callback_data="cancel")]])


# Кнопки "Назад" и "Изменить данные"
def back_cancel_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Назад", callback_data="back"),
            InlineKeyboardButton("🔁 Изменить данные", callback_data="cancel")
        ]
    ])


# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()
