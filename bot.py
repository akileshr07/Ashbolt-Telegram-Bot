import os
import logging
import asyncio
import httpx
from fastapi import FastAPI, Request, HTTPException
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
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
UPI_ID = os.environ.get("UPI_ID") or "ashboltbot@jio"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN") or "CHANGE_ME_SECRET"
QR_IMAGE_URL = "https://ibb.co/dwQDbPgN"

# Mandatory Channel Config
REQUIRED_CHANNEL_INVITE = "https://t.me/+ym4RnZoNubI1ZGE1"
# Set your channel ID here (Private channels usually start with -100...)
# e.g., os.environ.get("REQUIRED_CHANNEL_ID") or -1001234567890
REQUIRED_CHANNEL_ID = os.environ.get("REQUIRED_CHANNEL_ID")

GOOGLE_SHEET_WEBHOOK_URL = os.environ.get("GOOGLE_SHEET_WEBHOOK_URL", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment")

# ==============================================================================
# ANALYTICS LOGGER (NON-BLOCKING)
# ==============================================================================
http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

async def _send_sheet_post(payload: dict):
    if not GOOGLE_SHEET_WEBHOOK_URL or "YOUR_GOOGLE_APPS_SCRIPT" in GOOGLE_SHEET_WEBHOOK_URL:
        return
    try:
        response = await http_client.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload)
        if response.status_code >= 400:
            logging.getLogger(__name__).warning("Google Sheet HTTP Error: %s", response.status_code)
    except Exception as err:
        logging.getLogger(__name__).warning("Failed to log to Google Sheets: %s", err)

def log_to_sheet(user_id, username, name, step, course="", price=""):
    """Schedules sheet logging in background without delaying bot replies."""
    payload = {
        "user_id": str(user_id),
        "username": username or "N/A",
        "name": name or "Unknown",
        "step": step,
        "course": course,
        "price": str(price),
    }
    asyncio.create_task(_send_sheet_post(payload))

# ==============================================================================
# USER & ADMIN TEXT TEMPLATES / CONSTANTS
# ==============================================================================
def md(text: str) -> str:
    return escape_markdown(str(text), version=2)

MSG_WELCOME = "👋 Welcome to AshBolt Bot, {name}\\!\n\nSelect a course below:"
MSG_COURSE_INFO = "🔥 *You selected:* {label} \\(₹{price}\\)\n\n💸 *Pay to UPI:* `{upi}`"
MSG_SCAN_QR_CAPTION = "📷 Scan to pay ₹{price}"
MSG_AFTER_PAYMENT_PROMPT = "After payment, click below:"
MSG_PROMPT_SCREENSHOT = "📸 Send your payment screenshot now\\."
MSG_SCREENSHOT_RECEIVED = "✅ Screenshot sent to admin\\. You’ll get access soon\\."

MSG_FORCE_JOIN = (
    "⚠️️ *Mandatory Step: Join Our Channel*\n\n"
    "To proceed with verification and receive your course updates, "
    "you *must* join our channel below\\.\n\n"
    "After joining, click *Check Membership*\\."
)
MSG_NOT_JOINED_YET = "❌ You haven't joined the channel yet! Please join to proceed."

MSG_ERR_NO_COURSE = "⚠️ No course selected\\. Use /start"
MSG_ERR_UNEXPECTED_PHOTO = "❌ Unexpected photo\\. Use /start"
MSG_ERR_UNKNOWN_OPTION = "❌ Unknown option\\. Use /start"
MSG_ERR_UNKNOWN_COMMAND = "Unknown command\\. Use /start"

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

