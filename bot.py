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

# ----------------- Config -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)
UPI_ID = os.environ.get("UPI_ID") or "6382344469@jio"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN")

# ----------------- Logging -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------------- App & Bot -----------------
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()

# In-memory flow state
user_state = {}  # user_id -> state string

# ----------------- Course Config -----------------
COURSE_LINKS = {
    "react": {
        "title": "React JS",
        "access_link": "https://1024terabox.com/s/1Y3oW9KXnDpgNDvAVgqS75w",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE-USER ACCESS ONLY 🚨\nDo NOT forward/share this link. Violations = permanent ban.",
    },
    "dsa": {
        "title": "DSA",
        "access_link": "https://1024terabox.com/s/1bSAi4kTZNr_3vU8dw6beWA",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE-USER ACCESS ONLY 🚨\nDo NOT forward/share this link. Violations = permanent ban.",
    },
    "all_four": {
        "title": "All Four Courses",
        "access_link": "https://1024terabox.com/s/1S0ilCkU2M2gvNAeaL_2aHw",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨\nDo NOT share this bundle link. Violations = permanent ban.",
    },
    "nodejs": {
        "title": "Node JS",
        "access_link": "https://1024terabox.com/s/108ZGHCww19zCU7iux9tuxA",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨",
    },
    "frontend_design": {
        "title": "Frontend Design",
        "access_link": "https://1024terabox.com/s/1NPgtKbO_bWzP1SpNJWa0Lw",
        "password": "7878",
        "warning": "🚨 STRICT WARNING — SINGLE USER ONLY 🚨",
    },
}

COURSE_CONFIG = {
    "buy_react": {"label": "Namaste React", "price": 39, "link_key": "react"},
    "buy_nodejs": {"label": "Namaste Node.js", "price": 39, "link_key": "nodejs"},
    "buy_dsa": {"label": "Namaste DSA", "price": 69, "link_key": "dsa"},
    "buy_frontend_sd": {"label": "Namaste Frontend System Design", "price": 39, "link_key": "frontend_design"},
    "buy_bundle": {"label": "All four bundle", "price": 149, "link_key": "all_four"},
}

QR_IMAGE_URL = "https://i.postimg.cc/3N67GnpM/qr.jpg"


# ----------------- Helper -----------------
def notify_admin_sync(message: str):
    async def send():
        try:
            if ADMIN_ID:
                await bot_app.bot.send_message(chat_id=ADMIN_ID, text=message)
        except Exception as e:
            logger.exception("Failed to notify admin: %s", e)

    try:
        bot_app.create_task(send())
    except Exception:
        asyncio.create_task(send())


# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    keyboard = [
        [InlineKeyboardButton("1. Namaste DSA ₹69", callback_data="buy_dsa")],
        [InlineKeyboardButton("2. Namaste React ₹39", callback_data="buy_react")],
        [InlineKeyboardButton("3. Namaste Node.js ₹39", callback_data="buy_nodejs")],
        [InlineKeyboardButton("4. Namaste Frontend System Design ₹39", callback_data="buy_frontend_sd")],
        [InlineKeyboardButton("5. All four bundle ₹149", callback_data="buy_bundle")],
    ]

    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\nSelect a course below:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    user_state.pop(user_id, None)
    context.user_data.clear()


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    data = query.data

    # ---------------------- ADMIN APPROVE ----------------------
    if user_id == ADMIN_ID and data.startswith("admin_approve:"):
        _, target_id, course_key = data.split(":")
        target_id = int(target_id)

        info = COURSE_LINKS[course_key]
        price = next(v["price"] for v in COURSE_CONFIG.values() if v["link_key"] == course_key)

        msg = (
            "🎉 *Your Course Access is Ready!*\n\n"
            f"📚 Course: *{info['title']}*\n"
            f"💰 Price: ₹{price}\n\n"
            f"🔗 Access Link:\n{info['access_link']}\n\n"
            f"🔐 Password:\n{info['password']}\n\n"
            f"{info['warning']}"
        )

        try:
            await context.bot.send_message(chat_id=target_id, text=msg, parse_mode="Markdown")
            await query.message.reply_text(f"✅ Successfully sent access to user: {target_id}")
        except Exception as e:
            logger.exception("Failed to send course access to %s: %s", target_id, e)
            await query.message.reply_text(f"⚠️ Failed to send access to {target_id}\nError: {e}")
        return

    # ---------------------- ADMIN REJECT ----------------------
    if user_id == ADMIN_ID and data.startswith("admin_reject:"):
        _, target_id, course_key = data.split(":")
        target_id = int(target_id)

        warn = (
            "⚠️ Your payment could not be verified.\n\n"
            "Please restart using /start.\n"
            "For help: @iam_akilesh07"
        )

        try:
            await context.bot.send_message(chat_id=target_id, text=warn)
            await query.message.reply_text(f"❌ Rejected user: {target_id}")
        except Exception as e:
            logger.exception("Failed to reject user %s: %s", target_id, e)
            await query.message.reply_text(f"⚠️ Failed to reject user {target_id}\nError: {e}")
        return

    # ---------------------- SUBMIT SCREENSHOT ----------------------
    if data == "submit_screenshot":
        user_state[user_id] = "awaiting_payment_screenshot"

        await context.bot.send_message(
            chat_id=user_id,
            text="📸 Send your payment screenshot now."
        )
        return

    # ---------------------- COURSE SELECTION ----------------------
    if data in COURSE_CONFIG:
        cfg = COURSE_CONFIG[data]

        context.user_data["course_key"] = cfg["link_key"]
        context.user_data["course_label"] = cfg["label"]
        context.user_data["price"] = cfg["price"]

        user_state[user_id] = "course_selected"

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🔥 You selected: {cfg['label']} (₹{cfg['price']})\n\n"
                f"💸 Pay to UPI ID:\n`{UPI_ID}`"
            ),
            parse_mode="Markdown",
        )

        await context.bot.send_photo(
            chat_id=user_id,
            photo=QR_IMAGE_URL,
            caption=f"📷 Scan to Pay ₹{cfg['price']}",
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

    await context.bot.send_message(chat_id=user_id, text="❌ Unknown option. Use /start")


async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    state = user_state.get(user_id)

    if state != "awaiting_payment_screenshot":
        await update.message.reply_text("❌ Unexpected photo. Use /start.")
        return

    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or "No caption"

    course_key = context.user_data.get("course_key")
    price = context.user_data.get("price")
    label = context.user_data.get("course_label")
    username = f"@{user.username}" if user.username else "N/A"

    admin_caption = (
        f"🧾 *New Payment Request*\n\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📧 Username: {username}\n\n"
        f"📚 Course: *{label}*\n"
        f"💰 Amount: ₹{price}\n\n"
        f"💬 User Caption:\n{caption}"
    )

    approve = f"admin_approve:{user_id}:{course_key}"
    reject = f"admin_reject:{user_id}:{course_key}"

    btns = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Approve", callback_data=approve)],
            [InlineKeyboardButton("❌ Reject", callback_data=reject)],
        ]
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=admin_caption,
        parse_mode="Markdown",
        reply_markup=btns,
    )

    await update.message.reply_text("✅ Screenshot sent to admin. You’ll get access soon.")
    user_state[user_id] = "payment_under_review"


# ----------------- Unknown Commands -----------------
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /start")


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

    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


# ----------------- Startup / Shutdown -----------------
@fastapi_app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    await bot_app.start()
    if WEBHOOK_URL and WEBHOOK_SECRET_TOKEN:
        await bot_app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/{WEBHOOK_SECRET_TOKEN}",
            secret_token=WEBHOOK_SECRET_TOKEN,
        )


@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()
