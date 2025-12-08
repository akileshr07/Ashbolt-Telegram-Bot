import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
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

COURSE_LINKS = {
    "react": {
        "warning": "🚨 STRICT WARNING — SINGLE-USER ACCESS ONLY 🚨\nThis link is for one user only.\nIf it is shared, forwarded, or accessed by multiple people, your access will be permanently revoked without notice.\nDO NOT forward, repost, or share this link under any circumstances.",
        "title": "React JS",
        "access_link": "https://1024terabox.com/s/1Y3oW9KXnDpgNDvAVgqS75w",
        "password": "7878"
    },
    "dsa": {
        "warning": "🚨 STRICT WARNING — SINGLE-USER ACCESS ONLY 🚨\nThis link is for one user only.\nIf it is shared, forwarded, or accessed by multiple people, your access will be permanently revoked without notice.\nDO NOT forward, repost, or share this link under any circumstances.",
        "title": "DSA",
        "access_link": "https://1024terabox.com/s/1bSAi4kTZNr_3vU8dw6beWA",
        "password": "7878"
    },
    "all_four": {
        "warning": "🚨 STRICT WARNING 🚨\nThis link is for single-user access only.\nIf this link is shared, forwarded, or accessed by multiple users, your access will be permanently revoked without notice.\nDO NOT forward, repost, or share this link under any circumstances.",
        "title": "All Four Courses Link",
        "access_link": "https://1024terabox.com/s/1S0ilCkU2M2gvNAeaL_2aHw",
        "password": "7878"
    },
    "nodejs": {
        "warning": "🚨 STRICT WARNING — SINGLE-USER ACCESS ONLY 🚨\nThis link is for one user only.\nIf it is shared, forwarded, or accessed by multiple people, your access will be permanently revoked without notice.\nDO NOT forward, repost, or share this link under any circumstances.",
        "title": "Node JS",
        "access_link": "https://1024terabox.com/s/108ZGHCww19zCU7iux9tuxA",
        "password": "7878"
    },
    "frontend_design": {
        "warning": "🚨 STRICT WARNING — SINGLE-USER ACCESS ONLY 🚨\nThis link is for one user only.\nIf it is shared, forwarded, or accessed by multiple people, your access will be permanently revoked without notice.\nDO NOT forward, repost, or share this link under any circumstances.",
        "title": "Frontend Design",
        "access_link": "https://1024terabox.com/s/1NPgtKbO_bWzP1SpNJWa0Lw",
        "password": "7878"
    }
}

# ----------------- Helper -----------------
def notify_admin_sync(user, message, photo=None):
    username = f"@{user.username}" if user.username else "N/A"
    admin_message = (
        "👤 User Action\n"
        f"{message}\n"
        f"🆔 ID: {user.id}\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"📧 Username: {username}\n"
    )

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

def get_course_key_from_callback(callback_data: str) -> str | None:
    mapping = {
        "buy_react": "react",
        "buy_frontend_sd": "frontend_design",
        "buy_nodejs": "nodejs",
        "buy_dsa": "dsa",
        "buy_bundle": "all_four",
    }
    return mapping.get(callback_data)

def build_admin_summary_text(user, chat_id, course_key: str | None, extra_note: str = "") -> str:
    username = f"@{user.username}" if user.username else "N/A"
    if course_key and course_key in COURSE_LINKS:
        course_title = COURSE_LINKS[course_key]["title"]
    else:
        course_title = "Unknown Course"

    text = (
        "🔎 Review request for course access\n\n"
        f"🆔 ID: {chat_id}\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"📧 Username: {username}\n"
        f"📚 Course: {course_title}\n"
    )
    if extra_note:
        text += f"{extra_note}\n"
    text += "\nAdmin options:"
    return text