BTN_LABEL_DSA = "1. Namaste DSA ₹69"
BTN_LABEL_REACT = "2. Namaste React ₹39"
BTN_LABEL_NODE = "3. Namaste Node.js ₹39"
BTN_LABEL_SD = "4. Namaste Frontend SD ₹39"
BTN_LABEL_AI = "5. 🔥 Namaste AI ₹89"
BTN_LABEL_BUNDLE = "6. All five bundle ₹249"
BTN_LABEL_SUBMIT_SCREENSHOT = "📤 Submit Screenshot"
BTN_LABEL_APPROVE = "✅ Approve"
BTN_LABEL_REJECT = "❌ Reject"
BTN_LABEL_JOIN_CHANNEL = "📢 Join Official Channel"
BTN_LABEL_VERIFY_JOIN = "✅ Check Membership"

CB_BUY_DSA = "buy_dsa"
CB_BUY_REACT = "buy_react"
CB_BUY_NODE = "buy_nodejs"
CB_BUY_FRONTEND_SD = "buy_frontend_sd"
CB_BUY_AI = "buy_ai"
CB_BUY_BUNDLE = "buy_bundle"
CB_SUBMIT_SCREENSHOT = "submit_screenshot"
CB_CHECK_MEMBERSHIP = "check_channel_join"
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
    "ai": {
        "title": "Namaste AI",
        "access_link": "https://1024terabox.com/s/1z9qtIwLkA5rJGkmI0LZgsA",
        "password": "8787",
    },
    "all_five": {
        "title": "All Five Courses Bundle",
        "courses": ["dsa", "react", "nodejs", "frontend_design", "ai"],
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
    CB_BUY_AI: {
        "label": "Namaste AI",
        "price": 89,
        "link_key": "ai",
    },
    CB_BUY_BUNDLE: {
        "label": "All five bundle",
        "price": 249,
        "link_key": "all_five",
    },
}

# ==============================================================================
# STATE & SYSTEM INITIALIZATION
# ==============================================================================
STATE_COURSE_SELECTED = "course_selected"
STATE_WAITING_SCREENSHOT = "awaiting_payment_screenshot"
STATE_AWAITING_CHANNEL_JOIN = "awaiting_channel_join"
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
# HELPER FUNCTIONS
# ==============================================================================
async def is_user_in_channel(bot, user_id: int) -> bool:
    """Verifies if the user is a member/admin/owner of the required channel."""
    if not REQUIRED_CHANNEL_ID:
        # If no channel ID is configured, bypass check to avoid broken workflows
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ]
    except Exception as err:
        logger.error("Error checking channel membership for user %s: %s", user_id, err)
        return False


