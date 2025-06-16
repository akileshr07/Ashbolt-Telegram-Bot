import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.ext.webhook import WebhookHandler

# Load config from env vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
UPI_ID = os.environ.get("UPI_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Example: https://ashboltbot.onrender.com/webhook

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# App and state
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()
webhook_handler = WebhookHandler(bot_app)

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
        user_state[user_id] = "payment_received"
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Payment from {user.full_name or user.username}")
        await context.bot.send_message(chat_id=user_id,
            text="✅ Payment received. Please wait...\nNow, share the promo message in 3 groups and send screenshots.")
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/nVYkp19r/6213087660646450101-120.jpg",
                                     caption="📲 Share this image + join link in 3 groups.")
        keyboard = [[InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit_sharing_screenshots')]]
        await context.bot.send_message(chat_id=user_id,
            text="👇 Submit your 3 sharing screenshots",
            reply_markup=InlineKeyboardMarkup(keyboard))
        user_state[user_id] = "awaiting_sharing_button_click"

    elif user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] += 1
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
        except Exception:
            await update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")
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
@fastapi_app.post("/webhook")
async def telegram_webhook(request: Request):
    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await webhook_handler.handle_update(update)
    return {"ok": True}

# ---------- Set webhook on startup ----------
@fastapi_app.on_event("startup")
async def on_startup():
    await bot_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
