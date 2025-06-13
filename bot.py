import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ✅ Bot Configuration - Get from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID')) # Convert to int
UPI_ID = os.environ.get('UPI_ID')

# Validate if environment variables are set
if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable not set. Exiting.")
    exit(1)
if not ADMIN_ID:
    logging.error("ADMIN_ID environment variable not set. Exiting.")
    exit(1)
if not UPI_ID:
    logging.error("UPI_ID environment variable not set. Exiting.")
    exit(1)

# ✅ Logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

# ✅ User State
user_state = {}
user_screenshot_counter = {}

# ✅ Helper: Notify admin

def notify_admin(bot_instance: Bot, user, message):
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name}"
    admin_message += f" {user.last_name}" if user.last_name else ""
    admin_message += f"\n📧 Username: @{user.username}" if user.username else "\n📧 Username: N/A"

    try:
        bot_instance.send_message(chat_id=ADMIN_ID, text=admin_message)
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")

# ✅ /start

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=reply_markup
    )
    notify_admin(context.bot, user, "Started the bot")

# ✅ Callback Buttons

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = query.from_user

    if query.data == 'buy':
        notify_admin(context.bot, user, "Clicked 'Buy Course' button")

        query.message.reply_text(
            "🔥 Namaste React Course — Just ₹29!\n"
            "🚀 Limited Time Offer – Act Fast!\n\n"
            "🎯 Learn React from Scratch with Lifetime Access, Projects, Notes & More!\n\n"
            "📌 How to Unlock the Discount:\n"
            "1️⃣ Share the promo message (below) to 3 Telegram or WhatsApp groups\n"
            "2️⃣ Take screenshots\n"
            "3️⃣ Send them here via 📤 Submit Screenshots button\n\n"
            "📲 Join the Channel: https://t.me/+IEY3uiiKHfU4NzQ1\n\n"
            "❓ If you have any doubts, feel free to contact the admin 👉 @iam_akilesh07"
        )

        image_url = "https://i.postimg.cc/nVYkp19r/6213087660646450101-120.jpg"
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_url,
            caption=("💻 Namaste React Course by Akshay Saini – Just $0.35 / ₹29\n"
                     "🎯 50+ Hours of Project-Based Learning\n\n"
                     "🚀 Includes 3 Major Projects + Interview Prep\n\n"
                     "👨‍💻 Perfect for Beginners & Experienced Developers\n\n"
                     "🎯 Lifetime Access | Projects | Notes\n\n"
                     "🔗 Join Now 👉 https://t.me/ashbolt_bot\n"
                     "📲 Or Search 'ashbolt_bot' on Telegram\n"
                     "🚀 Limited Time Offer")
        )

        keyboard = [[InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit')]]
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Now you can submit your 3 screenshots below 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == 'submit':
        user_state[user.id] = "collecting_screenshots"
        user_screenshot_counter[user.id] = 0
        context.bot.send_message(chat_id=query.message.chat_id, text="📤 Please upload your 3 screenshots now.")

    elif query.data == 'send_receipt':
        user_state[user.id] = "ready_to_receive_payment"
        context.bot.send_message(chat_id=query.message.chat_id, text="📥 Please send your payment screenshot now.")

# ✅ Handle Photo Messages

def handle_photos(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = update.message.from_user

    if user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")

        if user_screenshot_counter[user_id] >= 3:
            user_state[user_id] = "awaiting_payment"
            notify_admin(context.bot, user, "Submitted 3 screenshots")

            context.bot.send_message(
                chat_id=user_id,
                text=(f"✅ All 3 screenshots received!\n\n"
                      f"💸 Now pay ₹29 to:\n\n💰 *{UPI_ID}*\n\n"
                      f"❓ If you have any doubts, feel free to contact the admin 👉 @iam_akilesh07"),
                parse_mode='Markdown'
            )
            context.bot.send_photo(
                chat_id=user_id,
                photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                caption=("📷 Scan this QR to pay ₹29\n\n"
                         "❓ If you have any doubts, feel free to contact the admin 👉 @iam_akilesh07")
            )

            keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')]]
            context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Click the button below after making the payment",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif user_state.get(user_id) == "ready_to_receive_payment":
        user_state[user_id] = "awaiting_verification"

        admin_message = f"🆕 Payment Receipt from {user.first_name}\n"
        admin_message += f"👤 ID: {user.id}\n"
        admin_message += f"📧 Username: @{user.username if user.username else 'N/A'}\n"
        admin_message += "⬇️ Payment Screenshot:"

        context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)

        context.bot.send_message(
            chat_id=user_id,
            text=("✅ Payment receipt received!\n\n"
                  "📩 Your payment is under verification. You'll receive the course link shortly after manual verification.\n\n"
                  "⏳ Please wait up to 24 hours.")
        )

# ✅ Admin command

def send_course_link(update: Update, context: CallbackContext):
    if update.message.from_user.id == ADMIN_ID:
        try:
            user_id = int(context.args[0])
            link = context.args[1]
            password = context.args[2]

            context.bot.send_message(
                chat_id=user_id,
                text=(f"🎉 Your payment has been verified!\n\n"
                      f"🎓 Course Access:\n🔗 {link}\n🔑 Password: {password}\n\nEnjoy learning! 😊")
            )
            update.message.reply_text("✅ Course link sent successfully!")
        except (IndexError, ValueError):
            update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")
    else:
        update.message.reply_text("❌ Unauthorized")

# ✅ Fallbacks

def submit_command(update: Update, context: CallbackContext):
    update.message.reply_text("📤 Please click '📤 Submit Screenshots' button above.")

def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Unknown command. Use /start or buttons.")

# ✅ Main Runner

def run_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("submit", submit_command))
    dp.add_handler(CommandHandler("send_link", send_course_link))

    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.photo, handle_photos))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    PORT = int(os.environ.get('PORT', '8443'))
    APP_NAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

    if APP_NAME:
        webhook_url = f"https://{APP_NAME}/{BOT_TOKEN}"
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN, webhook_url=webhook_url)
        updater.bot.set_webhook(webhook_url)
    else:
        updater.start_polling()

    updater.idle()

# ✅ Entry

if __name__ == '__main__':
    run_bot()