def build_admin_keyboard(chat_id, course_key: str | None):
    key = course_key or "unknown"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Access Provided",
                callback_data=f"admin|approve|{chat_id}|{key}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Rejected",
                callback_data=f"admin|reject|{chat_id}|{key}"
            )
        ],
        [
            InlineKeyboardButton(
                "🤷 Ignored",
                callback_data=f"admin|ignore|{chat_id}|{key}"
            )
        ],
    ])

# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id

    keyboard = [
        [InlineKeyboardButton("1. Namaste DSA ₹49", callback_data="buy_dsa")],
        [InlineKeyboardButton("2. Namaste React ₹29", callback_data="buy_react")],
        [InlineKeyboardButton("3. Namaste Node.js ₹29", callback_data="buy_nodejs")],
        [InlineKeyboardButton("4. Namaste Frontend System Design ₹29", callback_data="buy_frontend_sd")],
        [InlineKeyboardButton("5. All four bundle ₹99", callback_data="buy_bundle")]
    ]
    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nPlease choose a course option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Notify admin that user has started the bot and show basic control panel
    notify_admin_sync(user, "User started the bot")

    username = f"@{user.username}" if user.username else "N/A"
    admin_text = (
        "🔎 New user started the bot\n\n"
        f"🆔 ID: {chat_id}\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"📧 Username: {username}\n"
        "Status: Just started, no course selected yet.\n\n"
        "Admin options:"
    )
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Allow Flow",
                callback_data=f"admin_start|approve|{chat_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Reject Now",
                callback_data=f"admin_start|reject|{chat_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🤷 Ignore",
                callback_data=f"admin_start|ignore|{chat_id}"
            )
        ],
    ])
    try:
        await bot_app.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=admin_keyboard
        )
    except Exception as e:
        logger.warning(f"Failed to send admin start panel: {e}")

