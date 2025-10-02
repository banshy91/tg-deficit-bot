import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

# Состояния
WEIGHT, DEFICIT = range(2)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Введите ваш вес в кг:")
    return WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        context.user_data['weight'] = weight

        keyboard = [
            [InlineKeyboardButton("Быстрое похудение (−30%)", callback_data='30')],
            [InlineKeyboardButton("Умеренное (−20%)", callback_data='20')],
            [InlineKeyboardButton("Комфортное (−10%)", callback_data='10')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите тип дефицита:", reply_markup=reply_markup)
        return DEFICIT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число для веса.")
        return WEIGHT

async def deficit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    deficit_percent = int(query.data)
    weight = context.user_data['weight']

    protein = 2 * weight
    carbs = 4 * weight
    fat = 1 * weight

    total_calories = protein*4 + carbs*4 + fat*9
    calories_target = total_calories * (100 - deficit_percent)/100

    carb_fat_ratio = (carbs*4) / (carbs*4 + fat*9)
    carbs_new = ((calories_target - protein*4) * carb_fat_ratio) / 4
    fat_new = ((calories_target - protein*4) * (1 - carb_fat_ratio)) / 9

    keyboard = [[InlineKeyboardButton("Новый расчет", callback_data='restart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    response = f"Тип похудения: {deficit_percent}%\n" \
               f"Калории: {calories_target:.0f} ккал\n" \
               f"Белки: {protein:.1f} г\n" \
               f"Углеводы: {carbs_new:.1f} г\n" \
               f"Жиры: {fat_new:.1f} г"

    await query.edit_message_text(response, reply_markup=reply_markup)
    return DEFICIT

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите ваш вес в кг:")
    return WEIGHT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Расчет отменен.")
    return ConversationHandler.END

# --- Основная часть ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # https://tg-deficit-bot.onrender.com

app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
        DEFICIT: [
            CallbackQueryHandler(deficit, pattern='^(30|20|10)$'),
            CallbackQueryHandler(restart, pattern='^restart$')
        ]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

app.add_handler(conv_handler)

# Установка webhook
async def set_webhook():
    await app.bot.set_webhook(f"{WEBHOOK_URL}{TOKEN}")
    print("Webhook установлен!")

asyncio.run(set_webhook())

# Запуск веб-сервера на Render
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=f"{WEBHOOK_URL}{TOKEN}"
)
