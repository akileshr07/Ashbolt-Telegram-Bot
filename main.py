import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, CallbackQueryHandler
)

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 1774865778
UPI_ID = '6382344469@jio'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# User state management
user_state = {}
user_screenshot_counter = {}
payment_proofs = {}  # Maps user_id to message_id

# Start command
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')]]
    update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Button actions
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
                "💻 *Namaste React Course by Akshay Saini – Just $0.35 / ₹29!*\n\n"
                "🎯 50+ Hours of Project-Based Learning\n"
                "🚀 Includes 3 Major Projects + Interview Prep\n"
                "✅ Covers Latest React JS Concepts (Hooks, Redux, Routing, etc.)\n"
                "👨‍💻 Perfect for Beginners & Experienced Developers\n\n"
                "🔗 Join Now 👉 https://t.me/ashbolt_bot\n"
                "📲 Or Search \"ashbolt_bot\" on Telegram\n\n"
                "🌟 One-Time Access • Learn at Your Own Pace"
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

# Handle photos
def handle_photos(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")

        if user_screenshot_counter[user_id] == 3:
            user_state[user_id] = "waiting_payment"
            context.bot.send_message(
                chat_id=user_id,
                text=f"✅ All 3 screenshots received!\n\n💸 Pay ₹29 to: *{UPI_ID}*",
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

        # Forward to admin
        context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)

        # Admin Approval UI
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")]
        ])
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 Payment received from user ID: {user_id}\nReview and take action.",
            reply_markup=keyboard
        )
        context.bot.send_message(
            chat_id=user_id,
            text="📤 Payment screenshot sent to admin for review.\nPlease wait for approval."
        )

# Document fallback (image only)
def handle_documents(update: Update, context: CallbackContext):
    file = update.message.document
    if file.mime_type in ['image/jpeg', 'image/png']:
        update.message.photo = [file]
        handle_photos(update, context)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="❌ Unsupported file format. Only JPG/PNG allowed.")

# Fallback commands
def submit_command(update: Update, context: CallbackContext):
    update.message.reply_text("📤 Tap the Submit Screenshots button to begin.")

def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Unknown command. Please use /start or menu buttons.")

# Start bot
def run_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("submit", submit_command))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.photo, handle_photos))
    dp.add_handler(MessageHandler(Filters.document, handle_documents))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    print("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

run_bot()
