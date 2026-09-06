import os
import logging
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

# ==============================================================================
# CONFIGURATION & ENVIRONMENT
# ==============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)
UPI_ID = os.environ.get("UPI_ID") or "akilesh.5@superyes"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN") or "CHANGE_ME_SECRET"
QR_IMAGE_URL = "https://i.postimg.cc/7LxDZLSW/Whats-App-Image-2025-12-26-at-9-28-51-PM.jpg"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment")

# ==============================================================================
# USER & ADMIN TEXT TEMPLATES / CONSTANTS
# ==============================================================================
# Helpers
def md(text: str) -> str:
    return escape_markdown(str(text), version=2)

# Command & Notification Strings (MarkdownV2 formatted)
MSG_WELCOME = "👋 Welcome to AshBolt Bot, {name}\\!\n\nSelect a course below:"
MSG_COURSE_INFO = "🔥 *You selected:* {label} \\(₹{price}\\)\n\n💸 *Pay to UPI:* `{upi}`"
MSG_SCAN_QR_CAPTION = "📷 Scan to pay ₹{price}"
MSG_AFTER_PAYMENT_PROMPT = "After payment, click below:"
MSG_PROMPT_SCREENSHOT = "📸 Send your payment screenshot now\\."
MSG_SCREENSHOT_RECEIVED = "✅ Screenshot sent to admin\\. You’ll get access soon\\."
MSG_ERR_NO_COURSE = "⚠️ No course selected\\. Use /start"
MSG_ERR_UNEXPECTED_PHOTO = "❌ Unexpected photo\\. Use /start"
MSG_ERR_UNKNOWN_OPTION = "❌ Unknown option\\. Use /start"
MSG_ERR_UNKNOWN_COMMAND = "Unknown command\\. Use /start"

# Admin Notifications & Responses
MSG_ADMIN_REJECT_USER = "⚠️ Payment could not be verified\\. Please restart using /start"
MSG_ADMIN_APPROVED_LOG = "✅ Access sent to user `{target_id}`"
MSG_ADMIN_REJECTED_LOG = "❌ Rejected user `{target_id}`"
MSG_ADMIN_INVALID_KEY = "⚠️ Invalid course key in callback: {course_key}"

ADMIN_SCREENSHOT_CAPTION_TEMPLATE = (
    "🧾 *New Payment Request*\n\n"
    "👤 *Name:* {name}\n"
    "🆔 *ID:* `{user_id}`\n"
    "📧 *Username:* {username}\n\n"
    "📚 *Course:* {course_label}\n"
    "💰 *Amount:* ₹{price}\n\n"
    "💬 *Caption:*\n{caption}"
)

# User Access Delivery Message (HTML formatted)
MSG_USER_ACCESS_GRANTED_HTML = (
    "🚨 <b>ACCESS ONLY</b> 🚨\n"
    "This link is for <b>one user only</b>.\n"
    "If it is shared, forwarded, or accessed by multiple people, your access will be "
    "permanently revoked without notice.\n"
    "DO NOT forward, repost, or share this link under any circumstances.\n\n"
    "📌 <b>Title:</b> {title}\n"
    "💰 <b>Paid Amount:</b> ₹{price}\n"
    "🔗 <b>Access Link:</b> {access_link}\n"
    "🔐 <b>Password:</b> {password}\n\n"
    "— Confidential material. Sharing = <b>immediate termination</b> of access."
)

# Button Labels
BTN_LABEL_DSA = "1. Namaste DSA ₹69"
BTN_LABEL_REACT = "2. Namaste React ₹39"
BTN_LABEL_NODE = "3. Namaste Node.js ₹39"
BTN_LABEL_SD = "4. Namaste Frontend SD ₹39"
BTN_LABEL_BUNDLE = "5. All four bundle ₹149"
BTN_LABEL_SUBMIT_SCREENSHOT = "📤 Submit Screenshot"
BTN_LABEL_APPROVE = "✅ Approve"
BTN_LABEL_REJECT = "❌ Reject"

