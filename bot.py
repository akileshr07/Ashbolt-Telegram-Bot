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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Example: https://ashboltbot.onrender.com
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN")  # secret token for webhook path

# ----------------- Logging -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- App & Bot -----------------
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()

# In-memory state (simple). For production, use persistent storage.
user_state = {}  # maps chat_id -> state string
user_screenshot_counter = {}  # maps chat_id -> int

# ----------------- Helpers -----------------
def notify_admin_sync(user, message, photo=None, phone_number=None):
    """
    Synchronous wrapper to schedule async sending to admin using bot_app.create_task.
    """
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

    # schedule without awaiting
    try:
        bot_app.create_task(send())
    except Exception:
        # fallback to asyncio if create_task not available yet
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nPlease choose a course option:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = query.message.chat_id

    # ---------- Buying options ----------
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

        # Send payment instructions
        await query.message.reply_text(
            f"🔥 You selected: {selected_option_message.split('chose ')[1].capitalize()}\n\n"
            f"💸 Pay {amount_to_pay} to:\n\n💰 *{UPI_ID}*",
            parse_mode="Markdown"
        )
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                                     caption=f"📷 Scan this QR to pay {amount_to_pay}")
        # Offer to send receipt after payment
        keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt")]]
        await context.bot.send_message(
            chat_id=user_id,
            text="⬇️ Click below *after* payment, or send the screenshot now.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        # Set state for normal payment verification
        user_state[user_id] = "ready_to_receive_payment"
        return

    # ---------- User opts to send receipt for standard flow ----------
    if query.data == "send_receipt":
        await context.bot.send_message(chat_id=user_id, text="📥 Please send your payment screenshot now.")
        user_state[user_id] = "ready_to_receive_payment"
        return

    # ---------- User selects to submit screenshots (sharing path) ----------
    if query.data == "submit_sharing_screenshots":
        await context.bot.send_message(chat_id=user_id, text="📤 Upload your 3 sharing screenshots now.")
        user_state[user_id] = "collecting_screenshots"
        user_screenshot_counter[user_id] = 0
        return

    # ---------- Consent share phone (same as before) ----------
    if query.data == "consent_share_phone":
        notify_admin_sync(user, "User clicked 'Yes, Share My Phone Number' button (consented to share).")
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

    # ---------- NEW: Don't want to share -> offer skip for ₹50 ----------
    if query.data == "dont_want_to_share":
        # Inform user about skip option and show QR + UPI ID and "Send Payment Receipt" button
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "💡 Don’t want to share? You can skip this step by paying ₹50 extra — this covers promotion costs directly.\n\n"
                f"💸 Pay ₹50 to: *{UPI_ID}* (or scan QR below)."
            ),
            parse_mode="Markdown"
        )
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                                     caption="📷 Scan to pay ₹50 (skip sharing)")
        keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt_skip")]]
        await context.bot.send_message(chat_id=user_id,
                                       text="After payment, click below and send the screenshot.",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        # Mark a new state to indicate they intend to skip sharing
        user_state[user_id] = "ready_to_receive_payment_skip"
        return

    # ---------- NEW: Handler for clicking skip-send-receipt ----------
    if query.data == "send_receipt_skip":
        await context.bot.send_message(chat_id=user_id, text="📥 Please send your payment screenshot for the ₹50 skip now.")
        user_state[user_id] = "ready_to_receive_payment_skip"
        return

    # Unknown callback fallback
    await context.bot.send_message(chat_id=user_id, text="❌ Unknown action. Use /start to restart.")

# ---------- Contact handler ----------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    contact = update.message.contact

    if user_state.get(user_id) == "awaiting_phone_number" and contact:
        phone_number = contact.phone_number
        notify_admin_sync(user, "User shared phone number", phone_number=phone_number)
        await update.message.reply_text(
            "✅ Thank you for sharing your phone number! We will now proceed with verifying your details and providing course access. You'll be notified soon!",
            reply_markup=ReplyKeyboardRemove()
        )
        user_state[user_id] = "awaiting_admin_verification"
        # Clear selected_course_info (clean up)
        context.user_data.pop('selected_course_info', None)
    else:
        await update.message.reply_text("🤔 Unexpected contact sharing. Please use /start to follow the proper flow.")

# ---------- Photo handler (payment screenshots and sharing screenshots) ----------
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id

    state = user_state.get(user_id)

    # --- Standard payment screenshot (user paid regular price and wants to share) ---
    if state == "ready_to_receive_payment":
        # Forward to admin
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Payment (normal) from {user.full_name or user.username}")
        # Confirm receipt
        await context.bot.send_message(chat_id=user_id,
                                       text="✅ Payment proof received. Your payment is now *under verification*.",
                                       parse_mode="Markdown")
        # Now show sharing instructions + both choices (Submit or Don't Want to Share)
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 *Awesome!* To unlock the course, please share the promo message with image in *3 Telegram groups* and send *screenshots* here.\n\n"
                "📢 *Share Only In:*\n"
                "• 🎓 College / Junior groups\n"
                "• 📚 Study / Placement groups\n"
                "• 👨‍💻 Coding groups like @knacademydeloitte, @onlinestudy4ubatch2024, Prime Coding, etc.\n\n"
                "❌ *Don't Share In:*\n"
                "• Personal / family / unrelated groups\n\n"
                "⚠️ *Warning:* Irrelevant sharing may lead to *access removal*. Support genuine learners only."
            ),
            parse_mode="Markdown"
        )

        await context.bot.send_photo(
            chat_id=user_id,
            photo="https://i.postimg.cc/NfGX2Dfd/Web-Photo-Editor.jpg",
            caption=(
                "🚀 *Akshay Saini's Dev Courses for just ₹29!*\n"
                "💡 Includes: React, Frontend System Design, Node.js\n"
                "📚 Access once, learn forever (with real projects)\n\n"
                "👉 To get it: *search* 🔍 *ashbolt_bot* on Telegram"
            ),
            parse_mode="Markdown"
        )

        # Provide two choices: Submit Screenshots OR Don't Want to Share
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Submit Screenshots", callback_data="submit_sharing_screenshots")],
            [InlineKeyboardButton("🙅‍♂️ Don't Want to Share", callback_data="dont_want_to_share")]
        ])
        await context.bot.send_message(chat_id=user_id,
                                       text="Choose one of the options below:",
                                       reply_markup=keyboard)
        # update state
        user_state[user_id] = "awaiting_sharing_button_click"
        return

    # --- Skip-payment screenshot (user paid ₹50 to skip sharing) ---
    if state == "ready_to_receive_payment_skip":
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Skip-sharing Payment (₹50) from {user.full_name or user.username}")
        await context.bot.send_message(chat_id=user_id,
                                       text="✅ Payment proof for the ₹50 skip received. Your payment is under verification. You will receive course access soon.",
                                       parse_mode="Markdown")
        # mark as awaiting admin verification and DO NOT present sharing instructions again
        user_state[user_id] = "awaiting_admin_verification"
        # clear counters/context if any
        user_screenshot_counter.pop(user_id, None)
        context.user_data.pop('selected_course_info', None)
        return

    # --- Collecting sharing screenshots flow (user already clicked Submit Screenshots) ---
    if state == "collecting_screenshots":
        count = user_screenshot_counter.get(user_id, 0) + 1
        user_screenshot_counter[user_id] = count
        await context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {count} received!")
        # forward screenshot to admin
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"📸 Sharing Screenshot {count} from {user.full_name or user.username}")

        if count >= 3:
            # After 3 screenshots, ask for consent to share phone number
            consent_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Share My Phone Number", callback_data="consent_share_phone")]
            ])
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ All 3 screenshots received! Thank you for sharing.\n\n"
                    "To finalize your course access, we need your phone number. "
                    "This helps us with delivery and future support. "
                    "Please click the button below to give your consent and proceed."
                ),
                reply_markup=consent_keyboard
            )
            user_state[user_id] = "awaiting_phone_consent"
        return

    # --- Unexpected photo ---
    await context.bot.send_message(chat_id=user_id,
                                   text="🤔 Unexpected photo. Please use /start to follow the proper flow. Contact admin for help @iam_akilesh07")

