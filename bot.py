# ✅ STEP 1: Install required library
# !pip install python-telegram-bot==13.15
# You also need a web server library like Flask or FastAPI for webhooks.
# For simplicity with python-telegram-bot's webhook, Flask is often used internally.
# Or, if you need a full web server for other tasks, you'd integrate it.
# For just webhook, python-telegram-bot can handle the internal server.

# ✅ STEP 2: Imports & Config
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

# --- IMPORTANT: Modify notify_admin for webhook context ---
# When using webhooks, the 'context' might not always be available globally
# if notify_admin is called outside of an active handler.
# A safer approach is to pass the bot instance or context when calling it.
# For now, I'll adjust it slightly, but keep in mind that for cron-like jobs,
# you might need to instantiate a new Bot object.
def notify_admin(bot_instance: Bot, user, message):
    """Helper function to notify admin about user actions"""
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name}"
    admin_message += f" {user.last_name}" if user.last_name else ""
    admin_message += f"\n📧 Username: @{user.username}" if user.username else "\n📧 Username: N/A"

    try:
        bot_instance.send_message(chat_id=ADMIN_ID, text=admin_message)
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")


# ✅ /start command
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    keyboard = [[
        InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=reply_markup
    )
    # Notify admin about new user using the bot instance from context
    notify_admin(context.bot, user, "Started the bot")


# ✅ Promo Flow (Buy)
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = query.from_user

    if query.data == 'buy':
        # Notify admin that user clicked buy
        notify_admin(context.bot, user, "Clicked 'Buy Course' button")

        query.message.reply_text(
            "🔥 Namaste React Course — Just ₹29!\n"
            "🚀 Limited Time Offer – Act Fast!\n\n"
            "🎯 Learn React from Scratch with Lifetime Access, Projects, Notes & More!\n\n"
            "📌 How to Unlock the Discount:\n"
            "1️⃣ Share the promo message (below) to 3 Telegram groups or WhatsApp groups\n"
            "2️⃣ Take screenshots\n"
            "3️⃣ Send them here via 📤 Submit Screenshots button\n\n"
            "📲 Join the Channel: https://t.me/+IEY3uiiKHfU4NzQ1"
        )

        image_url = "https://i.postimg.cc/nVYkp19r/6213087660646450101-120.jpg"
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_url,
            caption=("💻 Namaste React Course by Akshay Saini – Just $0.35 / ₹29\n"
                     "🎯 50+ Hours of Project-Based Learning\n\n"
                     "🚀 Includes 3 Major Projects + Interview Prep\n\n"
                     "👨‍💻 Perfect for Beginners & Experienced Developer\n\n"
                     "🎯 Lifetime Access | Projects | Notes\n\n"
                     "🔗 Join Now 👉 https://t.me/ashbolt_bot\n"
                     "📲 Or Search 'ashbolt_bot' on Telegram\n"
                     "🚀 Limited Time Offer")
        )

        keyboard = [[
            InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit')
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Now you can submit your 3 screenshots below 👇",
            reply_markup=reply_markup
        )

    elif query.data == 'submit':
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📤 Please upload your 3 screenshot proofs here one by one."
        )
        user_state[query.message.chat_id] = "collecting_screenshots"
        user_screenshot_counter[query.message.chat_id] = 0

    elif query.data == 'send_receipt':
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📥 Please send your payment screenshot now."
        )
        user_state[query.message.chat_id] = "ready_to_receive_payment"