async def forward_screenshot_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Sends user payment request to admin once membership check is complete."""
    u_data = context.user_data
    photo_id = u_data.get("screenshot_photo_id")
    caption = u_data.get("screenshot_caption", "No caption")
    username = u_data.get("username", "N/A")
    name = u_data.get("first_name", "Unknown")
    label = u_data.get("course_label", "")
    price = u_data.get("price", "")
    course_key = u_data.get("course_key", "")

    admin_caption = ADMIN_SCREENSHOT_CAPTION_TEMPLATE.format(
        name=md(name),
        user_id=user_id,
        username=md(username),
        course_label=md(label),
        price=price,
        caption=md(caption),
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


# ==============================================================================
# COMMAND & EVENT HANDLERS
# ==============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    log_to_sheet(user_id, user.username, user.first_name, "STARTED_BOT")

    keyboard = [
        [InlineKeyboardButton(BTN_LABEL_DSA, callback_data=CB_BUY_DSA)],
        [InlineKeyboardButton(BTN_LABEL_REACT, callback_data=CB_BUY_REACT)],
        [InlineKeyboardButton(BTN_LABEL_NODE, callback_data=CB_BUY_NODE)],
        [InlineKeyboardButton(BTN_LABEL_SD, callback_data=CB_BUY_FRONTEND_SD)],
        [InlineKeyboardButton(BTN_LABEL_AI, callback_data=CB_BUY_AI)],
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

        if course_key == "all_five":
            bundle_courses = info.get("courses", [])
            for key in bundle_courses:
                course_item = COURSE_LINKS.get(key)
                if not course_item:
                    continue

                msg = MSG_USER_ACCESS_GRANTED_HTML.format(
                    title=course_item["title"],
                    price=price,
                    access_link=course_item["access_link"],
                    password=course_item["password"],
                )

                await context.bot.send_message(
                    chat_id=target_id,
                    text=msg,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        else:
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

        log_to_sheet(target_id, "N/A", "Customer", "PAYMENT_APPROVED", course_key, price)

        await query.message.reply_text(
            text=MSG_ADMIN_APPROVED_LOG.format(target_id=target_id),
            parse_mode="MarkdownV2",
        )
        return

    # ---------------------- ADMIN REJECTION ----------------------
    if user_id == ADMIN_ID and data.startswith(CB_PREFIX_REJECT):
        _, target_id_str, course_key = data.split(":", 2)
        target_id = int(target_id_str)

        log_to_sheet(target_id, "N/A", "Customer", "PAYMENT_REJECTED", course_key, "")

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

        log_to_sheet(
            user_id,
            user.username,
            user.first_name,
            "CLICKED_SUBMIT_SCREENSHOT",
            course_key,
            context.user_data.get("price", "")
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=MSG_PROMPT_SCREENSHOT,
            parse_mode="MarkdownV2",
        )
        return

    # ------------------ CHANNEL MEMBERSHIP VERIFY ------------------
    if data == CB_CHECK_MEMBERSHIP:
        joined = await is_user_in_channel(context.bot, user_id)
        if not joined:
            await query.answer(text="⚠️ You have not joined yet! Join first.", show_alert=True)
            return

        # Success - User joined! Forward the screenshot to admin
        await forward_screenshot_to_admin(context, user_id)
        user_state[user_id] = STATE_UNDER_REVIEW

        log_to_sheet(
            user_id,
            user.username,
            user.first_name,
            "JOINED_CHANNEL_AND_VERIFIED",
            context.user_data.get("course_key", ""),
            context.user_data.get("price", "")
        )

        await query.edit_message_text(
            text="🎉 *Verification successful\\!*\n\nYour screenshot has been forwarded to the admin\\. You'll get access soon\\.",
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

        log_to_sheet(
            user_id,
            user.username,
            user.first_name,
            "VIEWED_PRICE",
            cfg["link_key"],
            cfg["price"]
        )

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

    log_to_sheet(user_id, user.username, user.first_name, "SCREENSHOT_SUBMITTED", course_key, price)

    # Save photo information in user_data
    context.user_data["screenshot_photo_id"] = update.message.photo[-1].file_id
    context.user_data["screenshot_caption"] = update.message.caption or "No caption"
    context.user_data["username"] = f"@{user.username}" if user.username else "N/A"
    context.user_data["first_name"] = user.first_name

    # 1. Send the screenshot received message
    await update.message.reply_text(
        text=MSG_SCREENSHOT_RECEIVED,
        parse_mode="MarkdownV2",
    )

    # 2. Check if user is already in channel
    is_member = await is_user_in_channel(context.bot, user_id)
    if is_member:
        # If already joined, immediately forward to admin
        await forward_screenshot_to_admin(context, user_id)
        user_state[user_id] = STATE_UNDER_REVIEW
    else:
        # User has NOT joined: Lock progression and show mandatory join prompt
        user_state[user_id] = STATE_AWAITING_CHANNEL_JOIN
        channel_gate_buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(BTN_LABEL_JOIN_CHANNEL, url=REQUIRED_CHANNEL_INVITE)],
                [InlineKeyboardButton(BTN_LABEL_VERIFY_JOIN, callback_data=CB_CHECK_MEMBERSHIP)],
            ]
        )
        await update.message.reply_text(
            text=MSG_FORCE_JOIN,
            parse_mode="MarkdownV2",
            reply_markup=channel_gate_buttons,
        )


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
    await http_client.aclose()
