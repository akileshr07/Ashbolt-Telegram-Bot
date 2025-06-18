import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# Load config from env vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
UPI_ID = os.environ.get("UPI_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Example: https://ashboltbot.onrender.com
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN") # Add a secret token for security

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# App and state
fastapi_app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()

user_state = {}
user_screenshot_counter = {}

# ---------- Common Functions ----------
def notify_admin(user, message, photo=None, phone_number=None):
    admin_message = f"👤 User Action: {message}\n"
    admin_message += f"🆔 ID: {user.id}\n"
    admin_message += f"👤 Name: {user.first_name} {user.last_name or ''}\n"
    admin_message += f"📧 Username: @{user.username or 'N/A'}\n"
    if phone_number:
        admin_message += f"📱 Phone: {phone_number}\n" # Add phone number if provided

    async def send():
        if photo:
            await bot_app.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=admin_message)
        else:
            await bot_app.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    bot_app.create_task(send())

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    keyboard = [
        [InlineKeyboardButton("1. Namaste React ₹29", callback_data='buy_react')],
        [InlineKeyboardButton("2. Namaste Frontend System Design ₹29", callback_data='buy_frontend_sd')],
        [InlineKeyboardButton("3. Namaste Node.js ₹29", callback_data='buy_nodejs')],
        [InlineKeyboardButton("4. All three bundle ₹69", callback_data='buy_bundle')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome to AshBolt Bot, {user.first_name}!\n\n"
        "Please choose a course option:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = query.message.chat_id
    selected_option_message = ""
    amount_to_pay = "₹29"

    if query.data == 'buy_react':
        selected_option_message = "chose 'Namaste React' (₹29)"
    elif query.data == 'buy_frontend_sd':
        selected_option_message = "chose 'Namaste Frontend System Design' (₹29)"
    elif query.data == 'buy_nodejs':
        selected_option_message = "chose 'Namaste Node.js' (₹29)"
    elif query.data == 'buy_bundle':
        selected_option_message = "chose 'All three bundle' (₹69)"
        amount_to_pay = "₹69" # Update amount if bundle is chosen

    # If any of the 'buy' options were clicked, proceed with payment instructions directly
    if selected_option_message:
        notify_admin(user, f"User {selected_option_message}")
        
        # Store the selected course info temporarily
        context.user_data['selected_course_info'] = {'message': selected_option_message, 'amount': amount_to_pay}

        await query.message.reply_text(
            f"🔥 You selected: {selected_option_message.split('chose ')[1].capitalize()}\n\n"
            f"💸 Pay {amount_to_pay} to:\n\n💰 *{UPI_ID}*", parse_mode='Markdown'
        )
        await context.bot.send_photo(chat_id=user_id, photo="https://i.postimg.cc/3N67GnpM/qr.jpg",
                                     caption=f"📷 Scan this QR to pay {amount_to_pay}")
        keyboard = [[InlineKeyboardButton("📥 Send Payment Receipt", callback_data='send_receipt')]]
        await context.bot.send_message(chat_id=user_id,
                                       text="⬇️ Click below *after* payment, or send the screenshot now.",
                                       reply_markup=InlineKeyboardMarkup(keyboard)
        )
        user_state[user_id] = "ready_to_receive_payment"

    elif query.data == 'send_receipt': # Keep existing send_receipt logic
        await context.bot.send_message(chat_id=user_id,
            text="📥 Please send your payment screenshot now.")
        user_state[user_id] = "ready_to_receive_payment"
        return # Exit to prevent showing payment details again

    elif query.data == 'submit_sharing_screenshots': # Keep existing submit_sharing_screenshots logic
        await context.bot.send_message(chat_id=user_id,
            text="📤 Upload your 3 sharing screenshots now.")
        user_state[user_id] = "collecting_screenshots"
        user_screenshot_counter[user_id] = 0
        return # Exit to prevent showing payment details again

# ---------- Place handle_contact function BEFORE its usage in add_handler ----------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    contact = update.message.contact

    # Check if the user is in the state where we expect a phone number
    if user_state.get(user_id) == "awaiting_phone_number" and contact:
        phone_number = contact.phone_number
        notify_admin(user, "User shared phone number", phone_number=phone_number)
        
        await update.message.reply_text(
            "✅ Thank you for sharing your phone number! We will now proceed with verifying your details and providing course access. You'll be notified soon!",
            reply_markup=ReplyKeyboardRemove() # Remove the special keyboard
        )
        user_state[user_id] = "awaiting_admin_verification" # Set state for admin to verify and send link
        
        # Clear the temporarily stored course info if it exists (though not directly used here, good practice)
        if 'selected_course_info' in context.user_data:
            del context.user_data['selected_course_info']
    else:
        await update.message.reply_text("🤔 Unexpected contact sharing. Please use /start to follow the proper flow.")


async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = update.message.from_user
    photo_file_id = update.message.photo[-1].file_id

    if user_state.get(user_id) == "ready_to_receive_payment":
        # Notify admin about the payment screenshot
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
                                     caption=f"🧾 Payment from {user.full_name or user.username}")

        # Confirm receipt and state "under verification" to the user
        await context.bot.send_message(chat_id=user_id,
                                       text="✅ Payment proof received. Your payment is now *under verification*.",
                                       parse_mode='Markdown')

        # Now, proceed with the course details and sharing instructions.
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
            parse_mode='Markdown'
        )

        keyboard = [[InlineKeyboardButton("📤 Submit Screenshots", callback_data='submit_sharing_screenshots')]]
        await context.bot.send_message(chat_id=user_id,
            text="👇 Submit your 3 sharing screenshots",
            reply_markup=InlineKeyboardMarkup(keyboard))

        # Update user state to await the sharing button click
        user_state[user_id] = "awaiting_sharing_button_click"


    elif user_state.get(user_id) == "collecting_screenshots":
        user_screenshot_counter[user_id] = user_screenshot_counter.get(user_id, 0) + 1
        await context.bot.send_message(chat_id=user_id,
            text=f"✅ Screenshot {user_screenshot_counter[user_id]} received!")
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id,
            caption=f"📸 Sharing Screenshot {user_screenshot_counter[user_id]} from {user.full_name}")
        
        if user_screenshot_counter[user_id] == 3:
            # Now that all screenshots are received, ask for phone number
            phone_keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton("Share My Phone Number", request_contact=True)]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ All 3 screenshots received! Thank you for sharing.\n\n"
                    "Finally, please share your phone number with us. "
                    "This will help us contact you for course delivery and any future assistance."
                ),
                reply_markup=phone_keyboard
            )
            user_state[user_id] = "awaiting_phone_number" # Set state to await phone number

    else:
        await context.bot.send_message(chat_id=user_id,
            text="🤔 Unexpected photo. Please use /start to follow the proper flow. Contact admin for help @iam_akilesh07")

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
            logging.error(f"Error sending course link: {e}")
            await update.message.reply_text(f"An error occurred: {e}")
    else:
        await update.message.reply_text("❌ Unauthorized")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start to restart.")