# Callback Action Identifiers
CB_BUY_DSA = "buy_dsa"
CB_BUY_REACT = "buy_react"
CB_BUY_NODE = "buy_nodejs"
CB_BUY_FRONTEND_SD = "buy_frontend_sd"
CB_BUY_BUNDLE = "buy_bundle"
CB_SUBMIT_SCREENSHOT = "submit_screenshot"
CB_PREFIX_APPROVE = "admin_approve:"
CB_PREFIX_REJECT = "admin_reject:"

# ==============================================================================
# COURSE & CATALOG CONFIGURATION
# ==============================================================================
COURSE_LINKS = {
    "react": {
        "title": "React JS",
        "access_link": "https://1024terabox.com/s/1Y3oW9KXnDpgNDvAVgqS75w",
        "password": "7878",
    },
    "dsa": {
        "title": "DSA",
        "access_link": "https://1024terabox.com/s/1bSAi4kTZNr_3vU8dw6beWA",
        "password": "7878",
    },
    "all_four": {
        "title": "All Four Courses",
        "access_link": "https://1024terabox.com/s/1S0ilCkU2M2gvNAeaL_2aHw",
        "password": "7878",
    },
    "nodejs": {
        "title": "Node JS",
        "access_link": "https://1024terabox.com/s/108ZGHCww19zCU7iux9tuxA",
        "password": "7878",
    },
    "frontend_design": {
        "title": "Frontend Design",
        "access_link": "https://1024terabox.com/s/1NPgtKbO_bWzP1SpNJWa0Lw",
        "password": "7878",
    },
}

COURSE_CONFIG = {
    CB_BUY_REACT: {
        "label": "Namaste React",
        "price": 39,
        "link_key": "react",
    },
    CB_BUY_NODE: {
        "label": "Namaste Node.js",
        "price": 39,
        "link_key": "nodejs",
    },
    CB_BUY_DSA: {
        "label": "Namaste DSA",
        "price": 69,
        "link_key": "dsa",
    },
    CB_BUY_FRONTEND_SD: {
        "label": "Namaste Frontend System Design",
        "price": 39,
        "link_key": "frontend_design",
    },
    CB_BUY_BUNDLE: {
        "label": "All four bundle",
        "price": 149,
        "link_key": "all_four",
    },
}

# ==============================================================================
# STATE & SYSTEM INITIALIZATION
# ==============================================================================
STATE_COURSE_SELECTED = "course_selected"
STATE_WAITING_SCREENSHOT = "awaiting_payment_screenshot"
STATE_UNDER_REVIEW = "payment_under_review"

user_state = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()


