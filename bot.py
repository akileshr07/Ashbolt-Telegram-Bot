# ✅ STEP 1: Install required library
# !pip install python-telegram-bot==13.15

# ✅ STEP 2: Imports & Config
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
# This dictionary keeps track of where each user is in the bot's flow.
# Example: user_state[user_id] = "awaiting_contact"
user_state = {}
user_screenshot_counter = {} # Tracks how many screenshots a user has sent

# --- Helper function to notify admin ---
def notify_admin(bot_instance: Bot, user, message, phone_number=None):
    """
    Sends a notification to the admin with user details and a custom message.
    Includes phone number if provided.
    """
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name}"
    admin_message += f" {user.last_name}" if user.last_name else ""
    admin_message += f"\n📧 Username: @{user.username}" if user.username else "\n📧 Username: N/A"
    if phone_number:
        admin_message += f"\n📞 Phone Number: {phone_number}"

    try:
        bot_instance.send_message(chat_id=ADMIN_ID, text=admin_message)
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")


# ✅ /start command handler
def start(update: Update, context: CallbackContext):
    """
    Handles the /start command. Prompts the user to share their phone number
    before proceeding with the course purchase flow.
    """
    user = update.message.from_user
    # Request contact using a ReplyKeyboardMarkup
    keyboard = [[
        KeyboardButton("Share My Phone Number 📞", request_contact=True)
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\n"
        "To proceed, please share your phone number by clicking the button below.",
        reply_markup=reply_markup
    )
    # Set user state to anticipate contact sharing
    user_state[user.id] = "awaiting_contact"

# ✅ Handle shared contact
def handle_contact(update: Update, context: CallbackContext):
    """
    Processes the shared contact information from the user.
    Notifies the admin and then continues with the course purchase flow.
    """
    user = update.message.from_user
    chat_id = update.message.chat_id

    # Check if the message is a contact and if the user was in the expected state
    if user_state.get(user.id) == "awaiting_contact" and update.message.contact:
        phone_number = update.message.contact.phone_number
        # Notify admin with the user's details and phone number
        notify_admin(context.bot, user, "Shared phone number", phone_number)
        del user_state[user.id] # Clear state after receiving contact

        # Remove the contact sharing keyboard from the user's view
        update.message.reply_text(
            "Thank you for sharing your phone number!",
            reply_markup=ReplyKeyboardRemove()
        )

        # Now, present the "Buy Course" button as the next step
        keyboard = [[
            InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=chat_id,
            text=f"Great! Now click 'Buy Course' to start your journey!",
            reply_markup=reply_markup
        )
    else:
        # If a contact is sent when not expected, or it's not a contact message
        update.message.reply_text("Please use the /start command if you wish to share your contact or buy the course.")

# ✅ Promo Flow (Buy) - Inline button handler
def button_handler(update: Update, context: CallbackContext):
    """
    Handles all inline button presses, managing the course promo flow.
    """
    query = update.callback_query
    query.answer() # Acknowledge the callback query immediately
    user = query.from_user

    if query.data == 'buy':
        # Notify admin that user initiated the purchase flow
        notify_admin(context.bot, user, "Clicked 'Buy Course' button")

        # Send introductory text about the course and steps
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

        # Send the promotional image with a caption
        image_url = "https://i.postimg.cc/nVYkp19r/6213087660646450101-120.jpg"
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_url,
            caption=(
                "💻 Namaste React Course by Akshay Saini – Just $0.35 / ₹29\n"
                "🎯 50+ Hours of Project-Based Learning\n\n"
                "🚀 Includes 3 Major Projects + Interview Prep\n\n"
                "👨‍💻 Perfect for Beginners & Experienced Developer\n\n"
                "🎯 Lifetime Access | Projects | Notes\n\n"
                "🔗 Join Now 👉 https://t.me/ashbolt_bot\n"
                "📲 Or Search 'ashbolt_bot' on Telegram\n"
                "🚀 Limited Time Offer"
            )
        )

        # Offer the "Submit Screenshots" button
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
        # Prompt user to upload screenshots
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📤 Please upload your 3 screenshot proofs here one by one."
        )
        # Set user state to anticipate screenshots
        user_state[query.message.chat_id] = "collecting_screenshots"
        user_screenshot_counter[query.message.chat_id] = 0 # Reset screenshot counter for this user

    elif query.data == 'send_receipt':
        # Prompt user to send payment receipt
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📥 Please send your payment screenshot now."
        )
        # Set user state to anticipate payment receipt
        user_state[query.message.chat_id] = "ready_to_receive_payment"

