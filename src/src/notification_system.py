import os
import logging
import pandas as pd
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/notification_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("notification_system")

class NotificationSystem:
    """
    Class for generating notifications based on price movements, technical signals, and news
    """
    
    def __init__(self, check_interval=900, price_change_threshold=0.5, rsi_overbought=70, rsi_oversold=30):
        """
        Initialize the Notification System
        
        Parameters:
        check_interval (int): Interval between checks in seconds (default: 900 = 15 minutes)
        price_change_threshold (float): Percentage change to trigger price alert (default: 0.5%)
        rsi_overbought (int): RSI level considered overbought (default: 70)
        rsi_oversold (int): RSI level considered oversold (default: 30)
        """
        self.check_interval = check_interval
        self.price_change_threshold = price_change_threshold
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        self.last_price = None
        self.last_signal = None
        self.last_news_ids = set()
        self.last_check_time = None
        self.notifications_history = []
        
        # Create directories if they don't exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Load notification history if exists
        self._load_notification_history()
        
        logger.info(f"Notification System initialized with check_interval={check_interval}s, "
                   f"price_change_threshold={price_change_threshold}%, "
                   f"rsi_overbought={rsi_overbought}, rsi_oversold={rsi_oversold}")
    
    def _load_notification_history(self):
        """
        Load notification history from file
        """
        history_file = "data/notification_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    self.notifications_history = json.load(f)
                logger.info(f"Loaded {len(self.notifications_history)} notifications from history")
            except Exception as e:
                logger.error(f"Error loading notification history: {e}")
                self.notifications_history = []
    
    def _save_notification_history(self):
        """
        Save notification history to file
        """
        history_file = "data/notification_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self.notifications_history[-100:], f)  # Keep only last 100 notifications
            logger.info(f"Saved {len(self.notifications_history[-100:])} notifications to history")
        except Exception as e:
            logger.error(f"Error saving notification history: {e}")
    
    def check_price_movement(self, gold_monitor):
        """
        Check for significant price movements
        
        Parameters:
        gold_monitor: GoldPriceMonitor instance
        
        Returns:
        dict or None: Notification if significant movement detected, None otherwise
        """
        current_price = gold_monitor.get_current_price()
        
        if current_price is None:
            logger.error("Failed to get current price")
            return None
        
        # If this is the first check, just store the price
        if self.last_price is None:
            self.last_price = current_price
            logger.info(f"Initial price check: ${current_price:.2f}")
            return None
        
        # Calculate price change
        price_change = current_price - self.last_price
        percent_change = (price_change / self.last_price) * 100
        
        # Check if change exceeds threshold
        if abs(percent_change) >= self.price_change_threshold:
            direction = "up" if price_change > 0 else "down"
            logger.info(f"Significant price movement detected: ${price_change:.2f} ({percent_change:.2f}%)")
            
            # Create notification
            notification = {
                'type': 'price',
                'timestamp': datetime.now().isoformat(),
                'title': f"Gold Price {direction.capitalize()}",
                'message': f"Gold price moved {direction} by ${abs(price_change):.2f} ({abs(percent_change):.2f}%)\n"
                          f"Current price: ${current_price:.2f}\n"
                          f"Previous price: ${self.last_price:.2f}",
                'data': {
                    'current_price': current_price,
                    'previous_price': self.last_price,
                    'price_change': price_change,
                    'percent_change': percent_change
                }
            }
            
            # Generate chart
            chart_path = gold_monitor.plot_price_chart(save_path=f"charts/price_movement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            if chart_path:
                notification['data']['chart_path'] = chart_path
            
            # Update last price
            self.last_price = current_price
            
            return notification
        
        # Update last price
        self.last_price = current_price
        
        return None
    
    def check_technical_signals(self, technical_analysis):
        """
        Check for technical trading signals
        
        Parameters:
        technical_analysis: TechnicalAnalysis instance
        
        Returns:
        dict or None: Notification if new signal detected, None otherwise
        """
        # Generate signals
        signals = technical_analysis.generate_signals()
        
        if signals is None or signals.empty:
            logger.error("Failed to generate technical signals")
            return None
        
        # Get signal summary
        summary = technical_analysis.get_signal_summary(signals)
        
        if summary is None:
            logger.error("Failed to get signal summary")
            return None
        
        signal_type = summary['signal_type']
        signal_strength = summary['signal_strength']
        
        # If this is the first check, just store the signal
        if self.last_signal is None:
            self.last_signal = signal_type
            logger.info(f"Initial signal check: {signal_type} (Strength: {signal_strength:.2f})")
            return None
        
        # Check if signal changed
        if signal_type != self.last_signal and signal_type != "NEUTRAL":
            logger.info(f"New trading signal detected: {signal_type} (Strength: {signal_strength:.2f})")
            
            # Create notification
            notification = {
                'type': 'signal',
                'timestamp': datetime.now().isoformat(),
                'title': f"Gold Trading Signal: {signal_type}",
                'message': self._format_signal_message(summary),
                'data': summary
            }
            
            # Generate chart
            chart_path = technical_analysis.plot_indicators(signals, save_path=f"charts/signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            if chart_path:
                notification['data']['chart_path'] = chart_path
            
            # Update last signal
            self.last_signal = signal_type
            
            return notification
        
        # Update last signal
        self.last_signal = signal_type
        
        return None
    
    def _format_signal_message(self, summary):
        """
        Format signal message
        
        Parameters:
        summary (dict): Signal summary
        
        Returns:
        str: Formatted message
        """
        message = f"Trading Signal: {summary['signal_type']} (Strength: {summary['signal_strength']:.2f})\n\n"
        message += f"Current Price: ${summary['price']:.2f}\n"
        message += f"RSI: {summary['rsi']:.2f}"
        
        if summary['rsi'] > self.rsi_overbought:
            message += " (Overbought)\n"
        elif summary['rsi'] < self.rsi_oversold:
            message += " (Oversold)\n"
        else:
            message += " (Neutral)\n"
        
        message += f"MACD: {summary['macd']:.2f}\n"
        message += f"MACD Signal: {summary['macd_signal']:.2f}\n"
        
        if summary['macd'] > summary['macd_signal']:
            message += "MACD is bullish (MACD line above Signal line)\n"
        else:
            message += "MACD is bearish (MACD line below Signal line)\n"
        
        if 'closest_support' in summary and summary['closest_support'] is not None:
            message += f"\nClosest Support: ${summary['closest_support']:.2f}"
        
        if 'closest_resistance' in summary and summary['closest_resistance'] is not None:
            message += f"\nClosest Resistance: ${summary['closest_resistance']:.2f}"
        
        return message
    
    def check_news(self, news_monitor):
        """
        Check for important news
        
        Parameters:
        news_monitor: NewsMonitor instance
        
        Returns:
        list: List of notifications for new important news
        """
        # Fetch news
        news = news_monitor.fetch_all_news()
        
        if news is None or news.empty:
            logger.error("Failed to fetch news")
            return []
        
        # Get high impact news
        high_impact = news_monitor.get_high_impact_news(threshold=0.7)
        
        if high_impact is None or high_impact.empty:
            logger.info("No high impact news found")
            return []
        
        # Create a set of news IDs (title + source)
        current_news_ids = set()
        for _, article in high_impact.iterrows():
            news_id = f"{article['title']}|{article['source']}"
            current_news_ids.add(news_id)
        
        # If this is the first check, just store the news IDs
        if not self.last_news_ids:
            self.last_news_ids = current_news_ids
            logger.info(f"Initial news check: {len(current_news_ids)} high impact articles")
            return []
        
        # Find new news
        new_news_ids = current_news_ids - self.last_news_ids
        
        if not new_news_ids:
            logger.info("No new high impact news found")
            return []
        
        # Create notifications for new news
        notifications = []
        
        for _, article in high_impact.iterrows():
            news_id = f"{article['title']}|{article['source']}"
            
            if news_id in new_news_ids:
                logger.info(f"New high impact news detected: {article['title']} ({article['source']})")
                
                # Create notification
                notification = {
                    'type': 'news',
                    'timestamp': datetime.now().isoformat(),
                    'title': f"Gold News: {article['title']}",
                    'message': f"{article['title']}\n\n"
                              f"Source: {article['source']}\n"
                              f"Date: {article['date'].strftime('%Y-%m-%d %H:%M')}\n"
                              f"Impact: {article['impact']:.2f}\n\n"
                              f"URL: {article['url']}",
                    'data': {
                        'title': article['title'],
                        'source': article['source'],
                        'date': article['date'].isoformat(),
                        'impact': float(article['impact']),
                        'url': article['url']
                    }
                }
                
                notifications.append(notification)
        
        # Update last news IDs
        self.last_news_ids = current_news_ids
        
        return notifications
    
    def generate_eod_report(self, gold_monitor, technical_analysis, news_monitor):
        """
        Generate end-of-day report
        
        Parameters:
        gold_monitor: GoldPriceMonitor instance
        technical_analysis: TechnicalAnalysis instance
        news_monitor: NewsMonitor instance
        
        Returns:
        dict: EOD report notification
        """
        logger.info("Generating EOD report")
        
        # Get current price and daily change
        current_price = gold_monitor.get_current_price()
        change, percent_change = gold_monitor.get_price_change(period='1d')
        
        # Get technical signals
        signals = technical_analysis.generate_signals()
        summary = technical_analysis.get_signal_summary(signals) if signals is not None else None
        
        # Get news sentiment
        sentiment = news_monitor.analyze_news_sentiment()
        
        # Get latest news
        latest_news = news_monitor.get_latest_news(limit=5)
        
        # Create report
        report = {
            'type': 'eod',
            'timestamp': datetime.now().isoformat(),
            'title': "Gold Trading: End-of-Day Report",
            'message': self._format_eod_report(current_price, change, percent_change, summary, sentiment, latest_news),
            'data': {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'current_price': current_price,
                'price_change': change,
                'percent_change': percent_change,
                'signal': summary['signal_type'] if summary else None,
                'sentiment': sentiment['sentiment'] if sentiment else None
            }
        }
        
        # Generate price chart
        price_chart = gold_monitor.plot_price_chart(save_path=f"charts/eod_price_{datetime.now().strftime('%Y%m%d')}.png")
        if price_chart:
            report['data']['price_chart'] = price_chart
        
        # Generate technical chart
        if signals is not None:
            tech_chart = technical_analysis.plot_indicators(signals, save_path=f"charts/eod_technical_{datetime.now().strftime('%Y%m%d')}.png")
            if tech_chart:
                report['data']['technical_chart'] = tech_chart
        
        return report
    
    def _format_eod_report(self, current_price, change, percent_change, summary, sentiment, latest_news):
        """
        Format EOD report message
        
        Parameters:
        current_price (float): Current gold price
        change (float): Daily price change
        percent_change (float): Daily percent change
        summary (dict): Technical signal summary
        sentiment (dict): News sentiment analysis
        latest_news (pandas.DataFrame): Latest news
        
        Returns:
        str: Formatted message
        """
        # Format date
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Start with header
        message = f"🏆 GOLD TRADING: END-OF-DAY REPORT ({date}) 🏆\n\n"
        
        # Price section
        message += "💰 PRICE SUMMARY 💰\n"
        message += f"Current Price: ${current_price:.2f}\n"
        
        if change is not None and percent_change is not None:
            direction = "up" if change > 0 else "down"
            emoji = "📈" if change > 0 else "📉"
            message += f"Daily Change: {emoji} ${abs(change):.2f} ({abs(percent_change):.2f}%) {direction}\n\n"
        else:
            message += "\n"
        
        # Technical analysis section
        message += "📊 TECHNICAL ANALYSIS 📊\n"
        
        if summary:
            signal_emoji = "🟢" if summary['signal_type'] == "BUY" else "🔴" if summary['signal_type'] == "SELL" else "⚪"
            message += f"Signal: {signal_emoji} {summary['signal_type']} (Strength: {summary['signal_strength']:.2f})\n"
            message += f"RSI: {summary['rsi']:.2f}"
            
            if summary['rsi'] > self.rsi_overbought:
                message += " (Overbought)\n"
            elif summary['rsi'] < self.rsi_oversold:
                message += " (Oversold)\n"
            else:
                message += " (Neutral)\n"
            
            message += f"MACD: {summary['macd']:.2f} vs Signal: {summary['macd_signal']:.2f}\n"
            
            if 'closest_support' in summary and summary['closest_support'] is not None:
                message += f"Support: ${summary['closest_support']:.2f}\n"
            
            if 'closest_resistance' in summary and summary['closest_resistance'] is not None:
                message += f"Resistance: ${summary['closest_resistance']:.2f}\n"
        else:
            message += "No technical data available\n"
        
        message += "\n"
        
        # News section
        message += "📰 NEWS SUMMARY 📰\n"
        
        if sentiment:
            sentiment_emoji = "🟢" if sentiment['sentiment'] == "Bullish" else "🔴" if sentiment['sentiment'] == "Bearish" else "⚪"
            message += f"Sentiment: {sentiment_emoji} {sentiment['sentiment']} (Score: {sentiment['score']:.2f})\n"
            message += f"Articles: {sentiment['total_articles']} (Positive: {sentiment['positive_count']}, Negative: {sentiment['negative_count']})\n\n"
        else:
            message += "No sentiment data available\n\n"
        
        if not latest_news.empty:
            message += "Latest Headlines:\n"
            for i, (_, article) in enumerate(latest_news.iterrows()):
                if i < 5:  # Limit to 5 headlines
                    message += f"- {article['title']} ({article['source']})\n"
        else:
            message += "No recent news available\n"
        
        message += "\n"
        
        # Forecast section
        message += "🔮 NEXT DAY FORECAST 🔮\n"
        
        # Generate simple forecast based on technical and sentiment
        forecast = "Neutral"
        forecast_reason = []
        
        if summary:
            if summary['signal_type'] == "BUY":
                forecast = "Bullish"
                forecast_reason.append("Technical indicators suggest buying")
            elif summary['signal_type'] == "SELL":
                forecast = "Bearish"
                forecast_reason.append("Technical indicators suggest selling")
        
        if sentiment:
            if sentiment['sentiment'] == "Bullish":
                if forecast == "Bearish":
                    forecast = "Mixed"
                    forecast_reason.append("News sentiment is positive")
                else:
                    forecast = "Bullish"
                    forecast_reason.append("News sentiment is positive")
            elif sentiment['sentiment'] == "Bearish":
                if forecast == "Bullish":
                    forecast = "Mixed"
                    forecast_reason.append("News sentiment is negative")
                else:
                    forecast = "Bearish"
                    forecast_reason.append("News sentiment is negative")
        
        forecast_emoji = "🟢" if forecast == "Bullish" else "🔴" if forecast == "Bearish" else "⚪" if forecast == "Mixed" else "⚪"
        message += f"Forecast: {forecast_emoji} {forecast}\n"
        
        if forecast_reason:
            message += "Reasoning:\n"
            for reason in forecast_reason:
                message += f"- {reason}\n"
        
        return message
    
    def add_notification(self, notification):
        """
        Add notification to history
        
        Parameters:
        notification (dict): Notification to add
        
        Returns:
        bool: True if added successfully, False otherwise
        """
        if notification is None:
            return False
        
        try:
            # Add to history
            self.notifications_history.append(notification)
            
            # Save history
            self._save_notification_history()
            
            logger.info(f"Added notification: {notification['title']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding notification: {e}")
            return False
    
    def get_recent_notifications(self, limit=10):
        """
        Get recent notifications
        
        Parameters:
        limit (int): Number of notifications to return (default: 10)
        
        Returns:
        list: Recent notifications
        """
        return self.notifications_history[-limit:] if self.notifications_history else []

# Example usage
if __name__ == "__main__":
    import gold_price_monitor
    import technical_analysis
    import news_monitor
    
    # Create instances
    gm = gold_price_monitor.GoldPriceMonitor(interval='5m', period='1d')
    data = gm.fetch_live_data()
    
    if data is not None:
        ta = technical_analysis.TechnicalAnalysis(data)
        nm = news_monitor.NewsMonitor()
        
        # Create Notification System
        ns = NotificationSystem(check_interval=900, price_change_threshold=0.5)
        
        # Check for price movements
        price_notification = ns.check_price_movement(gm)
        if price_notification:
            print(f"Price Notification: {price_notification['title']}")
            print(price_notification['message'])
            print()
        
        # Check for technical signals
        signal_notification = ns.check_technical_signals(ta)
        if signal_notification:
            print(f"Signal Notification: {signal_notification['title']}")
            print(signal_notification['message'])
            print()
        
        # Check for news
        news_notifications = ns.check_news(nm)
        for notification in news_notifications:
            print(f"News Notification: {notification['title']}")
            print(notification['message'])
            print()
        
        # Generate EOD report
        eod_report = ns.generate_eod_report(gm, ta, nm)
        print(f"EOD Report: {eod_report['title']}")
        print(eod_report['message'])