# ==============================================================================
# COMMAND & EVENT HANDLERS
# ==============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    keyboard = [
        [InlineKeyboardButton(BTN_LABEL_DSA, callback_data=CB_BUY_DSA)],
        [InlineKeyboardButton(BTN_LABEL_REACT, callback_data=CB_BUY_REACT)],
        [InlineKeyboardButton(BTN_LABEL_NODE, callback_data=CB_BUY_NODE)],
        [InlineKeyboardButton(BTN_LABEL_SD, callback_data=CB_BUY_FRONTEND_SD)],
        [InlineKeyboardButton(BTN_LABEL_BUNDLE, callback_data=CB_BUY_BUNDLE)],
    ]

    welcome_text = MSG_WELCOME.format(name=md(user.first_name))

    await update.message.reply_text(
        text=welcome_text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    user_state.pop(user_id, None)
    context.user_data.clear()


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    user_id = user.id

    await query.answer()

    # ---------------------- ADMIN APPROVAL ----------------------
    if user_id == ADMIN_ID and data.startswith(CB_PREFIX_APPROVE):
        _, target_id_str, course_key = data.split(":", 2)
        target_id = int(target_id_str)

        info = COURSE_LINKS.get(course_key)
        if not info:
            await query.message.reply_text(
                MSG_ADMIN_INVALID_KEY.format(course_key=course_key)
            )
            return

        price = next(
            cfg["price"]
            for cfg in COURSE_CONFIG.values()
            if cfg["link_key"] == course_key
        )

        msg = MSG_USER_ACCESS_GRANTED_HTML.format(
            title=info["title"],
            price=price,
            access_link=info["access_link"],
            password=info["password"],
        )

        await context.bot.send_message(
            chat_id=target_id,
            text=msg,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        await query.message.reply_text(
            text=MSG_ADMIN_APPROVED_LOG.format(target_id=target_id),
            parse_mode="MarkdownV2",
        )
        return

    # ---------------------- ADMIN REJECTION ----------------------
    if user_id == ADMIN_ID and data.startswith(CB_PREFIX_REJECT):
        _, target_id_str, course_key = data.split(":", 2)
        target_id = int(target_id_str)

        await context.bot.send_message(
            chat_id=target_id,
            text=MSG_ADMIN_REJECT_USER,
            parse_mode="MarkdownV2",
        )

        await query.message.reply_text(
            text=MSG_ADMIN_REJECTED_LOG.format(target_id=target_id),
            parse_mode="MarkdownV2",
        )
        return

    # ---------------------- SUBMIT SCREENSHOT ----------------------
    if data == CB_SUBMIT_SCREENSHOT:
        course_key = context.user_data.get("course_key")
        if not course_key:
            await context.bot.send_message(
                chat_id=user_id,
                text=MSG_ERR_NO_COURSE,
                parse_mode="MarkdownV2",
            )
            return

        user_state[user_id] = STATE_WAITING_SCREENSHOT

        await context.bot.send_message(
            chat_id=user_id,
            text=MSG_PROMPT_SCREENSHOT,
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

        course_text = MSG_COURSE_INFO.format(
            label=md(cfg["label"]),
            price=cfg["price"],
            upi=md(UPI_ID),
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=course_text,
            parse_mode="MarkdownV2",
        )

        await context.bot.send_photo(
            chat_id=user_id,
            photo=QR_IMAGE_URL,
            caption=MSG_SCAN_QR_CAPTION.format(price=cfg["price"]),
        )

        submit_btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton(BTN_LABEL_SUBMIT_SCREENSHOT, callback_data=CB_SUBMIT_SCREENSHOT)]]
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=MSG_AFTER_PAYMENT_PROMPT,
            reply_markup=submit_btn,
        )
        return

    # ---------------------- FALLBACK ----------------------
    await context.bot.send_message(
        chat_id=user_id,
        text=MSG_ERR_UNKNOWN_OPTION,
        parse_mode="MarkdownV2",
    )


async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_state.get(user_id) != STATE_WAITING_SCREENSHOT:
        await update.message.reply_text(
            text=MSG_ERR_UNEXPECTED_PHOTO,
            parse_mode="MarkdownV2",
        )
        return

    course_key = context.user_data.get("course_key")
    price = context.user_data.get("price")
    label = context.user_data.get("course_label")

    photo_id = update.message.photo[-1].file_id
    caption = md(update.message.caption or "No caption")
    username = md(f"@{user.username}" if user.username else "N/A")

    admin_caption = ADMIN_SCREENSHOT_CAPTION_TEMPLATE.format(
        name=md(user.first_name),
        user_id=user_id,
        username=username,
        course_label=md(label),
        price=price,
        caption=caption,
    )

    approve_callback = f"{CB_PREFIX_APPROVE}{user_id}:{course_key}"
    reject_callback = f"{CB_PREFIX_REJECT}{user_id}:{course_key}"

    review_buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(BTN_LABEL_APPROVE, callback_data=approve_callback),
                InlineKeyboardButton(BTN_LABEL_REJECT, callback_data=reject_callback),
            ]
        ]
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=admin_caption,
        parse_mode="MarkdownV2",
        reply_markup=review_buttons,
    )

    await update.message.reply_text(
        text=MSG_SCREENSHOT_RECEIVED,
        parse_mode="MarkdownV2",
    )

    user_state[user_id] = STATE_UNDER_REVIEW


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        text=MSG_ERR_UNKNOWN_COMMAND,
        parse_mode="MarkdownV2",
    )


# ==============================================================================
# BOT HANDLER REGISTRATION
# ==============================================================================
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
bot_app.add_handler(MessageHandler(filters.COMMAND, unknown_command))


# ==============================================================================
# FASTAPI LIFECYCLE & WEBHOOK ROUTE
# ==============================================================================
@fastapi_app.post(f"/{WEBHOOK_SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


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


@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()
