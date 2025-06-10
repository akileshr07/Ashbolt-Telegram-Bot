import os
import logging
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# === Environment Configuration ===
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 1774865778))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Example: https://ashbolt-bot.onrender.com
UPI_ID = '6382344469@jio'

if not BOT_TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ BOT_TOKEN and WEBHOOK_URL must be set in environment variables!")

# === Init Flask App and Telegram Bot ===
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0, use_context=True)

# === Logging Setup ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === User State Management ===
user_state = {}
user_screenshot_counter = {}
payment_proofs = {}

# === Command and Message Handlers ===
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')]]
    update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat_id
    query.answer()

    if query.data == 'buy':
        query.message.reply_text(
            "🔥 Namaste React Course — Just ₹29!\n"
            "📌 To Unlock the Course:\n"
            "1️⃣ Forward promo message to 3 groups\n"
            "2️⃣ Upload 3 screenshots here\n"
            "3️⃣ Pay ₹29 and send screenshot\n\n"
            "📲 Join Channel: https://t.me/+IEY3uiiKHfU4NzQ1\n"
            "❓ Contact admin 👉 @iam_akilesh07"
        )
        context.bot.send_photo(
            chat_id=user_id,
            photo="https://i.postimg.cc/nVYkp19r/6213087660646450101-120.jpg",
            caption=(
                "💻 *Namaste React Course by Akshay Saini – Just ₹29!*\n"
                "🎯 50+ Hours of Project-Based Learning\n"
                "✅ Covers React, Hooks, Redux, Routing\n"
                "👨‍💻 For Beginners & Experienced Devs\n"
                "🔗 https://t.me/ashbolt_bot\n"
                "🌟 Lifetime Access"
            ),
            parse_mode='Markdown'
        )
        context.bot.send_message(
            chat_id=user_id,
            text="👇 Submit your 3 screenshots 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit')]
            ])
        )

    elif query.data == 'submit':
        user_state[user_id] = "collecting_screenshots"
        user_screenshot_counter[user_id] = 0
        context.bot.send_message(chat_id=user_id, text="📤 Upload your 3 screenshots one by one.")

    elif query.data == 'send_receipt':
        user_state[user_id] = "awaiting_payment"
        context.bot.send_message(chat_id=user_id, text="📥 Send your ₹29 UPI payment screenshot.\n⚠️ Fake UTRs will be banned.")

    elif query.data.startswith("approve_"):
        target_id = int(query.data.split("_")[1])
        context.bot.send_message(chat_id=target_id,
                                 text="✅ Payment Approved!\n🎓 Course Link: https://1024terabox.com/s/1F_FRmqIs_1HpALb7zUlM0g\n🔑 Password: 7878")
        context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ Approved access for user ID: {target_id}")

    elif query.data.startswith("reject_"):
        target_id = int(query.data.split("_")[1])
        context.bot.send_message(chat_id=target_id, text="❌ Payment not accepted. Please try again.")
        context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Rejected access for user ID: {target_id}")

def handle_photos(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")

        if user_screenshot_counter[user_id] == 3:
            user_state[user_id] = "waiting_payment"
            context.bot.send_message(
                chat_id=user_id,
                text=f"✅ All 3 screenshots received!\n💸 Pay ₹29 to: *{UPI_ID}*",
                parse_mode='Markdown'
            )
            context.bot.send_photo(
                chat_id=user_id,
                photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                caption="📷 Scan to Pay ₹29"
            )
            context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Tap below after payment",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt")]
                ])
            )

    elif user_state.get(user_id) == "awaiting_payment":
        user_state[user_id] = "awaiting_approval"
        payment_proofs[user_id] = update.message.message_id

        context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")]
        ])
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 Payment received from user ID: {user_id}",
            reply_markup=keyboard
        )
        context.bot.send_message(
            chat_id=user_id,
            text="📤 Payment screenshot sent to admin for review.\nPlease wait for approval."
        )

def handle_documents(update: Update, context: CallbackContext):
    file = update.message.document
    if file.mime_type in ['image/jpeg', 'image/png']:
        update.message.photo = [file]
        handle_photos(update, context)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="❌ Only JPG/PNG images are supported.")

def submit_command(update: Update, context: CallbackContext):
    update.message.reply_text("📤 Tap the 'Submit Screenshots' button to begin.")

def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Unknown command. Please use /start or buttons.")

# === Register Handlers ===
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("submit", submit_command))
dispatcher.add_handler(CallbackQueryHandler(button_handler))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_photos))
dispatcher.add_handler(MessageHandler(Filters.document, handle_documents))
dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

# === Webhook Endpoint ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

# === Health Check ===
@app.route("/", methods=["GET"])
def home():
    return "🤖 AshBolt Bot is running via webhook!", 200

# === Webhook Setup & Flask Launch ===
if __name__ == "__main__":
    bot.delete_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print("✅ Webhook set successfully!")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
