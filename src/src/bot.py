import os
import sys
import time
import logging
import json
from datetime import datetime
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("telegram_bot")

# Load environment variables
load_dotenv()

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '900'))  # Default: 15 minutes
EOD_REPORT_TIME = os.getenv('EOD_REPORT_TIME', '16:00')  # Default: 4:00 PM

class TelegramBot:
    """
    Class for Telegram bot integration with XAU/USD Trading Assistant
    """
    
    def __init__(self, token=None):
        """
        Initialize the Telegram Bot
        
        Parameters:
        token (str): Telegram Bot API token (optional, defaults to environment variable)
        """
        self.token = token or TELEGRAM_BOT_TOKEN
        
        if not self.token:
            logger.error("Telegram Bot token not provided")
            raise ValueError("Telegram Bot token is required")
        
        self.bot = telegram.Bot(token=self.token)
        self.updater = Updater(token=self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Initialize components
        from gold_price_monitor import GoldPriceMonitor
        from technical_analysis import TechnicalAnalysis
        from news_monitor import NewsMonitor
        from notification_system import NotificationSystem
        
        self.gold_monitor = GoldPriceMonitor(interval='5m', period='1d')
        self.news_monitor = NewsMonitor()
        self.notifier = NotificationSystem(check_interval=CHECK_INTERVAL)
        
        # Create directories if they don't exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Load registered users
        self.users_file = 'data/telegram_users.json'
        self.users = self._load_users()
        
        # Setup command handlers
        self._setup_handlers()
        
        logger.info(f"Telegram Bot initialized with token ending in ...{self.token[-5:]}")
    
    def _load_users(self):
        """
        Load registered users from file
        
        Returns:
        dict: Users data
        """
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading users file: {e}")
        
        # Default empty users data
        return {'users': []}
    
    def _save_users(self):
        """
        Save registered users to file
        """
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=4)
            logger.info(f"Saved {len(self.users['users'])} users to file")
        except Exception as e:
            logger.error(f"Error saving users file: {e}")
    
    def _setup_handlers(self):
        """
        Setup command handlers
        """
        # Command handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CommandHandler("price", self.price_command))
        self.dispatcher.add_handler(CommandHandler("signal", self.signal_command))
        self.dispatcher.add_handler(CommandHandler("news", self.news_command))
        self.dispatcher.add_handler(CommandHandler("report", self.report_command))
        self.dispatcher.add_handler(CommandHandler("settings", self.settings_command))
        
        # Message handler
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        # Error handler
        self.dispatcher.add_error_handler(self.error_handler)
        
        logger.info("Command handlers set up")
    
    def register_user(self, chat_id, username=None):
        """
        Register a new user
        
        Parameters:
        chat_id (int): Telegram chat ID
        username (str): Telegram username (optional)
        
        Returns:
        bool: True if new user registered, False if already registered
        """
        # Check if user already exists
        for user in self.users['users']:
            if user['chat_id'] == chat_id:
                logger.info(f"User {chat_id} already registered")
                return False
        
        # Add new user
        self.users['users'].append({
            'chat_id': chat_id,
            'username': username,
            'registered_at': datetime.now().isoformat(),
            'settings': {
                'price_alerts': True,
                'signal_alerts': True,
                'news_alerts': True,
                'eod_reports': True
            }
        })
        
        # Save users
        self._save_users()
        
        logger.info(f"New user registered: {chat_id} ({username})")
        return True
    
    def start_command(self, update, context):
        """
        Handle /start command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        chat_id = update.effective_chat.id
        username = update.effective_user.username
        
        # Register user
        is_new = self.register_user(chat_id, username)
        
        if is_new:
            message = (
                "🎉 Welcome to XAU/USD Trading Assistant! 🎉\n\n"
                "I'll send you alerts for:\n"
                "📈 Trading signals (Buy/Sell)\n"
                "💰 Price movements\n"
                "📰 Important gold-related news\n"
                "📊 End-of-day reports\n\n"
                "Use /help to see available commands."
            )
        else:
            message = (
                "Welcome back to XAU/USD Trading Assistant!\n\n"
                "Use /help to see available commands."
            )
        
        context.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Sent start message to {chat_id}")
    
    def help_command(self, update, context):
        """
        Handle /help command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        help_text = (
            "XAU/USD Trading Assistant Commands:\n\n"
            "/price - Get current gold price\n"
            "/signal - Get latest trading signal\n"
            "/news - Get latest gold news\n"
            "/report - Get latest EOD report\n"
            "/settings - Manage notification settings\n"
            "/help - Show this help message"
        )
        
        update.message.reply_text(help_text)
        logger.info(f"Sent help message to {update.effective_chat.id}")
    
    def price_command(self, update, context):
        """
        Handle /price command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        try:
            update.message.reply_text("Fetching current gold price...")
            
            # Fetch live data
            data = self.gold_monitor.fetch_live_data()
            
            if data is None:
                update.message.reply_text("Failed to fetch gold price data. Please try again later.")
                return
            
            # Get current price and change
            current_price = self.gold_monitor.get_current_price()
            change, percent_change = self.gold_monitor.get_price_change()
            
            # Generate chart
            chart_path = self.gold_monitor.plot_price_chart(save_path="charts/current_price.png")
            
            # Create message
            message = f"💰 Current XAU/USD Price: ${current_price:.2f}\n"
            
            if change is not None and percent_change is not None:
                direction = "up" if change > 0 else "down"
                emoji = "📈" if change > 0 else "📉"
                message += f"{emoji} Change: ${abs(change):.2f} ({abs(percent_change):.2f}%) {direction}\n"
            
            # Get price range
            low, high = self.gold_monitor.get_price_range()
            if low is not None and high is not None:
                message += f"Range: ${low:.2f} - ${high:.2f}\n"
            
            message += f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Send message with chart
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as chart:
                    update.message.reply_photo(photo=chart, caption=message)
            else:
                update.message.reply_text(message)
            
            logger.info(f"Sent price info to {update.effective_chat.id}")
            
        except Exception as e:
            logger.error(f"Error in price command: {e}")
            update.message.reply_text("An error occurred while fetching price data. Please try again later.")
    
    def signal_command(self, update, context):
        """
        Handle /signal command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        try:
            update.message.reply_text("Generating trading signal...")
            
            # Fetch live data
            data = self.gold_monitor.fetch_live_data()
            
            if data is None:
                update.message.reply_text("Failed to fetch gold price data. Please try again later.")
                return
            
            # Create technical analysis
            from technical_analysis import TechnicalAnalysis
            ta = TechnicalAnalysis(data)
            
            # Generate signals
            signals = ta.generate_signals()
            
            if signals is None:
                update.message.reply_text("Failed to generate trading signals. Please try again later.")
                return
            
            # Get signal summary
            summary = ta.get_signal_summary(signals)
            
            if summary is None:
                update.message.reply_text("Failed to generate signal summary. Please try again later.")
                return
            
            # Format message
            message = self.notifier._format_signal_message(summary)
            
            # Generate chart
            chart_path = ta.plot_indicators(signals, save_path="charts/current_signal.png")
            
            # Send message with chart
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as chart:
                    update.message.reply_photo(photo=chart, caption=message)
            else:
                update.message.reply_text(message)
            
            logger.info(f"Sent signal info to {update.effective_chat.id}")
            
        except Exception as e:
            logger.error(f"Error in signal command: {e}")
            update.message.reply_text("An error occurred while generating trading signal. Please try again later.")
    
    def news_command(self, update, context):
        """
        Handle /news command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        try:
            update.message.reply_text("Fetching latest gold news...")
            
            # Fetch news
            news = self.news_monitor.fetch_all_news()
            
            if news is None or news.empty:
                update.message.reply_text("Failed to fetch news. Please try again later.")
                return
            
            # Get latest news
            latest = self.news_monitor.get_latest_news(limit=5)
            
            if latest is None or latest.empty:
                update.message.reply_text("No recent news found.")
                return
            
            # Format message
            message = "📰 Latest Gold News 📰\n\n"
            
            for i, (_, article) in enumerate(latest.iterrows()):
                message += f"{i+1}. {article['title']}\n"
                message += f"   Source: {article['source']}\n"
                message += f"   Date: {article['date'].strftime('%Y-%m-%d %H:%M')}\n"
                message += f"   Impact: {article['impact']:.2f}\n"
                message += f"   URL: {article['url']}\n\n"
            
            # Get sentiment
            sentiment = self.news_monitor.analyze_news_sentiment()
            
            if sentiment:
                sentiment_emoji = "🟢" if sentiment['sentiment'] == "Bullish" else "🔴" if sentiment['sentiment'] == "Bearish" else "⚪"
                message += f"Overall Sentiment: {sentiment_emoji} {sentiment['sentiment']} (Score: {sentiment['score']:.2f})\n"
            
            update.message.reply_text(message)
            logger.info(f"Sent news info to {update.effective_chat.id}")
            
        except Exception as e:
            logger.error(f"Error in news command: {e}")
            update.message.reply_text("An error occurred while fetching news. Please try again later.")
    
    def report_command(self, update, context):
        """
        Handle /report command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        try:
            update.message.reply_text("Generating EOD report...")
            
            # Fetch live data
            data = self.gold_monitor.fetch_live_data()
            
            if data is None:
                update.message.reply_text("Failed to fetch gold price data. Please try again later.")
                return
            
            # Create technical analysis
            from technical_analysis import TechnicalAnalysis
            ta = TechnicalAnalysis(data)
            
            # Generate EOD report
            report = self.notifier.generate_eod_report(self.gold_monitor, ta, self.news_monitor)
            
            if report is None:
                update.message.reply_text("Failed to generate EOD report. Please try again later.")
                return
            
            # Send message with chart
            if 'technical_chart' in report['data'] and os.path.exists(report['data']['technical_chart']):
                with open(report['data']['technical_chart'], 'rb') as chart:
                    update.message.reply_photo(photo=chart, caption=report['message'])
            elif 'price_chart' in report['data'] and os.path.exists(report['data']['price_chart']):
                with open(report['data']['price_chart'], 'rb') as chart:
                    update.message.reply_photo(photo=chart, caption=report['message'])
            else:
                update.message.reply_text(report['message'])
            
            logger.info(f"Sent EOD report to {update.effective_chat.id}")
            
        except Exception as e:
            logger.error(f"Error in report command: {e}")
            update.message.reply_text("An error occurred while generating EOD report. Please try again later.")
    
    def settings_command(self, update, context):
        """
        Handle /settings command
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        chat_id = update.effective_chat.id
        
        # Find user
        user = None
        for u in self.users['users']:
            if u['chat_id'] == chat_id:
                user = u
                break
        
        if user is None:
            update.message.reply_text("You are not registered. Please use /start to register.")
            return
        
        # Get settings
        settings = user.get('settings', {
            'price_alerts': True,
            'signal_alerts': True,
            'news_alerts': True,
            'eod_reports': True
        })
        
        # Format message
        message = "⚙️ Your Notification Settings ⚙️\n\n"
        message += f"Price Alerts: {'✅ ON' if settings.get('price_alerts', True) else '❌ OFF'}\n"
        message += f"Signal Alerts: {'✅ ON' if settings.get('signal_alerts', True) else '❌ OFF'}\n"
        message += f"News Alerts: {'✅ ON' if settings.get('news_alerts', True) else '❌ OFF'}\n"
        message += f"EOD Reports: {'✅ ON' if settings.get('eod_reports', True) else '❌ OFF'}\n\n"
        message += "To change settings, reply with:\n"
        message += "price on/off\n"
        message += "signal on/off\n"
        message += "news on/off\n"
        message += "eod on/off"
        
        update.message.reply_text(message)
        logger.info(f"Sent settings info to {chat_id}")
    
    def handle_message(self, update, context):
        """
        Handle text messages
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        chat_id = update.effective_chat.id
        text = update.message.text.lower()
        
        # Find user
        user = None
        for u in self.users['users']:
            if u['chat_id'] == chat_id:
                user = u
                break
        
        if user is None:
            update.message.reply_text("You are not registered. Please use /start to register.")
            return
        
        # Check if message is a settings command
        settings_changed = False
        
        if 'price' in text and ('on' in text or 'off' in text):
            user['settings']['price_alerts'] = 'on' in text
            settings_changed = True
        
        if 'signal' in text and ('on' in text or 'off' in text):
            user['settings']['signal_alerts'] = 'on' in text
            settings_changed = True
        
        if 'news' in text and ('on' in text or 'off' in text):
            user['settings']['news_alerts'] = 'on' in text
            settings_changed = True
        
        if 'eod' in text and ('on' in text or 'off' in text):
            user['settings']['eod_reports'] = 'on' in text
            settings_changed = True
        
        if settings_changed:
            self._save_users()
            update.message.reply_text("Settings updated! Use /settings to view your current settings.")
            logger.info(f"Updated settings for {chat_id}")
        else:
            # Default response
            update.message.reply_text("I don't understand that command. Use /help to see available commands.")
    
    def error_handler(self, update, context):
        """
        Handle errors
        
        Parameters:
        update: Telegram update object
        context: Telegram context object
        """
        logger.error(f"Update {update} caused error: {context.error}")
    
    def send_notification(self, notification):
        """
        Send notification to all registered users
        
        Parameters:
        notification (dict): Notification to send
        
        Returns:
        int: Number of users notified
        """
        if not notification:
            return 0
        
        count = 0
        
        for user in self.users['users']:
            chat_id = user['chat_id']
            settings = user.get('settings', {})
            
            # Check if user wants this type of notification
            if notification['type'] == 'price' and not settings.get('price_alerts', True):
                continue
            if notification['type'] == 'signal' and not settings.get('signal_alerts', True):
                continue
            if notification['type'] == 'news' and not settings.get('news_alerts', True):
                continue
            if notification['type'] == 'eod' and not settings.get('eod_reports', True):
                continue
            
            try:
                # Send message with chart if available
                if 'data' in notification and 'chart_path' in notification['data'] and os.path.exists(notification['data']['chart_path']):
                    with open(notification['data']['chart_path'], 'rb') as chart:
                        self.bot.send_photo(chat_id=chat_id, photo=chart, caption=notification['message'])
                else:
                    self.bot.send_message(chat_id=chat_id, text=notification['message'])
                
                count += 1
                logger.info(f"Sent {notification['type']} notification to {chat_id}")
                
            except Exception as e:
                logger.error(f"Error sending notification to {chat_id}: {e}")
        
        return count
    
    def run_monitoring_loop(self):
        """
        Run the monitoring loop
        """
        logger.info("Starting monitoring loop")
        
        # Start the bot
        self.updater.start_polling()
        
        try:
            # Initialize technical analysis
            ta = None
            
            # Track last EOD report time
            last_eod_report_date = None
            
            while True:
                try:
                    current_time = datetime.now()
                    
                    # Fetch live data
                    data = self.gold_monitor.fetch_live_data()
                    
                    if data is not None:
                        # Initialize or update technical analysis
                        if ta is None:
                            from technical_analysis import TechnicalAnalysis
                            ta = TechnicalAnalysis(data)
                        else:
                            ta.set_data(data)
                        
                        # Check for price movements
                        price_notification = self.notifier.check_price_movement(self.gold_monitor)
                        if price_notification:
                            self.notifier.add_notification(price_notification)
                            self.send_notification(price_notification)
                        
                        # Check for technical signals
                        signal_notification = self.notifier.check_technical_signals(ta)
                        if signal_notification:
                            self.notifier.add_notification(signal_notification)
                            self.send_notification(signal_notification)
                        
                        # Check for news
                        news_notifications = self.notifier.check_news(self.news_monitor)
                        for notification in news_notifications:
                            self.notifier.add_notification(notification)
                            self.send_notification(notification)
                        
                        # Check if it's time for EOD report
                        eod_time = EOD_REPORT_TIME.split(':')
                        eod_hour = int(eod_time[0])
                        eod_minute = int(eod_time[1]) if len(eod_time) > 1 else 0
                        
                        if (current_time.hour == eod_hour and current_time.minute >= eod_minute and 
                            (last_eod_report_date is None or current_time.date() > last_eod_report_date)):
                            
                            # Generate EOD report
                            eod_report = self.notifier.generate_eod_report(self.gold_monitor, ta, self.news_monitor)
                            if eod_report:
                                self.notifier.add_notification(eod_report)
                                self.send_notification(eod_report)
                                last_eod_report_date = current_time.date()
                    
                    # Update last check time
                    self.notifier.last_check_time = current_time
                    
                    # Log status
                    logger.info(f"Monitoring check completed at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                
                # Sleep until next check
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Monitoring loop stopped by user")
        finally:
            # Stop the bot
            self.updater.stop()
            logger.info("Bot stopped")

def main():
    """
    Main function
    """
    try:
        # Create directories
        os.makedirs('logs', exist_ok=True)
        
        # Check if token is provided
        token = TELEGRAM_BOT_TOKEN
        if not token:
            logger.error("Telegram Bot token not provided. Please set TELEGRAM_BOT_TOKEN environment variable.")
            sys.exit(1)
        
        # Create and run bot
        bot = TelegramBot(token=token)
        bot.run_monitoring_loop()
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
