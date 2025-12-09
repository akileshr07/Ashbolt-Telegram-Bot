import os
import logging
import asyncio
import json
import time
from pathlib import Path
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
user_selected_course = {}  # chat_id -> course_key

# ----------------- JSON Storage -----------------
DATA_FILE = Path("data/users.json")
DATA_FILE.parent.mkdir(exist_ok=True)


def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


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


async def check_timers(user_id: int):
    data = load_data()
    uid = str(user_id)
    user = data.get(uid)

    if not user:
        return

    now = int(time.time())
    changed = False

    # Contact message after 15 minutes from start
    start_ts = user.get("start_timestamp")
    if start_ts and not user.get("contact_sent"):
        if now - start_ts >= 15 * 60:
            try:
                await bot_app.bot.send_message(
                    chat_id=user_id,
                    text="If you have any doubt, contact 👉 @iam_akilesh07"
                )
                user["contact_sent"] = True
                changed = True
            except Exception as e:
                logger.exception("Failed to send contact message to %s: %s", user_id, e)

    # Course auto-delivery
    payment_ts = user.get("payment_timestamp")
    course_sent = user.get("course_sent", False)
    clicked = user.get("clicked", False)
    click_ts = user.get("click_timestamp")

    if payment_ts and not course_sent:
        if not clicked:
            if now - payment_ts >= 7 * 60:
                await send_course_link_auto(user_id)
                user["course_sent"] = True
                changed = True
        else:
            base_ts = click_ts or payment_ts
            if now - base_ts >= 15 * 60:
                await send_course_link_auto(user_id)
                user["course_sent"] = True
                changed = True

    if changed:
        data[uid] = user
        save_data(data)


# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id

    data = load_data()
    uid = str(chat_id)
    u = data.get(uid, {})
    now = int(time.time())
    if "start_timestamp" not in u:
        u["start_timestamp"] = now
    if "contact_sent" not in u:
        u["contact_sent"] = False
    if "selected_course" not in u and user_selected_course.get(chat_id):
        u["selected_course"] = user_selected_course[chat_id]
    if "course_sent" not in u:
        u["course_sent"] = False
    data[uid] = u
    save_data(data)

    await check_timers(chat_id)

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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = query.message.chat_id

    await check_timers(user_id)
    await query.answer()

    # ---------- Course Selection ----------
    if query.data in ("buy_react", "buy_frontend_sd", "buy_nodejs", "buy_dsa", "buy_bundle"):
        amount_to_pay = "₹29"
        selected_option_message = ""
        course_key = None

        if query.data == "buy_react":
            selected_option_message = "chose 'Namaste React' (₹29)"
            course_key = "react"
        elif query.data == "buy_frontend_sd":
            selected_option_message = "chose 'Namaste Frontend System Design' (₹29)"
            course_key = "frontend_design"
        elif query.data == "buy_nodejs":
            selected_option_message = "chose 'Namaste Node.js' (₹29)"
            course_key = "nodejs"
        elif query.data == "buy_dsa":
            selected_option_message = "chose 'Namaste DSA' (₹49)"
            amount_to_pay = "₹49"
            course_key = "dsa"
        elif query.data == "buy_bundle":
            selected_option_message = "chose 'All four bundle' (₹99)"
            amount_to_pay = "₹99"
            course_key = "all_four"

        notify_admin_sync(user, f"User {selected_option_message}")
        context.user_data['selected_course_info'] = {
            'message': selected_option_message,
            'amount': amount_to_pay,
            'course_key': course_key
        }
        user_selected_course[user_id] = course_key

        data = load_data()
        uid = str(user_id)
        u = data.get(uid, {})
        u["selected_course"] = course_key
        if "start_timestamp" not in u:
            u["start_timestamp"] = int(time.time())
        if "contact_sent" not in u:
            u["contact_sent"] = False
        if "course_sent" not in u:
            u["course_sent"] = False
        data[uid] = u
        save_data(data)

        await query.message.reply_text(
            f"🔥 You selected: {selected_option_message.split('chose ')[1].capitalize()}\n\n"
            f"💸 Pay {amount_to_pay} to:\n\n💰 *{UPI_ID}*",
            parse_mode="Markdown"
        )
        await context.bot.send_photo(
            chat_id=user_id,
            photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
            caption=f"📷 Scan this QR to pay {amount_to_pay}"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="⬇️ Click below *after* payment, or send the screenshot now.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt")]]
            ),
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

        data = load_data()
        uid = str(user_id)
        u = data.get(uid, {})
        now = int(time.time())
        u["clicked"] = True
        u["click_timestamp"] = now
        if "payment_timestamp" not in u:
            u["payment_timestamp"] = now
        if "course_sent" not in u:
            u["course_sent"] = False
        data[uid] = u
        save_data(data)
        return

    # ---------- Don't want to share (skip ₹50 flow button) ----------
    if query.data == "dont_want_to_share":
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💡 Don’t want to share? Pay ₹50 extra to skip sharing and proceed.\n💸 Pay to: *{UPI_ID}*",
            parse_mode="Markdown"
        )
        await context.bot.send_photo(
            chat_id=user_id,
            photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
            caption="📷 Scan to pay ₹50 (skip sharing)"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="After payment, click below and send the screenshot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data="send_receipt_skip")]]
            )
        )
        user_state[user_id] = "ready_to_receive_payment_skip"

        data = load_data()
        uid = str(user_id)
        u = data.get(uid, {})
        now = int(time.time())
        u["clicked"] = True
        u["click_timestamp"] = now
        if "payment_timestamp" not in u:
            u["payment_timestamp"] = now
        if "course_sent" not in u:
            u["course_sent"] = False
        data[uid] = u
        save_data(data)
        return

    await context.bot.send_message(chat_id=user_id, text="❌ Unknown action. Use /start to restart.")


