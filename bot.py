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

# ----------------- Course Config -----------------
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

COURSE_CONFIG = {
    "buy_react": {
        "label": "Namaste React",
        "price": 39,
        "link_key": "react"
    },
    "buy_nodejs": {
        "label": "Namaste Node.js",
        "price": 39,
        "link_key": "nodejs"
    },
    "buy_dsa": {
        "label": "Namaste DSA",
        "price": 69,
        "link_key": "dsa"
    },
    "buy_frontend_sd": {
        "label": "Namaste Frontend System Design",
        "price": 39,
        "link_key": "frontend_design"
    },
    "buy_bundle": {
        "label": "All four bundle",
        "price": 149,
        "link_key": "all_four"
    }
}

# ----------------- Helper -----------------
def notify_admin_sync(message: str):
    async def send():
        try:
            await bot_app.bot.send_message(chat_id=ADMIN_ID, text=message)
        except Exception as e:
            logger.exception("Failed to notify admin: %s", e)

    try:
        bot_app.create_task(send())
    except Exception:
        asyncio.create_task(send())

def get_course_from_link_key(link_key: str):
    for key, cfg in COURSE_CONFIG.items():
        if cfg["link_key"] == link_key:
            return cfg
    return None

# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    keyboard = [
        [InlineKeyboardButton("1. Namaste DSA ₹69", callback_data="buy_dsa")],
        [InlineKeyboardButton("2. Namaste React ₹39", callback_data="buy_react")],
        [InlineKeyboardButton("3. Namaste Node.js ₹39", callback_data="buy_nodejs")],
        [InlineKeyboardButton("4. Namaste Frontend System Design ₹39", callback_data="buy_frontend_sd")],
        [InlineKeyboardButton("5. All four bundle ₹149", callback_data="buy_bundle")]
    ]

    text = (
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\n"
        "Please choose a course option below and follow the payment instructions carefully."
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data

    # Admin actions: approve or ignore payment
    if user.id == ADMIN_ID and data.startswith("approve:"):
        _, user_id_str, course_key = data.split(":")
        target_user_id = int(user_id_str)

        course_link_info = COURSE_LINKS.get(course_key)
        course_cfg = get_course_from_link_key(course_key)

        if not course_link_info or not course_cfg:
            await query.edit_message_caption(
                caption="⚠️ Error: Course configuration not found. Please check the bot setup."
            )
            return

        price = course_cfg["price"]

        message_text = (
            "🎉 *Your Course Access is Ready!*\n\n"
            f"📚 *Course:* {course_link_info['title']}\n"
            f"💰 *Price:* ₹{price}\n\n"
            f"🔗 *Access Link:*\n{course_link_info['access_link']}\n\n"
            f"🔐 *Password:*\n{course_link_info['password']}\n\n"
            f"{course_link_info['warning']}"
        )

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=message_text,
                parse_mode="Markdown"
            )
            await query.edit_message_caption(
                caption=f"✅ Approved and access sent to user {target_user_id}."
            )
        except Exception as e:
            logger.exception("Failed to send course access to user: %s", e)
            await query.edit_message_caption(
                caption=f"⚠️ Failed to send course access to user {target_user_id}. Check logs."
            )

        user_state.pop(target_user_id, None)
        return

    if user.id == ADMIN_ID and data.startswith("ignore:"):
        _, user_id_str, course_key = data.split(":")
        target_user_id = int(user_id_str)

        warning_text = (
            "⚠️ CLICK /START BUTTON TO RESTART THE PURCHASE. "
            "DO THE PAYMENT PROPERLY. "
            "IF YOU HAVE ANY DOUBTS CONTACT ADMIN @iam_akilesh07"
        )

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=warning_text
            )
            await query.edit_message_caption(
                caption=f"🚫 Payment request from user {target_user_id} was ignored. Warning sent."
            )
        except Exception as e:
            logger.exception("Failed to send ignore warning to user: %s", e)
            await query.edit_message_caption(
                caption=f"⚠️ Failed to notify user {target_user_id}. Check logs."
            )

        user_state.pop(target_user_id, None)
        return

    # User actions: course selection
    if data in COURSE_CONFIG:
        cfg = COURSE_CONFIG[data]
        label = cfg["label"]
        price = cfg["price"]
        link_key = cfg["link_key"]

        context.user_data["course_key"] = link_key
        context.user_data["price"] = price
        context.user_data["course_label"] = label

        user_state[chat_id] = "awaiting_payment_screenshot"

        message_text = (
            f"🔥 You selected: *{label}* (₹{price})\n\n"
            f"💸 Pay *₹{price}* to the UPI ID below and then send your payment screenshot.\n\n"
            f"💰 UPI ID: `{UPI_ID}`\n\n"
            "While sending the payment screenshot, please add this as the photo caption:\n\n"
            f"Name: <your full name>\n"
            f"Course: {label}\n"
            f"Amount Paid: ₹{price}\n\n"
            "After you send the screenshot, the admin will review and approve your access."
        )

        await query.message.reply_text(
            message_text,
            parse_mode="Markdown"
        )

        await context.bot.send_photo(
            chat_id=chat_id,
            photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
            caption=f"📷 Scan this QR to pay ₹{price}"
        )

        notify_admin_sync(f"User {user.id} selected {label} (₹{price}).")

        return

    # Fallback
    await context.bot.send_message(
        chat_id=chat_id,
        text="❌ Unknown action. Use /start to restart."
    )

