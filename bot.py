import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import requests
import json
import random
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = '7583525993:AAGD3IKwGataqJgqMAkz6nyeCMmoc2A5QvY'

# n8n Webhook URL - vul hier je n8n webhook URL in
N8N_WEBHOOK_URL = 'https://primary-ovys-production.up.railway.app/webhook-test/9cd758ba-d510-4dfa-b3cf-cac1341c4940'

# Whitelist of allowed chat IDs
ALLOWED_CHATS = {
    1234567890,  # Example chat ID
    5493460969,  # Your chat ID
    2004519703,  # Jo's chat ID
}

def is_allowed(update: Update) -> bool:
    """Check if the chat ID is allowed to use the bot."""
    return update.effective_chat.id in ALLOWED_CHATS

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    try:
        chat_id = update.effective_chat.id
        if not is_allowed(update):
            logger.warning(f"Unauthorized access attempt from chat ID: {chat_id}")
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return

        logger.info(f"Start command received from authorized user {chat_id}")
        keyboard = [
            [
                InlineKeyboardButton("Select Trading Pair", callback_data='select_pair'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Welcome to SigmaPips! Please select an option:', reply_markup=reply_markup)
        logger.info(f"Start command processed for user {chat_id}")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        raise

def get_trading_pairs():
    """Get list of trading pairs."""
    return [
        'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF',
        'AUDUSD', 'USDCAD', 'NZDUSD', 'EURJPY'
    ]

def get_timeframes():
    """Get list of timeframes."""
    return [
        'M5', 'M15', 'M30',
        'H1', 'H4', 'D1'
    ]

def show_pairs(update: Update, context: CallbackContext) -> None:
    """Show available trading pairs."""
    pairs = get_trading_pairs()
    keyboard = []
    for pair in pairs:
        keyboard.append([InlineKeyboardButton(pair, callback_data=f'pair_{pair}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        update.callback_query.edit_message_text('Select a trading pair:', reply_markup=reply_markup)
    else:
        update.message.reply_text('Select a trading pair:', reply_markup=reply_markup)

def show_timeframes(update: Update, context: CallbackContext, selected_pair: str) -> None:
    """Show available timeframes."""
    timeframes = get_timeframes()
    keyboard = []
    for tf in timeframes:
        keyboard.append([InlineKeyboardButton(tf, callback_data=f'tf_{selected_pair}_{tf}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(f'Selected pair: {selected_pair}\nChoose timeframe:', reply_markup=reply_markup)

def send_to_n8n(pair: str, timeframe: str, update: Update, context: CallbackContext):
    """Send the request to n8n and handle the response."""
    try:
        # Bereid de data voor
        data = {
            "pair": pair,
            "timeframe": timeframe,
            "chat_id": update.effective_chat.id,
            "message_id": update.callback_query.message.message_id
        }
        
        # Stuur request naar n8n
        response = requests.post(N8N_WEBHOOK_URL, json=data)
        response.raise_for_status()
        
        # Bevestig dat het verzoek is verzonden
        update.callback_query.edit_message_text(
            f"🔄 Analyzing {pair} on {timeframe} timeframe...\n"
            f"Please wait while I process your request."
        )
        
    except Exception as e:
        logger.error(f"Error in send_to_n8n: {str(e)}")
        error_message = "❌ Sorry, er is een fout opgetreden. Probeer het later opnieuw."
        try:
            update.callback_query.edit_message_text(text=error_message)
        except Exception as e2:
            logger.error(f"Error sending error message: {str(e2)}")

def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    if not is_allowed(update):
        query.edit_message_text('Sorry, you are not authorized to use this bot.')
        return
    
    data = query.data
    
    if data == 'select_pair':
        show_pairs(update, context)
    elif data.startswith('pair_'):
        pair = data.split('_')[1]
        show_timeframes(update, context, pair)
    elif data.startswith('tf_'):
        _, pair, timeframe = data.split('_')
        send_to_n8n(pair, timeframe, update, context)

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.error(f'Update "{update}" caused error "{context.error}"')

def handle_unknown(update: Update, context: CallbackContext) -> None:
    """Handle unknown commands."""
    chat_id = update.effective_chat.id
    if not is_allowed(update):
        logger.warning(f"Unauthorized command attempt from chat ID: {chat_id}")
        update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    update.message.reply_text("Invalid input. Please use /start to begin again.")
    logger.warning(f"Unknown command received from {chat_id}: {update.message.text}")

def main() -> None:
    """Start the bot."""
    try:
        # Create the Updater and pass it your bot's token
        updater = Updater(TOKEN)

        # Get the dispatcher to register handlers
        dispatcher = updater.dispatcher

        # Register command handlers
        dispatcher.add_handler(CommandHandler("start", start))
        
        # Register callback query handler
        dispatcher.add_handler(CallbackQueryHandler(button_callback))
        
        # Register message handler for unknown commands
        dispatcher.add_handler(MessageHandler(Filters.command, handle_unknown))
        
        # Register error handler
        dispatcher.add_error_handler(error_handler)

        # Delete webhook before starting polling
        logger.info("Deleting webhook...")
        updater.bot.delete_webhook()
        
        # Start the Bot with drop_pending_updates=True to clean any pending updates
        logger.info("Bot started successfully")
        updater.start_polling(drop_pending_updates=True)

        # Run the bot until you press Ctrl-C
        updater.idle()
            
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise  # Re-raise the exception to let the shell script handle the restart

if __name__ == '__main__':
    main()
