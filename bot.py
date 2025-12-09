import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.helpers import escape_markdown

# ----------------- Config -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)
UPI_ID = os.environ.get("UPI_ID") or "6382344469@jio"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN") or "CHANGE_ME_SECRET"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment")

if not ADMIN_ID:
    logging.warning("ADMIN_ID is 0 or not set. Admin actions will not work correctly.")

# ----------------- Logging -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------------- App & Bot -----------------
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()

# ----------------- In-memory state -----------------
STATE_COURSE_SELECTED = "course_selected"
STATE_WAITING_SCREENSHOT = "awaiting_payment_screenshot"
STATE_UNDER_REVIEW = "payment_under_review"

# user_id -> state string
user_state = {}

# ----------------- Course Config -----------------
COURSE_LINKS = {
    "react": {
        "title": "React JS",
        "access_link": "https://1024terabox.com/s/1Y3oW9KXnDpgNDvAVgqS75w",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨\nDo NOT forward/share this link.",
    },
    "dsa": {
        "title": "DSA",
        "access_link": "https://1024terabox.com/s/1bSAi4kTZNr_3vU8dw6beWA",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨\nDo NOT forward/share this link.",
    },
    "all_four": {
        "title": "All Four Courses",
        "access_link": "https://1024terabox.com/s/1S0ilCkU2M2gvNAeaL_2aHw",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨\nDo NOT forward/share this link.",
    },
    "nodejs": {
        "title": "Node JS",
        "access_link": "https://1024terabox.com/s/108ZGHCww19zCU7iux9tuxA",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨\nDo NOT forward/share this link.",
    },
    "frontend_design": {
        "title": "Frontend Design",
        "access_link": "https://1024terabox.com/s/1NPgtKbO_bWzP1SpNJWa0Lw",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨\nDo NOT forward/share this link.",
    },
}

COURSE_CONFIG = {
    "buy_react": {"label": "Namaste React", "price": 39, "link_key": "react"},
    "buy_nodejs": {"label": "Namaste Node.js", "price": 39, "link_key": "nodejs"},
    "buy_dsa": {"label": "Namaste DSA", "price": 69, "link_key": "dsa"},
    "buy_frontend_sd": {
        "label": "Namaste Frontend System Design",
        "price": 39,
        "link_key": "frontend_design",
    },
    "buy_bundle": {"label": "All four bundle", "price": 149, "link_key": "all_four"},
}

QR_IMAGE_URL = "https://i.postimg.cc/3N67GnpM/qr.jpg"


# ----------------- Helpers -----------------
def md(text: str) -> str:
    return escape_markdown(text, 2)


# ----------------- Start -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    keyboard = [
        [InlineKeyboardButton("1. Namaste DSA ₹69", callback_data="buy_dsa")],
        [InlineKeyboardButton("2. Namaste React ₹39", callback_data="buy_react")],
        [InlineKeyboardButton("3. Namaste Node.js ₹39", callback_data="buy_nodejs")],
        [InlineKeyboardButton("4. Namaste Frontend SD ₹39", callback_data="buy_frontend_sd")],
        [InlineKeyboardButton("5. All four bundle ₹149", callback_data="buy_bundle")],
    ]

    welcome_text = (
        f"👋 Welcome to AshBolt Bot, {md(user.first_name)}!\n\n"
        "Select a course below:"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    # Reset state
    user_state.pop(user_id, None)
    context.user_data.clear()


# ----------------- Button Handler -----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    user_id = user.id

    await query.answer()

    # ---------------------- ADMIN APPROVE ----------------------
    if user_id == ADMIN_ID and data.startswith("admin_approve:"):
        try:
            _, target_id_str, course_key = data.split(":", 2)
            target_id = int(target_id_str)
        except ValueError:
            await query.message.reply_text(
                "⚠️ Invalid approve callback data.",
                parse_mode="MarkdownV2",
            )
            return

        info = COURSE_LINKS.get(course_key)
        if not info:
            await query.message.reply_text(
                "⚠️ Unknown course key in approve.",
                parse_mode="MarkdownV2",
            )
            return

        # Find price from COURSE_CONFIG
        price = None
        for cfg in COURSE_CONFIG.values():
            if cfg["link_key"] == course_key:
                price = cfg["price"]
                break

        if price is None:
            await query.message.reply_text(
                "⚠️ Price not found for this course.",
                parse_mode="MarkdownV2",
            )
            return

        msg = (
            "🎉 *Your Course Access is Ready!*\n\n"
            f"📚 *{md(info['title'])}*\n"
            f"💰 Price: ₹{price}\n\n"
            f"🔗 Link:\n{md(info['access_link'])}\n\n"
            f"🔐 Password:\n{md(info['password'])}\n\n"
            f"{md(info['warning'])}"
        )

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=msg,
                parse_mode="MarkdownV2",
            )

            await query.message.reply_text(
                f"✅ Access sent to user `{target_id}`",
                parse_mode="MarkdownV2",
            )

        except Exception as e:
            logger.exception("Failed to send access to user %s", target_id)
            await query.message.reply_text(
                f"⚠️ Failed to send access to `{target_id}`\nError: `{md(str(e))}`",
                parse_mode="MarkdownV2",
            )

        return

    # ---------------------- ADMIN REJECT ----------------------
    if user_id == ADMIN_ID and data.startswith("admin_reject:"):
        try:
            _, target_id_str, course_key = data.split(":", 2)
            target_id = int(target_id_str)
        except ValueError:
            await query.message.reply_text(
                "⚠️ Invalid reject callback data.",
                parse_mode="MarkdownV2",
            )
            return

        warn = (
            "⚠️ Payment could not be verified.\n"
            "Please restart the process using /start and try again."
        )

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=warn,
                parse_mode="MarkdownV2",
            )

            await query.message.reply_text(
                f"❌ Rejected user `{target_id}`",
                parse_mode="MarkdownV2",
            )

        except Exception as e:
            logger.exception("Failed to reject user %s", target_id)
            await query.message.reply_text(
                f"⚠️ Failed to reject `{target_id}`\nError: `{md(str(e))}`",
                parse_mode="MarkdownV2",
            )

        return

    # ---------------------- SUBMIT SCREENSHOT ----------------------
    if data == "submit_screenshot":
        # Only allow if course was selected
        course_key = context.user_data.get("course_key")
        if not course_key:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ No course selected. Please use /start and choose a course first.",
                parse_mode="MarkdownV2",
            )
            return

        user_state[user_id] = STATE_WAITING_SCREENSHOT

        await context.bot.send_message(
            chat_id=user_id,
            text="📸 Send your payment screenshot now.",
            parse_mode="MarkdownV2",
        )
        return

    # ---------------------- COURSE SELECTION ----------------------
    if data in COURSE_CONFIG:
        cfg = COURSE_CONFIG[data]

        context.user_data["course_key"] = cfg["link_key"]
        context.user_data["course_label"] = cfg["label"]
        context.user_data["price"] = cfg["price"]

        user_state[user_id] = STATE_COURSE_SELECTED

        course_text = (
            f"🔥 *You selected:* {md(cfg['label'])} (₹{cfg['price']})\n\n"
            f"💸 *Pay to UPI:* `{md(UPI_ID)}`"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=course_text,
            parse_mode="MarkdownV2",
        )

        await context.bot.send_photo(
            chat_id=user_id,
            photo=QR_IMAGE_URL,
            caption=f"📷 Scan to pay ₹{cfg['price']}",
        )

        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📤 Submit Screenshot", callback_data="submit_screenshot")]]
        )

        await context.bot.send_message(
            chat_id=user_id,
            text="After payment, click below:",
            reply_markup=btn,
        )
        return

    # ---------------------- Unknown button ----------------------
    await context.bot.send_message(
        chat_id=user_id,
        text="❌ Unknown option. Use /start",
        parse_mode="MarkdownV2",
    )