async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = update.message.from_user
    state = user_state.get(chat_id)

    if state != "awaiting_payment_screenshot":
        await update.message.reply_text("🤔 Unexpected photo. Use /start to follow the proper purchase flow.")
        return

    photo_file_id = update.message.photo[-1].file_id
    caption_text = update.message.caption or "No caption provided."

    course_key = context.user_data.get("course_key")
    price = context.user_data.get("price")
    course_label = context.user_data.get("course_label")

    if not course_key or price is None or not course_label:
        await update.message.reply_text("⚠️ Internal error: course details missing. Please use /start again.")
        return

    admin_caption = (
        "🧾 *New Payment Request*\n\n"
        f"👤 User ID: `{chat_id}`\n"
        f"🧷 Name: {user.first_name} {user.last_name or ''}\n"
        f"📧 Username: @{user.username or 'N/A'}\n\n"
        f"📚 Course: *{course_label}*\n"
        f"💰 Expected Amount: ₹{price}\n\n"
        f"💬 User Caption:\n{caption_text}\n\n"
        "If everything looks correct, use the buttons below."
    )

    approve_cb = f"approve:{chat_id}:{course_key}"
    ignore_cb = f"ignore:{chat_id}:{course_key}"

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve & Send Access", callback_data=approve_cb)],
        [InlineKeyboardButton("🚫 Ignore Payment", callback_data=ignore_cb)]
    ])

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=admin_caption,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.exception("Failed to send payment screenshot to admin: %s", e)
        await update.message.reply_text("⚠️ Failed to send your receipt to admin. Please try again or contact support.")
        return

    await update.message.reply_text(
        "✅ Your payment receipt has been sent to the admin for verification.\n"
        "You will receive your course access link after approval."
    )

    user_state[chat_id] = "payment_under_review"

async def send_course_link_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return

    try:
        user_id = int(context.args[0])
        course_key = context.args[1]

        course_link_info = COURSE_LINKS.get(course_key)
        course_cfg = get_course_from_link_key(course_key)

        if not course_link_info or not course_cfg:
            await update.message.reply_text("⚠️ Error: Course configuration not found.")
            return

        price = course_cfg["price"]

        message_text = (
            "🎉 *Your Course Access is Ready!*\n\n"
            f"📚 *Course:* {course_link_info['title']}\n"
            f"💰 *Price:* ₹{price}\n\n"
            f"🔗 *Access Link:*\n{course_link_info['access_link']}\n\n"
            f"🔐 *Password:*\n{course_link_info['password']}\n\n"
            f"{course_link_info['warning']}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Sent course access manually.")
        user_state.pop(user_id, None)
    except Exception as e:
        logger.exception("Failed to send course link manually: %s", e)
        await update.message.reply_text("❌ Usage: /send_link <user_id> <course_key>")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")

# ----------------- Handlers -----------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("send_link", send_course_link_manual))
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
