import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# Load config from env vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
UPI_ID = os.environ.get("UPI_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Example: https://ashboltbot.onrender.com
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN") # Add a secret token for security

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# App and state
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()

user_state = {}
user_screenshot_counter = {}

# ---------- Common Functions ----------
def notify_admin(user, message, photo=None):
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name} {user.last_name or ''}\n"
    admin_message += f"📧 Username: @{user.username or 'N/A'}"

    async def send():
        if photo:
            await bot_app.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=admin_message)
        else:
            await bot_app.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    bot_app.create_task(send())

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("🔥 Buy Course At Just ₹29", callback_data='buy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nClick 'Buy Course' to start your journey!",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = query.message.chat_id

    if query.data == 'buy':
        notify_admin(user, "Clicked 'Buy Course' button")
        await query.message.reply_text(
            "🔥 Namaste React Course — Just ₹29!\n"
            f"💸 Pay ₹29 to:\n\n💰 *{UPI_ID}*", parse_mode='Markdown'
        )
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                                     caption="📷 Scan this QR to pay ₹29")
        keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')]]
        await context.bot.send_message(chat_id=user_id,
            text="⬇️ Click below *after* payment, or send the screenshot now.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        user_state[user_id] = "ready_to_receive_payment"

    elif query.data == 'send_receipt':
        await context.bot.send_message(chat_id=user_id,
            text="📥 Please send your payment screenshot now.")
        user_state[user_id] = "ready_to_receive_payment"

    elif query.data == 'submit_sharing_screenshots':
        await context.bot.send_message(chat_id=user_id,
            text="📤 Upload your 3 sharing screenshots now.")
        user_state[user_id] = "collecting_screenshots"
        user_screenshot_counter[user_id] = 0

async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id

    if user_state.get(user_id) == "ready_to_receive_payment":
        # Notify admin about the payment screenshot
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Payment from {user.full_name or user.username}")

        # Confirm receipt and state "under verification" to the user
        await context.bot.send_message(chat_id=user_id,
                                       text="✅ Payment proof received. Your payment is now *under verification*.",
                                       parse_mode='Markdown')

        # Now, proceed with the course details and sharing instructions.
        await context.bot.send_message(chat_id=user_id,
            text="Awesome! As part of the ₹29 course offer, please share the promo message with message in 3 Telegram or WhatsApp groups and take screenshots of your shares.")

        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/63d8vMq3/Whats-App-Image-2025-06-16-at-20-24-36-af8e4ee8.jpg",
                                     caption=(
        "🚀 *Top Namaste Dev Courses for Just ₹29!*\n"
        "🔥 Namaste React • Frontend System Design • Node.js\n"
        "🎓 By Akshay Saini (Ex-Uber) – Real Projects + Career Prep\n\n"
        "💥 *Only ₹29 Each* or *₹69 for All 3!*\n"
        "📚 One-Time Access • Lifetime Learning\n\n"
        "🔗 *Join 👉 https://t.me/ashbolt_bot*\n"
        "🤖 Or *Search:* *ashbolt_bot* on Telegram"
    ), parse_mode='Markdown') # Added parse_mode='Markdown' here for consistency

        keyboard = [[InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit_sharing_screenshots')]]
        await context.bot.send_message(chat_id=user_id,
            text="👇 Submit your 3 sharing screenshots",
            reply_markup=InlineKeyboardMarkup(keyboard))

        # Update user state to await the sharing button click
        user_state[user_id] = "awaiting_sharing_button_click"


    elif user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] = user_screenshot_counter.get(user_id, 0) + 1
        await context.bot.send_message(chat_id=user_id,
            text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
            caption=f"📸 Sharing Screenshot {user_screenshot_counter[user_id]} from {user.full_name}")
        if user_screenshot_counter[user_id] == 3:
            user_state[user_id] = "awaiting_admin_verification"
            await context.bot.send_message(chat_id=user_id,
                text="✅ All 3 screenshots received. We'll verify and send access soon!")

    else:
        await context.bot.send_message(chat_id=user_id,
            text="🤔 Unexpected photo. Please use /start to follow the proper flow.")

async def send_course_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        try:
            user_id = int(context.args[0])
            link = context.args[1]
            password = context.args[2]
            await context.bot.send_message(chat_id=user_id,
                text=f"🎓 Course Link: {link}\n🔐 Password: {password}")
            await update.message.reply_text("✅ Sent!")
            user_state.pop(user_id, None)
            user_screenshot_counter.pop(user_id, None)
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")
        except Exception as e:
            logging.error(f"Error sending course link: {e}")
            await update.message.reply_text(f"An error occurred: {e}")
    else:
        await update.message.reply_text("❌ Unauthorized")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")

# ---------- Add handlers ----------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("send_link", send_course_link))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
bot_app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

# ---------- Webhook endpoint ----------
@fastapi_app.post(f"/{WEBHOOK_SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid secret token")

    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    # Process the update using the initialized application
    await bot_app.process_update(update)
    return {"ok": True}

# ---------- Set webhook and initialize application on startup ----------
@fastapi_app.on_event("startup")
async def on_startup():
    logging.info("Initializing Telegram bot application...")
    # Initialize the application
    await bot_app.initialize()

    # Start the application - this sets up the internal task queue etc.
    await bot_app.start()
    logging.info("Telegram bot application initialized and started.")

    # Set the webhook URL
    webhook_url_full = f"{WEBHOOK_URL}/{WEBHOOK_SECRET_TOKEN}"
    logging.info(f"Setting webhook to {webhook_url_full}")
    await bot_app.bot.set_webhook(
        url=webhook_url_full,
        secret_token=WEBHOOK_SECRET_TOKEN
    )
    logging.info("Webhook set successfully.")

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    logging.info("Stopping Telegram bot application...")
    # Stop the application gracefully on shutdown
    await bot_app.stop()
    await bot_app.shutdown()
    logging.info("Telegram bot application stopped.")

# To run this with uvicorn, you would use:
# uvicorn your_file_name:fastapi_app --host 0.0.0.0 --port 10000