# ✅ Handle Photos (Screenshots + Payment Proof)
def handle_photos(update: Update, context: CallbackContext):
    """
    Handles incoming photo messages, distinguishing between promo screenshots
    and payment receipts based on user state.
    """
    user_id = update.message.chat_id
    user = update.message.from_user

    # --- Screenshot Collection Phase ---
    if user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        context.bot.send_message(chat_id=user_id,
                                 text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")

        if user_screenshot_counter[user_id] == 3:
            # All 3 screenshots received, transition to payment phase
            user_state[user_id] = "awaiting_payment_button"

            # Notify admin about screenshot submission
            notify_admin(context.bot, user, "Submitted all 3 screenshots")

            # Provide UPI ID and QR code for payment
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

            # Offer the "Send Payment Receipt" button
            keyboard = [[
                InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Click the button below *after* making the payment",
                reply_markup=reply_markup
            )

    # --- Payment Receipt Phase ---
    elif user_state.get(user_id) == "ready_to_receive_payment":
        user_state[user_id] = "awaiting_verification" # User has sent payment, now waiting for admin to verify

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

        # Send confirmation message to the user
        context.bot.send_message(
            chat_id=user_id,
            text=("✅ Payment receipt received!\n\n"
                  "📩 Your payment is under verification. "
                  "You'll receive the course access link shortly after manual verification.\n\n"
                  "⏳ Please wait for confirmation (usually within 24 hours).")
        )

# ✅ Admin command to send course link
def send_course_link(update: Update, context: CallbackContext):
    """
    Allows the admin to send the course access link and password to a user.
    Usage: /send_link <user_id> <link> <password>
    """
    # Check if the command is issued by the admin
    if update.message.from_user.id == ADMIN_ID:
        try:
            # Parse command arguments
            user_id = int(context.args[0])
            link = context.args[1]
            password = context.args[2]

            # Send the course link to the specified user
            context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 Your payment has been verified!\n\n"
                     f"🎓 Here is your course access:\n"
                     f"🔗 {link}\n"
                     f"🔑 Password: {password}\n\n"
                     f"Enjoy learning! 😊"
            )

            # Confirm to the admin that the link was sent
            update.message.reply_text(f"✅ Course link sent successfully to user {user_id}")

        except (IndexError, ValueError):
            # Handle incorrect command usage
            update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")
    else:
        # Deny unauthorized access
        update.message.reply_text("❌ Unauthorized access.")

# ✅ /submit fallback
def submit_command(update: Update, context: CallbackContext):
    """
    A fallback handler for the /submit command, guiding users to the correct button.
    """
    update.message.reply_text("📤 Please click 📤 Submit Screenshots option at top")

# ✅ Handle unknown commands and general text messages
def unknown_message(update: Update, context: CallbackContext):
    """
    Responds to unknown commands or general text messages not handled by other handlers.
    """
    update.message.reply_text("❌ I didn't understand that. Use /start or tap the buttons.")

# ✅ Main bot runner - Configured for Webhooks (e.g., for Render deployment)
def run_bot():
    """
    Initializes and runs the Telegram bot using either webhooks or long polling.
    """
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("submit", submit_command))
    dp.add_handler(CommandHandler("send_link", send_course_link))

    # Handle inline button presses
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Handle different types of messages
    dp.add_handler(MessageHandler(Filters.photo, handle_photos)) # For screenshots and payment proof
    dp.add_handler(MessageHandler(Filters.contact, handle_contact)) # For shared phone numbers
    dp.add_handler(MessageHandler(Filters.command, unknown_message)) # For unhandled commands
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, unknown_message)) # For unhandled text messages

    # --- Webhook configuration for Render's free Web Service ---
    PORT = int(os.environ.get('PORT', '8443')) # Get port from environment or default
    APP_NAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME') # Render's public hostname

    if APP_NAME:
        # If running on Render, set up webhook
        webhook_url = f"https://{APP_NAME}/{BOT_TOKEN}"
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=BOT_TOKEN,
                              webhook_url=webhook_url)
        logging.info(f"🤖 Bot running with webhook on {webhook_url}")
        # IMPORTANT: The set_webhook call below is commented out.
        # It should ideally be done once manually (e.g., via curl) or in a
        # separate deployment script to avoid rate limit issues on every restart.
        # updater.bot.set_webhook(webhook_url)
        # logging.info("Telegram webhook set successfully.")
    else:
        # Fallback to long polling for local development or if APP_NAME isn't set
        updater.start_polling()
        logging.info("🤖 Bot running with long polling (local development)")

    updater.idle() # Keeps the bot running until interrupted

# ✅ Run the bot
if __name__ == '__main__':
    run_bot()
