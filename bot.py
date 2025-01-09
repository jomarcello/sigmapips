import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
    Filters,
)
import requests
import json
import random
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = '7583525993:AAHybOQQJ0OOamxjCJMSSgQm5W3eMNAsMaM'

# Whitelist of allowed chat IDs
ALLOWED_CHATS = {
    1234567890,  # Example chat ID
    5493460969,  # Your chat ID
    2004519703,  # Jo's chat ID
}

# Market Data
MARKET_DATA = {
    'forex': {
        'name': 'Forex',
        'pairs': {
            'eurusd': 'EUR/USD',
            'gbpusd': 'GBP/USD',
            'usdjpy': 'USD/JPY',
            'audusd': 'AUD/USD',
            'usdcad': 'USD/CAD'
        }
    },
    'crypto': {
        'name': 'Crypto',
        'pairs': {
            'btcusd': 'BTC/USD',
            'ethusd': 'ETH/USD',
            'bnbusd': 'BNB/USD',
            'xrpusd': 'XRP/USD',
            'solusd': 'SOL/USD'
        }
    },
    'indices': {
        'name': 'Indices',
        'pairs': {
            'us30': 'US30',
            'us100': 'US100',
            'us500': 'US500',
            'eu50': 'EU50',
            'jp225': 'JP225'
        }
    }
}

def is_allowed(chat_id: int) -> bool:
    """Check if the chat ID is allowed to use the bot."""
    return chat_id in ALLOWED_CHATS

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.error(f'Update "{update}" caused error "{context.error}"')

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    try:
        chat_id = update.effective_chat.id
        if not is_allowed(chat_id):
            logger.warning(f"Unauthorized access attempt from chat ID: {chat_id}")
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return

        logger.info(f"Start command received from authorized user {chat_id}")
        keyboard = [
            [InlineKeyboardButton("Forex", callback_data='forex')],
            [InlineKeyboardButton("Crypto", callback_data='crypto')],
            [InlineKeyboardButton("Indices", callback_data='indices')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            'Welcome to the Trading Bot! Please choose a market to receive signals:',
            reply_markup=reply_markup
        )
        logger.info(f"Start command processed for user {chat_id}")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        raise

def generate_pair_buttons(market: str) -> list:
    """Generate pair buttons for a specific market."""
    pairs = MARKET_DATA[market]['pairs']
    buttons = []
    for pair_id, pair_name in pairs.items():
        buttons.append([InlineKeyboardButton(
            pair_name,
            callback_data=f'{market}_{pair_id}'
        )])
    return buttons

def generate_timeframe_buttons(callback_data: str) -> list:
    """Generate timeframe buttons."""
    return [
        [
            InlineKeyboardButton("15m", callback_data=f'{callback_data}_15m'),
            InlineKeyboardButton("H1", callback_data=f'{callback_data}_h1'),
            InlineKeyboardButton("H4", callback_data=f'{callback_data}_h4')
        ]
    ]

def send_to_n8n(pair: str, timeframe: str, update: Update, context: CallbackContext):
    """Process the trading signal directly."""
    try:
        # Here we can add the trading analysis logic that was in n8n
        analysis_result = analyze_trading_pair(pair, timeframe)
        
        # Format and send our own message
        message = (
            f"🎯 *Trading Signal Analysis*\n\n"
            f"📊 *Pair:* {pair}\n"
            f"⏱ *Timeframe:* {timeframe}\n\n"
            f"📈 *Analysis:*\n{analysis_result}\n\n"
            f"_Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        )
        
        # Send message with markdown formatting
        update.callback_query.edit_message_text(
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Successfully sent analysis for {pair} {timeframe}")
        
    except Exception as e:
        logger.error(f"Error in signal analysis: {str(e)}")
        error_message = "❌ Sorry, er is een fout opgetreden bij het analyseren. Probeer het later opnieuw."
        try:
            update.callback_query.edit_message_text(text=error_message)
        except Exception as e2:
            logger.error(f"Error sending error message: {str(e2)}")

def analyze_trading_pair(pair: str, timeframe: str) -> str:
    """Analyze the trading pair and return insights."""
    # Here we can implement the analysis logic that was previously in n8n
    # This is a simple example - you can make this as sophisticated as needed
    
    analysis = [
        "🔍 *Market Analysis:*",
        "- Current trend is bullish",
        "- Strong support at recent levels",
        "- Volume showing increasing interest",
        "",
        "📊 *Technical Indicators:*",
        "- RSI: 58 (Neutral)",
        "- MACD: Bullish crossover",
        "- Moving Averages: Above 200 EMA",
        "",
        "💡 *Recommendation:*",
        "Consider long position with tight stop loss"
    ]
    
    return "\n".join(analysis)

def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    if not is_allowed(chat_id):
        logger.warning(f"Unauthorized callback attempt from chat ID: {chat_id}")
        query.answer("Sorry, you are not authorized to use this bot.")
        return

    callback_data = query.data
    logger.info(f"Received callback: {callback_data}")

    # Parse callback data
    parts = callback_data.split('_')
    
    if len(parts) == 1:  # Market selection
        market = parts[0]
        keyboard = generate_pair_buttons(market)
        query.edit_message_text(
            text=f"Select a pair from {MARKET_DATA[market]['name']}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif len(parts) == 2:  # Pair selection
        market, pair = parts
        keyboard = generate_timeframe_buttons(callback_data)
        query.edit_message_text(
            text=f"Select timeframe for {MARKET_DATA[market]['pairs'][pair]}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif len(parts) == 3:  # Timeframe selection
        market, pair, timeframe = parts
        pair_name = MARKET_DATA[market]['pairs'][pair]
        logger.info(f"Generating signal for {pair_name} on {timeframe}")
        send_to_n8n(pair_name, timeframe, update, context)

def handle_unknown(update: Update, context: CallbackContext) -> None:
    """Handle unknown commands."""
    chat_id = update.effective_chat.id
    if not is_allowed(chat_id):
        logger.warning(f"Unauthorized command attempt from chat ID: {chat_id}")
        update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    update.message.reply_text("Invalid input. Please use /start to begin again.")
    logger.warning(f"Unknown command received from {chat_id}: {update.message.text}")

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log the error and send a message to the user."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    try:
        if update and update.effective_message:
            update.effective_message.reply_text(
                "Sorry, er is een fout opgetreden. Probeer /start om opnieuw te beginnen."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

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
