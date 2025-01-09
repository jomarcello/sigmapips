import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import requests
import json
from datetime import datetime
import sys

# Enable logging with more detail
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = '7583525993:AAHWnOP1jPOM_PunvAHwHizFXLPIYkz9Iho'

# n8n Webhook URL
N8N_WEBHOOK_URL = 'https://primary-ovys-production.up.railway.app/webhook-test/webhook'

# Whitelist of allowed chat IDs
ALLOWED_CHATS = {
    1234567890,  # Example chat ID
    5493460969,  # Your chat ID
    2004519703,  # Jo's chat ID
}

# Market Data Structure
MARKET_DATA = {
    'forex': {
        'name': 'Forex',
        'instruments': [
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'
        ]
    },
    'crypto': {
        'name': 'Crypto',
        'instruments': [
            'BTCUSD', 'ETHUSD', 'BNBUSD', 'XRPUSD', 'SOLUSD'
        ]
    },
    'commodities': {
        'name': 'Commodities',
        'instruments': [
            'XAUUSD', 'XAGUSD', 'WTIUSD', 'BRENTUSD', 'COPPERUSD'
        ]
    },
    'indices': {
        'name': 'Indices',
        'instruments': [
            'US30', 'US500', 'USTEC', 'GER40', 'UK100'
        ]
    }
}

# Timeframes
TIMEFRAMES = ['15m', 'H1', 'H4']

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
        keyboard = []
        for market_id, market_data in MARKET_DATA.items():
            keyboard.append([InlineKeyboardButton(market_data['name'], callback_data=f'market_{market_id}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Welcome to SigmaPips! Select a market:', reply_markup=reply_markup)
        logger.info(f"Start command processed for user {chat_id}")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        raise

def show_instruments(update: Update, context: CallbackContext, market_id: str) -> None:
    """Show instruments for selected market."""
    market = MARKET_DATA[market_id]
    keyboard = []
    for instrument in market['instruments']:
        keyboard.append([InlineKeyboardButton(instrument, callback_data=f'inst_{market_id}_{instrument}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        f"Select {market['name']} instrument:",
        reply_markup=reply_markup
    )

def show_timeframes(update: Update, context: CallbackContext, market_id: str, instrument: str) -> None:
    """Show timeframe selection."""
    keyboard = []
    for tf in TIMEFRAMES:
        keyboard.append([InlineKeyboardButton(tf, callback_data=f'tf_{market_id}_{instrument}_{tf}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        f"Selected: {instrument}\nChoose timeframe:",
        reply_markup=reply_markup
    )

def send_to_n8n(market: str, instrument: str, timeframe: str, update: Update, context: CallbackContext):
    """Send the request to n8n and handle the response."""
    try:
        # Prepare data
        data = {
            "market": market,
            "instrument": instrument,
            "timeframe": timeframe,
            "chat_id": update.effective_chat.id,
            "message_id": update.callback_query.message.message_id
        }
        
        logger.debug(f"=== Starting n8n request ===")
        logger.debug(f"Webhook URL: {N8N_WEBHOOK_URL}")
        logger.debug(f"Request data: {json.dumps(data, indent=2)}")
        
        # Send request to n8n
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        logger.debug(f"Request headers: {headers}")
        
        response = requests.post(N8N_WEBHOOK_URL, json=data, headers=headers)
        
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response content: {response.text}")
        logger.debug("=== End n8n request ===")
        
        response.raise_for_status()
        
        # Confirm request sent
        market_name = MARKET_DATA[market]['name']
        message = (
            f"🔄 Analysis Request\n\n"
            f"Market: {market_name}\n"
            f"Instrument: {instrument}\n"
            f"Timeframe: {timeframe}\n\n"
            f"Status: Workflow started ✅"
        )
        update.callback_query.edit_message_text(message)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        error_message = (
            f"❌ Network Error\n"
            f"Please try again later."
        )
        update.callback_query.edit_message_text(text=error_message)
    except Exception as e:
        logger.error(f"General error in send_to_n8n: {str(e)}", exc_info=True)
        error_message = (
            f"❌ Error\n"
            f"Please try again later."
        )
        try:
            update.callback_query.edit_message_text(text=error_message)
        except Exception as e2:
            logger.error(f"Error sending error message: {str(e2)}", exc_info=True)

def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    if not is_allowed(update):
        query.edit_message_text('Sorry, you are not authorized to use this bot.')
        return
    
    data = query.data
    
    if data.startswith('market_'):
        market_id = data.split('_')[1]
        show_instruments(update, context, market_id)
    
    elif data.startswith('inst_'):
        _, market_id, instrument = data.split('_')
        show_timeframes(update, context, market_id, instrument)
    
    elif data.startswith('tf_'):
        _, market_id, instrument, timeframe = data.split('_')
        send_to_n8n(market_id, instrument, timeframe, update, context)

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
        updater = Updater(TOKEN, use_context=True)

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

        # Start the Bot
        logger.info("Starting bot...")
        updater.start_polling(allowed_updates=['message', 'callback_query'])
        logger.info("Bot started successfully")

        # Run the bot until you press Ctrl-C
        updater.idle()
            
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise  # Re-raise the exception to let the shell script handle the restart

if __name__ == '__main__':
    main()
