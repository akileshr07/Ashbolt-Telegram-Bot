# ✅ STEP 1: Install required library
# !pip install python-telegram-bot==13.15

# ✅ STEP 2: Imports & Config
import logging
import os # Import os module
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ✅ Bot Configuration - Get from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID')) # Convert to int
UPI_ID = os.environ.get('UPI_ID')

# Validate if environment variables are set
if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable not set.")
    exit(1)
if not ADMIN_ID:
    logging.error("ADMIN_ID environment variable not set.")
    exit(1)
if not UPI_ID:
    logging.error("UPI_ID environment variable not set.")
    exit(1)


# ✅ Logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

# ✅ User State
user_state = {}
user_screenshot_counter = {}

def notify_admin(user, message):
    """Helper function to notify admin about user actions"""
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name}"
    admin_message += f" {user.last_name}" if user.last_name else ""
    admin_message += f"\n📧 Username: @{user.username}" if user.username else "\n📧 Username: N/A"

    # Get the bot instance from any handler's context
    # This part is a bit tricky. In a deployed environment,
    # you might not have direct access to 'updater.bot' outside of the main loop.
    # A more robust way is to pass the bot instance or context around,
    # or re-instantiate if absolutely necessary (less efficient).
    # For simplicity, we'll keep the current approach, but be aware it's not ideal for
    # concurrent calls if not managed carefully.
    try:
        context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
    except AttributeError:
        # Fallback if context.bot is not available (e.g., if called outside a handler)
        # This will create a new bot instance, which is generally discouraged but works as a fallback
        from telegram import Bot
        temp_bot = Bot(token=BOT_TOKEN)
        temp_bot.send_message(chat_id=ADMIN_ID, text=admin_message)


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

# ✅ Promo Flow (Buy)
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = query.from_user

    if query.data == 'buy':
        # Notify admin that user clicked buy
        notify_admin(user, "Clicked 'Buy Course' button")

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
            notify_admin(user, "Submitted all 3 screenshots")

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

# ✅ Main bot runner
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

    updater.start_polling()
    print("🤖 Bot is running...")
    updater.idle()

# ✅ Run
if __name__ == '__main__':
    run_bot()