# ----------------- Button Handler -----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat_id

    data = query.data

    # ---------- Admin START decision buttons ----------
    if data.startswith("admin_start|"):
        # Format: admin_start|action|user_id
        parts = data.split("|")
        if len(parts) != 3:
            await query.answer("Invalid admin action.", show_alert=True)
            return

        action, target_id_str = parts[1], parts[2]

        if query.from_user.id != ADMIN_ID:
            await query.answer("Only admin can use this.", show_alert=True)
            return

        try:
            target_user_id = int(target_id_str)
        except ValueError:
            await query.answer("Invalid user id.", show_alert=True)
            return

        if action == "approve":
            # Just inform the user that they can continue normally
            try:
                await bot_app.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        "✅ Your journey with AshBolt Bot is approved.\n"
                        "Please follow all payment and promo steps carefully to get course access."
                    )
                )
                await query.edit_message_text(
                    f"✅ Allowed user {target_user_id} to continue the flow."
                )
            except Exception as e:
                logger.exception("Failed to notify user on approve (start): %s", e)
                await query.answer("Failed to notify user.", show_alert=True)
            return

        if action == "reject":
            msg = (
                "🚫 Your access for the course is rejected because you are not following "
                "the promo message steps properly.\n\n"
                "👉 Click /start to follow the promo steps properly.\n"
                "If you have any doubt, contact admin @iam_akilesh07"
            )
            try:
                await bot_app.bot.send_message(chat_id=target_user_id, text=msg)
                await query.edit_message_text(
                    f"❌ Rejected access for user {target_user_id} at start."
                )
            except Exception as e:
                logger.exception("Failed to send rejection (start) to user: %s", e)
                await query.answer("Failed to notify user.", show_alert=True)

            user_state.pop(target_user_id, None)
            user_screenshot_counter.pop(target_user_id, None)
            return

        if action == "ignore":
            try:
                await query.edit_message_text(
                    f"🤷 Ignored user {target_user_id} at start. No action taken."
                )
            except Exception as e:
                logger.exception("Failed to edit admin start message: %s", e)
            return

        await query.answer("Unknown admin action.", show_alert=True)
        return

    # ---------- Admin FINAL decision buttons ----------
    if data.startswith("admin|"):
        # Format: admin|action|user_id|course_key
        parts = data.split("|")
        if len(parts) != 4:
            await query.answer("Invalid admin action.", show_alert=True)
            return

        action, target_id_str, course_key = parts[1], parts[2], parts[3]

        if query.from_user.id != ADMIN_ID:
            await query.answer("Only admin can use this.", show_alert=True)
            return

        try:
            target_user_id = int(target_id_str)
        except ValueError:
            await query.answer("Invalid user id.", show_alert=True)
            return

        if action == "approve":
            details = COURSE_LINKS.get(course_key)
            if not details:
                await query.answer("Invalid course selected.", show_alert=True)
                return

            text = (
                f"{details['warning']}\n\n"
                f"🎓 Course: {details['title']}\n"
                f"🔗 Access Link: {details['access_link']}\n"
                f"🔐 Password: {details['password']}"
            )
            try:
                await bot_app.bot.send_message(chat_id=target_user_id, text=text)
                await query.edit_message_text(
                    f"✅ Approved and sent {details['title']} to user {target_user_id}."
                )
            except Exception as e:
                logger.exception("Failed to send course to user: %s", e)
                await query.answer("Failed to send course to user.", show_alert=True)

            # Clear state for that user
            user_state.pop(target_user_id, None)
            user_screenshot_counter.pop(target_user_id, None)
            return

        elif action == "reject":
            msg = (
                "🚫 Your access for the course is rejected because you are not following "
                "the promo message steps properly.\n\n"
                "👉 Click /start to follow the promo steps properly.\n"
                "If you have any doubt, contact admin @iam_akilesh07"
            )
            try:
                await bot_app.bot.send_message(chat_id=target_user_id, text=msg)
                await query.edit_message_text(
                    f"❌ Rejected course access for user {target_user_id}."
                )
            except Exception as e:
                logger.exception("Failed to send rejection to user: %s", e)
                await query.answer("Failed to notify user.", show_alert=True)

            user_state.pop(target_user_id, None)
            user_screenshot_counter.pop(target_user_id, None)
            return

        elif action == "ignore":
            msg = (
                "⚠ Please send a proper payment receipt.\n\n"
                "If you have any doubt, contact admin @iam_akilesh07"
            )
            try:
                await bot_app.bot.send_message(chat_id=target_user_id, text=msg)
                await query.edit_message_text(
                    f"🤷 Ignored; asked user {target_user_id} for proper payment receipt."
                )
            except Exception as e:
                logger.exception("Failed to send ignore message to user: %s", e)
                await query.answer("Failed to notify user.", show_alert=True)

            # Keep state as-is so user can send again
            return

        else:
            await query.answer("Unknown admin action.", show_alert=True)
            return

    # ---------- Course Selection ----------
    if data in ("buy_react", "buy_frontend_sd", "buy_nodejs", "buy_dsa", "buy_bundle"):
        amount_to_pay = "₹29"
        selected_option_message = ""
        course_key = get_course_key_from_callback(data)

        if data == "buy_react":
            selected_option_message = "chose 'Namaste React' (₹29)"
        elif data == "buy_frontend_sd":
            selected_option_message = "chose 'Namaste Frontend System Design' (₹29)"
        elif data == "buy_nodejs":
            selected_option_message = "chose 'Namaste Node.js' (₹29)"
        elif data == "buy_dsa":
            selected_option_message = "chose 'Namaste DSA' (₹49)"
            amount_to_pay = "₹49"
        elif data == "buy_bundle":
            selected_option_message = "chose 'All four bundle' (₹99)"
            amount_to_pay = "₹99"

        notify_admin_sync(user, f"User {selected_option_message}")
        context.user_data['selected_course_info'] = {
            'message': selected_option_message,
            'amount': amount_to_pay,
            'course_key': course_key
        }

        course_name = selected_option_message.split("chose '")[1].split("'")[0]
        await query.message.reply_text(
            f"🔥 You selected: {course_name}\n\n"
            f"💸 Pay {amount_to_pay} to:\n\n💰 *{UPI_ID}*",
            parse_mode="Markdown"
        )
        await bot_app.bot.send_photo(
            chat_id=chat_id,
            photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
            caption=f"📷 Scan this QR to pay {amount_to_pay}"
        )
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="⬇️ Click below *after* payment, or send the screenshot now.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt")]]
            ),
            parse_mode="Markdown"
        )
        user_state[chat_id] = "awaiting_payment_screenshot"
        return

    # ---------- Send Payment Receipt button ----------
    if data == "send_receipt":
        user_state[chat_id] = "awaiting_payment_screenshot"
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="📥 Please send your payment screenshot now."
        )
        return

    # ---------- Submit sharing screenshots ----------
    if data == "submit_sharing_screenshots":
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="📤 Upload your 3 sharing screenshots now."
        )
        user_state[chat_id] = "collecting_screenshots"
        user_screenshot_counter[chat_id] = 0
        return

    # ---------- Don't want to share (₹50 extra) ----------
    if data == "dont_want_to_share":
        amount_to_pay = "₹50"
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text=(
                "🙅 You chose not to share the promo message.\n\n"
                f"💸 Please pay an extra {amount_to_pay} to continue.\n"
                f"Pay to UPI ID: *{UPI_ID}*"
            ),
            parse_mode="Markdown"
        )
        await bot_app.bot.send_photo(
            chat_id=chat_id,
            photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
            caption=f"📷 Scan this QR to pay {amount_to_pay} (skip sharing)"
        )
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="📥 After payment, send your payment screenshot here."
        )
        user_state[chat_id] = "awaiting_skip_sharing_payment_screenshot"
        return

    # ---------- Fallback ----------
    await bot_app.bot.send_message(
        chat_id=chat_id,
        text="❌ Unknown action. Use /start to restart."
    )

