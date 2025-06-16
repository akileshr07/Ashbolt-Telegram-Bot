 import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ✅ Bot Configuration - Get from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID')) # Convert to int
UPI_ID = os.environ.get('UPI_ID')

# ✅ Logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ✅ User State
user_state = {}
user_screenshot_counter = {}

# Global app instance
app = None

def notify_admin(user, message, photo=None):
    """Helper function to notify admin about user actions, optionally with a photo"""
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name}"
    admin_message += f" {user.last_name}" if user.last_name else ""
    admin_message += f"\n📧 Username: @{user.username}" if user.username else "\n📧 Username: N/A"

    import asyncio
    if app:
        if photo:
            asyncio.create_task(app.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=admin_message))
        else:
            asyncio.create_task(app.bot.send_message(chat_id=ADMIN_ID, text=admin_message))

# ✅ /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=reply_markup
    )

# ✅ Promo Flow (Buy)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = query.message.chat_id

    if query.data == 'buy':
        notify_admin(user, "Clicked 'Buy Course' button")

        await query.message.reply_text(
            "🔥 Namaste React Course — Just ₹29!\n"
            "🚀 Limited Time Offer – Act Fast!\n\n"
            f"💸 Please pay ₹29 to:\n\n💰 *{UPI_ID}*",
            parse_mode='Markdown'
        )

        await context.bot.send_photo(
            chat_id=user_id,
            photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
            caption="📷 Scan this QR to pay ₹29"
        )

        keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text="⬇️ Click the button below *after* making the payment, or simply send the screenshot now.",
            reply_markup=reply_markup
        )
        user_state[user_id] = "ready_to_receive_payment"

    elif query.data == 'send_receipt':
        await context.bot.send_message(
            chat_id=user_id,
            text="📥 Please send your payment screenshot now."
        )
        user_state[user_id] = "ready_to_receive_payment"

    elif query.data == 'submit_sharing_screenshots':
        await context.bot.send_message(
            chat_id=user_id,
            text="📤 Please upload your 3 screenshot proofs of sharing here one by one."
        )
        user_state[user_id] = "collecting_screenshots"
        user_screenshot_counter[user_id] = 0

# ✅ Handle Photos
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id

    if user_state.get(user_id) == "ready_to_receive_payment":
        user_state[user_id] = "payment_received"

        admin_message = f"🆕 Payment Receipt from User:\n"
        admin_message += f"👤 Name: {user.first_name} {user.last_name if user.last_name else ''}\n"
        admin_message += f"🆔 ID: {user.id}\n"
        admin_message += f"📧 Username: @{user.username if user.username else 'N/A'}\n\n"
        admin_message += "⬇️ Payment Screenshot:"

        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=admin_message)

        await context.bot.send_message(
            chat_id=user_id,
            text=("✅ Payment receipt received!\n\n"
                  "📩 Your payment is under initial processing. "
                  "Now, let's complete the final step for discount!\n\n"
                  "⏳ Please wait for instructions...")
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎯 To unlock the discount and get your course:\n"
                "1️⃣ Share the promo message (below) to 3 Telegram groups or WhatsApp groups\n"
                "2️⃣ Take screenshots of your shares\n"
                "3️⃣ Send them here via the 'Submit Screenshots' button\n\n"
                "📲 Join the Channel: https://t.me/+IEY3uiiKHfU4NzQ1"
            )
        )

        image_url = "https://i.postimg.cc/nVYkp19r/6213087660646450101-120.jpg"
        await context.bot.send_photo(
            chat_id=user_id,
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

        keyboard = [[InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit_sharing_screenshots')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text="👇 Now you can submit your 3 sharing screenshots below 👇",
            reply_markup=reply_markup
        )
        user_state[user_id] = "awaiting_sharing_button_click"

    elif user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Sharing Screenshot {user_screenshot_counter[user_id]} received!"
        )

        admin_message = f"📸 Sharing Screenshot {user_screenshot_counter[user_id]} from User:\n"
        admin_message += f"👤 Name: {user.first_name} {user.last_name if user.last_name else ''}\n"
        admin_message += f"🆔 ID: {user.id}\n"
        admin_message += f"📧 Username: @{user.username if user.username else 'N/A'}\n"

        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=admin_message)

        if user_screenshot_counter[user_id] == 3:
            notify_admin(user, "Submitted all 3 sharing screenshots")
            user_state[user_id] = "awaiting_admin_verification"

            await context.bot.send_message(
                chat_id=user_id,
                text=("✅ All 3 sharing screenshots received!\n\n"
                      "📩 Both your payment and sharing proofs are now under verification. "
                      "You'll receive the course access link shortly after manual verification.\n\n"
                      "⏳ Please wait for confirmation (usually within 24 hours).")
            )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="🤔 I'm not expecting a photo right now. Please follow the instructions or use /start."
        )

# ✅ Admin Command: /send_link
async def send_course_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        try:
            user_id = int(context.args[0])
            link = context.args[1]
            password = context.args[2]

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 Your payment and sharing proofs have been verified!\n\n"
                    f"🎓 Here is your course access:\n"
                    f"🔗 {link}\n"
                    f"🔑 Password: {password}\n\n"
                    f"Enjoy learning! 😊"
                )
            )

            await update.message.reply_text(f"✅ Course link sent successfully to user {user_id}")

            if user_id in user_state:
                del user_state[user_id]
            if user_id in user_screenshot_counter:
                del user_screenshot_counter[user_id]

        except (IndexError, ValueError):
            await update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")
    else:
        await update.message.reply_text("❌ Unauthorized access.")

# ✅ /submit fallback
async def submit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please use the buttons provided in the flow. Use /start to restart if stuck.")

# ✅ Unknown command
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start or tap buttons.")

# ✅ Main runner
def run_bot():
    global app
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submit", submit_command))
    app.add_handler(CommandHandler("send_link", send_course_link))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
