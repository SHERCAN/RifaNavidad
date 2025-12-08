import os
import logging
import random
from typing import Dict, List, Tuple
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
MAX_USERS = int(os.getenv("MAX_USERS", "10"))
PASSWORD = os.getenv("PASSWORD", "secret123")
ADMIN_ID = os.getenv("ADMIN_ID")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for ConversationHandler
SELECTING_ACTION, TYPING_NICKNAME, TYPING_PASSWORD = range(3)

# Data Storage
# confirmed_participants: chat_id -> {"name": str, "username": str}
participants: Dict[int, Dict] = {}

# temporary_data: chat_id -> {"nickname": str, "password_ok": bool}
temp_user_data: Dict[int, Dict] = {}


def get_main_menu_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Creates the main menu keyboard based on user status."""
    data = temp_user_data.get(chat_id, {"nickname": None, "password_ok": False})
    
    # Status Icons
    nick_status = "✅" if data.get("nickname") else "❌"
    pass_status = "✅" if data.get("password_ok") else "❌"
    
    # Check if registered
    is_registered = chat_id in participants

    keyboard = []
    
    if is_registered:
        keyboard.append([InlineKeyboardButton("✅ Ya estás inscrito", callback_data="noop")])
    else:
        keyboard.append([
            InlineKeyboardButton(f"👤 Nickname {nick_status}", callback_data="set_nickname"),
            InlineKeyboardButton(f"🔑 Contraseña {pass_status}", callback_data="set_password")
        ])
        
        # Inscribirse button available only if both are set
        if data.get("nickname") and data.get("password_ok"):
            keyboard.append([InlineKeyboardButton("📝 Inscribirse a la Rifa", callback_data="join_raffle")])
        else:
            keyboard.append([InlineKeyboardButton("📝 Inscribirse (Completa datos)", callback_data="noop_disabled")])

    keyboard.append([InlineKeyboardButton("📊 Ver Estado", callback_data="status")])
    
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the initial menu."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Initialize temp data if new
    if chat_id not in temp_user_data:
        temp_user_data[chat_id] = {
            "nickname": user.first_name, # Default to telegram name
            "password_ok": False
        }

    await update.message.reply_text(
        "🎄 **¡Bienvenido a la Rifa Navideña!** 🎄\n\n"
        "Configura tus datos usando los botones de abajo para participar.",
        reply_markup=get_main_menu_keyboard(chat_id),
        parse_mode="Markdown"
    )
    return SELECTING_ACTION


async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button clicks in the main menu."""
    query = update.callback_query
    await query.answer() # Acknowledge
    
    data = query.data
    chat_id = update.effective_chat.id

    if data == "set_nickname":
        await query.edit_message_text("👤 Por favor, escribe el **nickname** que quieres usar:")
        return TYPING_NICKNAME

    elif data == "set_password":
        await query.edit_message_text("🔑 Por favor, escribe la **contraseña** del evento:")
        return TYPING_PASSWORD

    elif data == "join_raffle":
        # Final check
        user_data = temp_user_data.get(chat_id)
        if not (user_data and user_data.get("nickname") and user_data.get("password_ok")):
             await query.message.reply_text("❌ Faltan datos.")
             return SELECTING_ACTION

        if len(participants) >= MAX_USERS:
            await query.message.reply_text("⛔ Lo sentimos, el cupo está lleno.")
            await query.edit_message_text(
                "🎄 **Menú Principal**",
                reply_markup=get_main_menu_keyboard(chat_id),
                parse_mode="Markdown"
            )
            return SELECTING_ACTION

        # Register
        participants[chat_id] = {
             "name": user_data["nickname"],
             "username": update.effective_user.username
        }
        
        await query.edit_message_text(
            f"✅ **¡Inscrito correctamente!**\n\nEsperando participantes: {len(participants)}/{MAX_USERS}",
            reply_markup=get_main_menu_keyboard(chat_id),
            parse_mode="Markdown"
        )
        
        # Check raffle
        if len(participants) == MAX_USERS:
            await check_and_run_raffle(context)
            
        return SELECTING_ACTION

    elif data == "status":
        msg = (
            f"📊 **Estado de la Rifa**:\n"
            f"- Inscritos: {len(participants)} / {MAX_USERS}\n"
            f"- Tu estado: {'Inscrito ✅' if chat_id in participants else 'No inscrito ❌'}"
        )
        # Avoid editing matching content error by checking text? 
        # Easier to just send or careful edit.
        try:
            await query.edit_message_text(
                msg, 
                reply_markup=get_main_menu_keyboard(chat_id),
                parse_mode="Markdown"
            )
        except Exception:
            pass # Content same
        return SELECTING_ACTION
        
    elif data == "noop":
         await query.answer("Ya estás listo. ¡Espera al sorteo!")
         return SELECTING_ACTION
         
    elif data == "noop_disabled":
         await query.answer("Debes completar Nickname y Contraseña primero.", show_alert=True)
         return SELECTING_ACTION

    return SELECTING_ACTION