# ----------------- Handle Photos -----------------
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id
    state = user_state.get(chat_id)
    selected_info = context.user_data.get('selected_course_info', {})
    course_key = selected_info.get('course_key')
    amount_to_pay = selected_info.get('amount', '₹29')

    username = f"@{user.username}" if user.username else "N/A"

    # If user skipped pressing "Submit Screenshots" button and directly sends screenshots
    if state == "awaiting_sharing_button_click":
        user_state[chat_id] = "collecting_screenshots"
        user_screenshot_counter.setdefault(chat_id, 0)
        state = "collecting_screenshots"

    # --- Payment screenshot ---
    if state == "awaiting_payment_screenshot":
        caption = (
            "👤 User Action\n"
            "💬 Payment screenshot received\n"
            f"🆔 ID: {chat_id}\n"
            f"👤 Name: {user.first_name} {user.last_name or ''}\n"
            f"📧 Username: {username}\n"
        )
        if course_key and course_key in COURSE_LINKS:
            caption += f"📚 Course: {COURSE_LINKS[course_key]['title']}\n"
        caption += f"💸 Amount: {amount_to_pay}"

        await bot_app.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=caption
        )

        await bot_app.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ Payment is under verification.\n\n"
                "Now follow the final step to unlock the course.\n"
                "You must share the below promo post to 3 relevant Telegram groups and send screenshots.\n"
                "If you don't want to share, you can pay ₹50 extra to skip sharing."
            )
        )

        personal_text = (
            f"👋 Hello {username},\n\n"
            "💸 Your payment is under verification.\n"
            "If you don’t get course access in 24h, contact 👉 @iam_akilesh07"
        )
        try:
            await bot_app.bot.send_message(chat_id=user.id, text=personal_text)
        except Exception as e:
            logger.warning(f"Failed to send personal message to {user.id}: {e}")

        await bot_app.bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 To unlock the course, share the below promo post to 3 Telegram groups and send screenshots.\n"
                "⚠️ Don't share in personal/unrelated groups."
            )
        )
        await bot_app.bot.send_photo(
            chat_id=chat_id,
            photo="https://i.postimg.cc/K8BPYMMD/Untitled-design.png",
            caption=(
                "🚀 Akshay Saini's Dev Courses for just ₹29\n\n"
                "📚 Includes:\n"
                "   - React\n"
                "   - Frontend System Design\n"
                "   - Node.js\n"
                "   - DSA\n\n"
                "⚡ Access once, learn forever (with real projects)\n\n"
                "👉 To get it: Search **ashbolt_bot** on Telegram"
            )
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Submit Screenshots", callback_data="submit_sharing_screenshots")],
            [InlineKeyboardButton("🙅 Don't Want To Share", callback_data="dont_want_to_share")],
        ])
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="After sharing in 3 groups, click below and upload your screenshots.\nOr pay ₹50 extra to skip sharing.",
            reply_markup=keyboard
        )
        user_state[chat_id] = "awaiting_sharing_button_click"
        return

    # --- Skip-sharing payment screenshot (₹50 extra) ---
    if state == "awaiting_skip_sharing_payment_screenshot":
        caption = (
            "👤 User Action\n"
            "💬 Skip-sharing payment screenshot received (₹50 extra)\n"
            f"🆔 ID: {chat_id}\n"
            f"👤 Name: {user.first_name} {user.last_name or ''}\n"
            f"📧 Username: {username}\n"
        )
        if course_key and course_key in COURSE_LINKS:
            caption += f"📚 Course: {COURSE_LINKS[course_key]['title']}\n"
        caption += "💸 Amount: ₹50 (skip sharing)"

        await bot_app.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=caption
        )

        await bot_app.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ Your ₹50 skip-sharing payment is received and under review.\n"
                "You will receive course access here after admin approval.\n"
                "If you have any doubt, contact 👉 @iam_akilesh07"
            )
        )

        # Send admin summary with approve / reject / ignore buttons
        admin_text = build_admin_summary_text(
            user,
            chat_id,
            course_key,
            extra_note="Mode: Skip sharing (₹50 extra)"
        )
        admin_keyboard = build_admin_keyboard(chat_id, course_key)
        await bot_app.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=admin_keyboard
        )

        user_state[chat_id] = "pending_admin_decision"
        return

    # --- Collecting sharing screenshots ---
    if state == "collecting_screenshots":
        count = user_screenshot_counter.get(chat_id, 0) + 1
        user_screenshot_counter[chat_id] = count
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Screenshot {count} received!"
        )

        share_caption = (
            "👤 User Action\n"
            "💬 Promo sharing screenshot received\n"
            f"🆔 ID: {chat_id}\n"
            f"👤 Name: {user.first_name} {user.last_name or ''}\n"
            f"📧 Username: {username}\n"
            f"🖼 Screenshot No: {count}\n"
        )
        if course_key and course_key in COURSE_LINKS:
            share_caption += f"📚 Course: {COURSE_LINKS[course_key]['title']}"

        await bot_app.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=share_caption
        )

        if count >= 3:
            await bot_app.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ All 3 screenshots received!\n\n"
                    "Your access request will now be reviewed by the admin.\n"
                    "You will receive the course link here after approval."
                )
            )

            admin_text = build_admin_summary_text(
                user,
                chat_id,
                course_key,
                extra_note="Mode: Promo sharing (3 screenshots verified)"
            )
            admin_keyboard = build_admin_keyboard(chat_id, course_key)

            await bot_app.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=admin_keyboard
            )

            user_state[chat_id] = "pending_admin_decision"
        return

    await bot_app.bot.send_message(
        chat_id=chat_id,
        text="🤔 Unexpected photo. Use /start to follow the proper flow."
    )

# ----------------- Unknown Command -----------------
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")

# ----------------- Handlers -----------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
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
        await bot_app.bot.set_webhook(
            url=webhook_url_full,
            secret_token=WEBHOOK_SECRET_TOKEN
        )

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()