# ✅ Handle Photos (Screenshots + Payment Proof)
def handle_photos(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user = update.message.from_user

    # Screenshot Phase
    if user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        context.bot.send_message(chat_id=user_id,
                                 text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")

        if user_screenshot_counter[user_id] == 3:
            user_state[user_id] = "awaiting_payment_button"

            # Notify admin that user submitted all screenshots
            notify_admin(context.bot, user, "Submitted all 3 screenshots")

            # Show UPI + QR
            context.bot.send_message(
                chat_id=user_id,
                text=(f"✅ All 3 screenshots received!\n\n"
                      f"💸 Now pay ₹29 to:\n\n💰 *{UPI_ID}*"),
                parse_mode='Markdown'
            )

            context.bot.send_photo(
                chat_id=user_id,
                photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                caption="📷 Scan this QR to pay ₹29"
            )

            keyboard = [[
                InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Click the button below *after* making the payment",
                reply_markup=reply_markup
            )

    # Payment Receipt Phase
    elif user_state.get(user_id) == "ready_to_receive_payment":
        user_state[user_id] = "awaiting_verification"

        # Forward payment screenshot to admin with user info
        admin_message = f"🆕 Payment Receipt from User:\n"
        admin_message += f"👤 Name: {user.first_name} {user.last_name if user.last_name else ''}\n"
        admin_message += f"🆔 ID: {user.id}\n"
        admin_message += f"📧 Username: @{user.username if user.username else 'N/A'}\n\n"
        admin_message += "⬇️ Payment Screenshot:"

        context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )

        # Send confirmation to user
        context.bot.send_message(
            chat_id=user_id,
            text=("✅ Payment receipt received!\n\n"
                  "📩 Your payment is under verification. "
                  "You'll receive the course access link shortly after manual verification.\n\n"
                  "⏳ Please wait for confirmation (usually within 24 hours).")
        )

# ✅ Admin command to send course link
def send_course_link(update: Update, context: CallbackContext):
    # Check if the command is from admin
    if update.message.from_user.id == ADMIN_ID:
        try:
            # Command format: /send_link <user_id> <link> <password>
            user_id = int(context.args[0])
            link = context.args[1]
            password = context.args[2]

            # Send the course link to the user
            context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 Your payment has been verified!\n\n"
                     f"🎓 Here is your course access:\n"
                     f"🔗 {link}\n"
                     f"🔑 Password: {password}\n\n"
                     f"Enjoy learning! 😊"
            )

            # Confirm to admin
            update.message.reply_text(f"✅ Course link sent successfully to user {user_id}")

        except (IndexError, ValueError):
            update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")
    else:
        update.message.reply_text("❌ Unauthorized access.")

# ✅ /submit fallback
def submit_command(update: Update, context: CallbackContext):
    update.message.reply_text("📤 Please click 📤 Submit Screenshots option at top")

# ✅ Handle unknown commands
def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Unknown command. Use /start or tap buttons.")

# ✅ Main bot runner - MODIFIED FOR WEBHOOKS
def run_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("submit", submit_command))
    dp.add_handler(CommandHandler("send_link", send_course_link))

    # Buttons & Messages
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.photo, handle_photos))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    # --- Webhook configuration for Render's free Web Service ---
    # Get port from environment, defaults to 8443 for local testing/fallback
    PORT = int(os.environ.get('PORT', '8443'))

    # Render sets RENDER_EXTERNAL_HOSTNAME for your public URL
    # Example: your-service-name.onrender.com
    APP_NAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

    if APP_NAME:
        # If running on Render, set up webhook
        webhook_url = f"https://{APP_NAME}/{BOT_TOKEN}"
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=BOT_TOKEN,
                              webhook_url=webhook_url)
        logging.info(f"🤖 Bot running with webhook on {webhook_url}")
        # IMPORTANT: Set webhook with Telegram if you haven't already.
        # This line ensures Telegram knows where to send updates.
        # Only set it if it's not already set correctly to avoid unnecessary calls.
        # You might want to do this once on deployment or if the webhook URL changes.
        # For simplicity, we'll put it here, but a more robust app might manage this.
        updater.bot.set_webhook(webhook_url)
        logging.info("Telegram webhook set successfully.")
    else:
        # Fallback to polling for local development or if APP_NAME isn't set
        updater.start_polling()
        logging.info("🤖 Bot running with long polling (local development)")

    updater.idle() # This keeps the webhook server running

# ✅ Run
if __name__ == '__main__':
    run_bot()
