import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler
)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing! Make sure to set it in Render's environment variables.")

ADMIN_ID = 1774865778
UPI_ID = '6382344469@jio'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

user_state = {}
user_screenshot_counter = {}

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'buy':
        query.message.reply_text(
            "🔥 Namaste React Course — Just ₹29!\n"
            "📌 How to Unlock the course payment link:\n"
            "1️⃣ Forward the promo message (below) with image to 3 Telegram groups\n"
            "2️⃣ Take screenshots\n"
            "3️⃣ Send them here via 📤 Submit Screenshots button\n\n"
            "📲 Join the Channel: https://t.me/+IEY3uiiKHfU4NzQ1\n"
            "❓ If you have any doubts, feel free to contact the admin 👉 @iam_akilesh07"
        )

        image_url = "https://i.postimg.cc/dtSLLGJ2/akl.png"
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_url,
            caption=("💻 *Namaste React Course Akshay Saini – Just ₹29!*\n"
                     "🎯 Project-Based | 50+ Hours | 3 Major Projects\n"
                     "✅ Latest React Practices + Interview Prep\n\n"
                     "📩 *DM 👉 @ashbolt_bot*\n"
                     "🚀 Limited Time Offer!"),
            parse_mode='Markdown'
        )

        keyboard = [[InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit')]]
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Now you can submit your 3 screenshots below 👇",
            reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'submit':
        context.bot.send_message(chat_id=query.message.chat_id, text="📤 Please upload your 3 screenshot proofs here one by one.")
        user_state[query.message.chat_id] = "collecting_screenshots"
        user_screenshot_counter[query.message.chat_id] = 0

    elif query.data == 'send_receipt':
        context.bot.send_message(chat_id=query.message.chat_id, text="📥 Please send your payment screenshot now.")
        user_state[query.message.chat_id] = "ready_to_receive_payment"

def handle_photos(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")

        if user_screenshot_counter[user_id] == 3:
            user_state[user_id] = "awaiting_payment_button"
            context.bot.send_message(
                chat_id=user_id,
                text=(f"✅ All 3 screenshots received!\n\n💸 Now pay ₹29 to:\n\n💰 *{UPI_ID}*"),
                parse_mode='Markdown')

            context.bot.send_photo(
                chat_id=user_id,
                photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                caption="📷 Scan this QR to pay ₹29\n\n❓ If you have any doubts, feel free to contact the admin 👉 @iam_akilesh07")

            keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')]]
            context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Click the button below *after* making the payment",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')

    elif user_state.get(user_id) == "ready_to_receive_payment":
        user_state[user_id] = "completed"
        context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        context.bot.send_message(
            chat_id=user_id,
            text=("🎉 Payment screenshot received and forwarded to admin.\n"
                  "🎓 Here is your course access link:\n"
                  "🔗 https://1024terabox.com/s/1F_FRmqIs_1HpALb7zUlM0g\n"
                  "🔑 Password: 7878"))

def handle_documents(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    file = update.message.document
    file_name = file.file_name.lower()

    if file_name.endswith(('.jpg', '.jpeg', '.png')):
        update.message.photo = [file]
        handle_photos(update, context)
    else:
        context.bot.send_message(chat_id=user_id, text="❌ Unsupported file type. Please send only JPG/PNG images.")

def submit_command(update: Update, context: CallbackContext):
    update.message.reply_text("📤 Please click 📤 Submit Screenshots option at top")

def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Unknown command. Use /start or tap buttons.")

# ✅ Run bot with webhook
def run_bot():
    PORT = int(os.environ.get("PORT", 8443))
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("submit", submit_command))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.photo, handle_photos))
    dp.add_handler(MessageHandler(Filters.document, handle_documents))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://ashbolt-telegram-bot.onrender.com/{BOT_TOKEN}"
    )

    print("🤖 Bot is running with webhook...")
    updater.idle()

run_bot()