# ----------------- Handle Photos -----------------
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id
    state = user_state.get(user_id)

    await check_timers(user_id)

    # --- Standard Payment ---
    if state == "ready_to_receive_payment":
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=f"🧾 Payment from {user.full_name or user.username}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Payment is under verification. Please follow the steps below to unlock the course. "
                "This is the last part of the course purchase. You can skip the sharing requirement by paying extra; "
                "there is an option for this below."
            )
        )

        username = f"@{user.username}" if user.username else "bro"
        personal_text = (
            f"👋 Hello {username},\n\n"
            "💸 Your payment is under verification.\n"
            "If you don’t get course access in 24h, contact 👉 @iam_akilesh07"
        )
        try:
            await context.bot.send_message(chat_id=user.id, text=personal_text)
        except Exception as e:
            logger.warning(f"Failed to send personal message to {user.id}: {e}")

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 To unlock the course, share the below promo post to 3 Telegram groups and send screenshots.\n"
                "⚠️ Don't share in personal/unrelated groups."
            )
        )
        await context.bot.send_photo(
            chat_id=user_id,
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
            [InlineKeyboardButton("🙅‍♂️ Don't Want to Share", callback_data="dont_want_to_share")]
        ])
        await context.bot.send_message(chat_id=user_id, text="Choose one:", reply_markup=keyboard)
        user_state[user_id] = "awaiting_sharing_button_click"

        data = load_data()
        uid = str(user_id)
        u = data.get(uid, {})
        now = int(time.time())
        u["payment_timestamp"] = now
        u["clicked"] = False
        u["click_timestamp"] = None
        if "selected_course" not in u and user_selected_course.get(user_id):
            u["selected_course"] = user_selected_course[user_id]
        if "course_sent" not in u:
            u["course_sent"] = False
        if "start_timestamp" not in u:
            u["start_timestamp"] = now
        if "contact_sent" not in u:
            u["contact_sent"] = False
        data[uid] = u
        save_data(data)
        return

    # --- Skip ₹50 Payment ---
    if state == "ready_to_receive_payment_skip":
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=f"🧾 Skip-sharing Payment ₹50 from {user.full_name or user.username}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Payment received! You will receive your course access shortly."
        )

        username = f"@{user.username}" if user.username else "bro"
        personal_text = (
            f"👋 Hello {username},\n\n"
            "💸 Your ₹50 skip-sharing payment is under verification.\n"
            "If you don’t get course access in 24h, contact 👉 @iam_akilesh07"
        )
        try:
            await context.bot.send_message(chat_id=user.id, text=personal_text)
        except Exception as e:
            logger.warning(f"Failed to send personal message to {user.id}: {e}")

        user_state[user_id] = "awaiting_course_delivery_skip"
        user_screenshot_counter.pop(user_id, None)
        return

    # --- Collecting Sharing Screenshots ---
    if state == "collecting_screenshots":
        count = user_screenshot_counter.get(user_id, 0) + 1
        user_screenshot_counter[user_id] = count
        await context.bot.send_message(chat_id=user_id, text=f"✅ Screenshot {count} received!")
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=f"📸 Screenshot {count} from {user.full_name or user.username}"
        )

        if count >= 3:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ All 3 screenshots received! You will receive your course access shortly."
            )
            user_state[user_id] = "awaiting_course_delivery_from_sharing"
        return

    await context.bot.send_message(chat_id=user_id, text="🤔 Unexpected photo. Use /start to follow the proper flow.")


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

        data = load_data()
        uid = str(user_id)
        u = data.get(uid, {})
        u["course_sent"] = True
        data[uid] = u
        save_data(data)
    except Exception:
        await update.message.reply_text("❌ Usage: /send_link <user_id> <link> <password>")


# ----------------- Unknown Command -----------------
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    await check_timers(user_id)
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")


# ----------------- Handlers -----------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("send_link", send_course_link))
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
        await bot_app.bot.set_webhook(url=webhook_url_full, secret_token=WEBHOOK_SECRET_TOKEN)


@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()


# ----------------- Course Links -----------------
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


# ----------------- Auto Course Link Sender -----------------
async def send_course_link_auto(chat_id: int):
    data = load_data()
    uid = str(chat_id)
    user = data.get(uid, {})

    course_key = user_selected_course.get(chat_id) or user.get("selected_course")
    if not course_key:
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="We could not detect your selected course. Please use /start and select a course again."
        )
        return

    course = COURSE_LINKS.get(course_key)
    if not course:
        await bot_app.bot.send_message(
            chat_id=chat_id,
            text="Course configuration missing. Please contact 👉 @iam_akilesh07"
        )
        return

    text = (
        f"{course['warning']}\n\n"
        f"🎓 {course['title']} Access Details:\n"
        f"🔗 Link: {course['access_link']}\n"
        f"🔐 Password: {course['password']}"
    )
    await bot_app.bot.send_message(chat_id=chat_id, text=text)

    user["course_sent"] = True
    data[uid] = user
    save_data(data)