async def save_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the nickname and returns to menu."""
    text = update.message.text
    chat_id = update.effective_chat.id
    
    if chat_id not in temp_user_data:
        temp_user_data[chat_id] = {"nickname": None, "password_ok": False}
        
    temp_user_data[chat_id]["nickname"] = text
    
    await update.message.reply_text(
        f"✅ Nickname guardado: **{text}**",
        reply_markup=get_main_menu_keyboard(chat_id),
        parse_mode="Markdown"
    )
    return SELECTING_ACTION


async def save_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks password and returns to menu."""
    text = update.message.text
    chat_id = update.effective_chat.id
    
    if chat_id not in temp_user_data:
        temp_user_data[chat_id] = {"nickname": None, "password_ok": False}

    if text == PASSWORD:
        temp_user_data[chat_id]["password_ok"] = True
        await update.message.reply_text(
            "✅ Contraseña correcta.",
            reply_markup=get_main_menu_keyboard(chat_id),
            parse_mode="Markdown"
        )
    else:
        temp_user_data[chat_id]["password_ok"] = False
        await update.message.reply_text(
            "❌ Contraseña incorrecta. Intenta de nuevo en el menú.",
            reply_markup=get_main_menu_keyboard(chat_id),
            parse_mode="Markdown"
        )
        
    return SELECTING_ACTION


async def check_and_run_raffle(context: ContextTypes.DEFAULT_TYPE):
    """Logic to run raffle."""
    if len(participants) % 2 != 0:
        msg = f"⚠️ Límite ({MAX_USERS}) alcanzado, pero el número es IMPAR. No se puede sortear en parejas."
        for pid in participants:
             await context.bot.send_message(chat_id=pid, text=msg)
        return

    ids = list(participants.keys())
    random.shuffle(ids)
    
    pairs = []
    for i in range(0, len(ids), 2):
        pairs.append((ids[i], ids[i+1]))

    for u1_id, u2_id in pairs:
        u1_name = participants[u1_id]["name"]
        u2_name = participants[u2_id]["name"]
        
        try:
            await context.bot.send_message(
                chat_id=u1_id,
                text=f"🎁 **¡Resultados de la Rifa!** 🎁\n\nTu pareja secreta (mutua) es: **{u2_name}**"
            )
            await context.bot.send_message(
                chat_id=u2_id,
                text=f"🎁 **¡Resultados de la Rifa!** 🎁\n\nTu pareja secreta (mutua) es: **{u1_name}**"
            )
        except Exception as e:
            logger.error(f"Error sending to {u1_id}/{u2_id}: {e}")

    logger.info("Raffle finished.")


def main():
    if not TOKEN:
        print("Error: BOT_TOKEN missing.")
        return

    application = Application.builder().token(TOKEN).build()

    # Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(menu_button_handler)
            ],
            TYPING_NICKNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_nickname)
            ],
            TYPING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_password)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    
    # Simple status command outside conversation (optional, or make it part of it)
    # The menu has a status button, so this is just extra
    # application.add_handler(CommandHandler("status", status)) 

    print("Bot with UI running...")
    application.run_polling()

if __name__ == "__main__":
    main()
