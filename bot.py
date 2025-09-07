import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# ----------------- Config -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)
UPI_ID = os.environ.get("UPI_ID") or "your-upi@bank"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN")

# ----------------- Logging -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- App & Bot -----------------
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()

# In-memory state
user_state = {}  # chat_id -> state string
user_screenshot_counter = {}  # chat_id -> int

# ----------------- Helper -----------------
def notify_admin_sync(user, message, photo=None, phone_number=None):
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name} {user.last_name or ''}\n"
    admin_message += f"📧 Username: @{user.username or 'N/A'}\n"
    if phone_number:
        admin_message += f"📱 Phone: {phone_number}\n"

    async def send():
        try:
            if photo:
                await bot_app.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=admin_message)
            else:
                await bot_app.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        except Exception as e:
            logger.exception("Failed to notify admin: %s", e)

    try:
        bot_app.create_task(send())
    except Exception:
        asyncio.create_task(send())

# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    keyboard = [
        [InlineKeyboardButton("1. Namaste React ₹29", callback_data="buy_react")],
        [InlineKeyboardButton("2. Namaste Frontend System Design ₹29", callback_data="buy_frontend_sd")],
        [InlineKeyboardButton("3. Namaste Node.js ₹29", callback_data="buy_nodejs")],
        [InlineKeyboardButton("4. All three bundle ₹69", callback_data="buy_bundle")]
    ]
    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nPlease choose a course option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------------- Button Handler -----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = query.message.chat_id

    # ---------- Course Selection ----------
    if query.data in ("buy_react", "buy_frontend_sd", "buy_nodejs", "buy_bundle"):
        amount_to_pay = "₹29"
        selected_option_message = ""
        if query.data == "buy_react":
            selected_option_message = "chose 'Namaste React' (₹29)"
        elif query.data == "buy_frontend_sd":
            selected_option_message = "chose 'Namaste Frontend System Design' (₹29)"
        elif query.data == "buy_nodejs":
            selected_option_message = "chose 'Namaste Node.js' (₹29)"
        elif query.data == "buy_bundle":
            selected_option_message = "chose 'All three bundle' (₹69)"
            amount_to_pay = "₹69"

        notify_admin_sync(user, f"User {selected_option_message}")
        context.user_data['selected_course_info'] = {'message': selected_option_message, 'amount': amount_to_pay}

        # Payment instructions
        await query.message.reply_text(
            f"🔥 You selected: {selected_option_message.split('chose ')[1].capitalize()}\n\n"
            f"💸 Pay {amount_to_pay} to:\n\n💰 *{UPI_ID}*",
            parse_mode="Markdown"
        )
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                                     caption=f"📷 Scan this QR to pay {amount_to_pay}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⬇️ Click below *after* payment, or send the screenshot now.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt")]]),
            parse_mode="Markdown"
        )
        user_state[user_id] = "ready_to_receive_payment"
        return

    # ---------- Send Payment Receipt ----------
    if query.data in ("send_receipt", "send_receipt_skip"):
        if query.data == "send_receipt":
            user_state[user_id] = "ready_to_receive_payment"
            await context.bot.send_message(chat_id=user_id, text="📥 Please send your payment screenshot now.")
        else:
            user_state[user_id] = "ready_to_receive_payment_skip"
            await context.bot.send_message(chat_id=user_id, text="📥 Please send your ₹50 skip payment screenshot now.")
        return

    # ---------- Submit sharing screenshots ----------
    if query.data == "submit_sharing_screenshots":
        await context.bot.send_message(chat_id=user_id, text="📤 Upload your 3 sharing screenshots now.")
        user_state[user_id] = "collecting_screenshots"
        user_screenshot_counter[user_id] = 0
        return

    # ---------- Consent to share phone ----------
    if query.data == "consent_share_phone":
        notify_admin_sync(user, "User consented to share phone number")
        await query.message.reply_text(
            "Please press the button below to share your phone number with us:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Share My Phone Number", request_contact=True)]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        user_state[user_id] = "awaiting_phone_number"
        await query.edit_message_reply_markup(reply_markup=None)
        return

    # ---------- Don't want to share ----------
    if query.data == "dont_want_to_share":
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💡 Don’t want to share? Pay ₹50 extra to skip sharing and proceed.\n💸 Pay to: *{UPI_ID}*",
            parse_mode="Markdown"
        )
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                                     caption="📷 Scan to pay ₹50 (skip sharing)")
        await context.bot.send_message(
            chat_id=user_id,
            text="After payment, click below and send the screenshot.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt_skip")]])
        )
        user_state[user_id] = "ready_to_receive_payment_skip"
        return

    await context.bot.send_message(chat_id=user_id, text="❌ Unknown action. Use /start to restart.")