# ---------- Admin command to send course link ----------
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
            logger.exception("Error sending course link: %s", e)
            await update.message.reply_text(f"An error occurred: {e}")
    else:
        await update.message.reply_text("❌ Unauthorized")

# ---------- Unknown commands fallback ----------
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")

# ----------------- Register handlers -----------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("send_link", send_course_link))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
bot_app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))

# ----------------- Webhook endpoint -----------------
@fastapi_app.post(f"/{WEBHOOK_SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid secret token")

    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

# ----------------- Startup / Shutdown -----------------
@fastapi_app.on_event("startup")
async def on_startup():
    logger.info("Initializing Telegram bot application...")
    await bot_app.initialize()
    await bot_app.start()
    logger.info("Telegram bot application initialized and started.")

    if WEBHOOK_URL and WEBHOOK_SECRET_TOKEN:
        webhook_url_full = f"{WEBHOOK_URL}/{WEBHOOK_SECRET_TOKEN}"
        logger.info("Setting webhook to %s", webhook_url_full)
        await bot_app.bot.set_webhook(url=webhook_url_full, secret_token=WEBHOOK_SECRET_TOKEN)
        logger.info("Webhook set successfully.")
    else:
        logger.warning("WEBHOOK_URL or WEBHOOK_SECRET_TOKEN not set — webhook not configured.")

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    logger.info("Stopping Telegram bot application...")
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("Telegram bot application stopped.")

# Run with:
# uvicorn your_file_name:fastapi_app --host 0.0.0.0 --port 10000