# ---------- Add handlers ----------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("send_link", send_course_link))
bot_app.add_handler(CallbackQueryHandler(button_handler))
# Handler for when user shares their contact - this is now at the END of the flow
bot_app.add_handler(MessageHandler(filters.CONTACT & filters.PRIVATE, handle_contact))
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
bot_app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command)) # Catch any other text

# ---------- Webhook endpoint ----------
@fastapi_app.post(f"/{WEBHOOK_SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid secret token")

    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    # Process the update using the initialized application
    await bot_app.process_update(update)
    return {"ok": True}

# ---------- Set webhook and initialize application on startup ----------
@fastapi_app.on_event("startup")
async def on_startup():
    logging.info("Initializing Telegram bot application...")
    # Initialize the application
    await bot_app.initialize()

    # Start the application - this sets up the internal task queue etc.
    await bot_app.start()
    logging.info("Telegram bot application initialized and started.")

    # Set the webhook URL
    webhook_url_full = f"{WEBHOOK_URL}/{WEBHOOK_SECRET_TOKEN}"
    logging.info(f"Setting webhook to {webhook_url_full}")
    await bot_app.bot.set_webhook(
        url=webhook_url_full,
        secret_token=WEBHOOK_SECRET_TOKEN
    )
    logging.info("Webhook set successfully.")

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    logging.info("Stopping Telegram bot application...")
    # Stop the application gracefully on shutdown
    await bot_app.stop()
    await bot_app.shutdown()
    logging.info("Telegram bot application stopped.")

# To run this with uvicorn, you would use:
# uvicorn your_file_name:fastapi_app --host 0.0.0.0 --port 10000