# ----------------- Handle Screenshot -----------------
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_state.get(user_id) != STATE_WAITING_SCREENSHOT:
        await update.message.reply_text(
            "❌ Unexpected photo. Use /start",
            parse_mode="MarkdownV2",
        )
        return

    course_key = context.user_data.get("course_key")
    price = context.user_data.get("price")
    label = context.user_data.get("course_label")

    if not course_key or not price or not label:
        # Something went wrong / user_data cleared
        await update.message.reply_text(
            "⚠️ Session expired. Please use /start and try again.",
            parse_mode="MarkdownV2",
        )
        user_state.pop(user_id, None)
        context.user_data.clear()
        return

    photo = update.message.photo
    if not photo:
        await update.message.reply_text(
            "⚠️ No photo found in this message. Please send the payment screenshot.",
            parse_mode="MarkdownV2",
        )
        return

    photo_id = photo[-1].file_id
    caption_raw = update.message.caption or "No caption"
    caption = md(caption_raw)

    username_value = f"@{user.username}" if user.username else "N/A"
    username_md = md(username_value)

    admin_caption = (
        "🧾 *New Payment Request*\n\n"
        f"👤 *Name:* {md(user.first_name)}\n"
        f"🆔 *ID:* `{user_id}`\n"
        f"📧 *Username:* {username_md}\n\n"
        f"📚 *Course:* {md(label)}\n"
        f"💰 *Amount:* ₹{price}\n\n"
        f"💬 *Caption:*\n{caption}"
    )

    approve_data = f"admin_approve:{user_id}:{course_key}"
    reject_data = f"admin_reject:{user_id}:{course_key}"

    btns = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Approve", callback_data=approve_data)],
            [InlineKeyboardButton("❌ Reject", callback_data=reject_data)],
        ]
    )

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=admin_caption,
            parse_mode="MarkdownV2",
            reply_markup=btns,
        )
    except Exception as e:
        logger.exception("Failed to send screenshot to admin")
        await update.message.reply_text(
            f"⚠️ Failed to send screenshot to admin.\nError: `{md(str(e))}`",
            parse_mode="MarkdownV2",
        )
        return

    await update.message.reply_text(
        "✅ Screenshot sent to admin. You’ll get access soon.",
        parse_mode="MarkdownV2",
    )

    user_state[user_id] = STATE_UNDER_REVIEW


# ----------------- Unknown Commands -----------------
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Unknown command. Use /start",
        parse_mode="MarkdownV2",
    )


# ----------------- Handlers -----------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
bot_app.add_handler(MessageHandler(filters.COMMAND, unknown_command))


# ----------------- Webhook -----------------
@fastapi_app.post(f"/{WEBHOOK_SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


# ----------------- Startup / Shutdown -----------------
@fastapi_app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    await bot_app.start()
    if WEBHOOK_URL:
        await bot_app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/{WEBHOOK_SECRET_TOKEN}",
            secret_token=WEBHOOK_SECRET_TOKEN,
        )
        logger.info("Webhook set to %s/%s", WEBHOOK_URL, WEBHOOK_SECRET_TOKEN)
    else:
        logger.warning("WEBHOOK_URL not set. Bot will not receive updates.")


@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()