# ----------------- Handle Contact -----------------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    contact = update.message.contact

    if user_state.get(user_id) == "awaiting_phone_number" and contact:
        phone_number = contact.phone_number
        notify_admin_sync(user, "User shared phone number", phone_number=phone_number)
        await update.message.reply_text(
            "✅ Thank you! Your phone number is received. Course access will be granted shortly.",
            reply_markup=ReplyKeyboardRemove()
        )
        user_state[user_id] = "awaiting_admin_verification"
        context.user_data.pop('selected_course_info', None)
    else:
        await update.message.reply_text("🤔 Unexpected contact. Use /start to follow the flow.")

# ----------------- Handle Photos -----------------
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id
    state = user_state.get(user_id)

    # --- Standard Payment ---
    if state == "ready_to_receive_payment":
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Payment from {user.full_name or user.username}")
        await context.bot.send_message(chat_id=user_id, text="✅ Payment received. Please follow the steps below to unlock the course. This is the last part of the course purchase. You can skip the sharing requirement by paying extra; there is an option for this below. After that, you need to share your contact details to receive course access.")

        # Show sharing instructions
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 To unlock the course, share the promo in 3 Telegram groups and send screenshots.\n"
                "⚠️ Don't share in personal/unrelated groups."
            )
        )
        await context.bot.send_photo(
            chat_id=user_id,
            photo="https://i.postimg.cc/NfGX2Dfd/Web-Photo-Editor.jpg",
            caption = (
    "🚀 Akshay Saini's Dev Courses for just ₹29\n\n"
    "📚 Includes:\n"
    "   - React\n"
    "   - Frontend System Design\n"
    "   - Node.js\n\n"
    "⚡ Access once, learn forever (with real projects)\n\n"
    "👉 To get it: Search **ashbolt_bot** on Telegram"
)

        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Submit Screenshots", callback_data="submit_sharing_screenshots")],
            [InlineKeyboardButton("🙅‍♂️ Don't Want to Share", callback_data="dont_want_to_share")]
        ])
        await context.bot.send_message(chat_id=user_id, text="Choose one:", reply_markup=keyboard)
        user_state[user_id] = "awaiting_sharing_button_click"
        return

    # --- Skip ₹50 Payment ---
    if state == "ready_to_receive_payment_skip":
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Skip-sharing Payment ₹50 from {user.full_name or user.username}")
        # Ask for phone consent
        consent_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Share My Phone Number", callback_data="consent_share_phone")]
        ])
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Payment received! To finalize your course access, please share your phone numberPayment done but no access? Ping @iam_akilesh07. Support in 24h.",
            reply_markup=consent_keyboard
        )
        user_state[user_id] = "awaiting_phone_consent"
        context.user_data.pop('selected_course_info', None)
        user_screenshot_counter.pop(user_id, None)
        return

    # --- Collecting Sharing Screenshots ---
    if state == "collecting_screenshots":
        count = user_screenshot_counter.get(user_id, 0) + 1
        user_screenshot_counter[user_id] = count
        await context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {count} received!")
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"📸 Screenshot {count} from {user.full_name or user.username}")

        if count >= 3:
            consent_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Share My Phone Number", callback_data="consent_share_phone")]
            ])
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ All 3 screenshots received! Please share your phone number to finalize course access.Payment done but no access? Ping @iam_akilesh07. Support in 24h.",
                reply_markup=consent_keyboard
            )
            user_state[user_id] = "awaiting_phone_consent"
        return

    await context.bot.send_message(chat_id=user_id,
                                   text="🤔 Unexpected photo. Use /start to follow the proper flow.")

# ----------------- Admin Send Course -----------------
async def send_course_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return

    try:
        user_id = int(context.args[0])
        link = context.args[1]
        password = context.args[2]
        await context.bot.send_message(chat_id=user_id, text=f"🎓 Course Link: {link}\n🔐 Password: {password}")
        await update.message.reply_text("✅ Sent!")
        user_state.pop(user_id, None)
        user_screenshot_counter.pop(user_id, None)
    except Exception:
        await update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")

# ----------------- Unknown Command -----------------
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")

# ----------------- Handlers -----------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("send_link", send_course_link))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
bot_app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))

# ----------------- Webhook -----------------
@fastapi_app.post(f"/{WEBHOOK_SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

# ----------------- Startup / Shutdown -----------------
@fastapi_app.on_event("startup")
async def on_startup():
    logger.info("Initializing Telegram bot...")
    await bot_app.initialize()
    await bot_app.start()
    if WEBHOOK_URL and WEBHOOK_SECRET_TOKEN:
        webhook_url_full = f"{WEBHOOK_URL}/{WEBHOOK_SECRET_TOKEN}"
        await bot_app.bot.set_webhook(url=webhook_url_full, secret_token=WEBHOOK_SECRET_TOKEN)

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()
