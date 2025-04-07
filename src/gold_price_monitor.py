import os
import logging
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/gold_price_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gold_price_monitor")

class GoldPriceMonitor:
    """
    Class for monitoring XAU/USD (Gold) prices
    """
    
    def __init__(self, interval='5m', period='1d'):
        """
        Initialize the Gold Price Monitor
        
        Parameters:
        interval (str): Data interval (default: '5m' = 5 minutes)
        period (str): Data period (default: '1d' = 1 day)
        """
        self.interval = interval
        self.period = period
        self.data = None
        self.current_price = None
        
        # Create directories if they don't exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('charts', exist_ok=True)
        
        logger.info(f"Gold Price Monitor initialized with interval={interval}, period={period}")
    
    def fetch_live_data(self, interval=None, period=None):
        """
        Fetch live XAU/USD price data
        
        Parameters:
        interval (str): Data interval (optional, overrides default)
        period (str): Data period (optional, overrides default)
        
        Returns:
        pandas.DataFrame: Price data
        """
        if interval is None:
            interval = self.interval
        if period is None:
            period = self.period
            
        try:
            logger.info(f"Fetching XAU/USD data with interval={interval}, period={period}")
            
            # Fetch data from Yahoo Finance
            data = yf.download("GC=F", interval=interval, period=period, progress=False)
            
            if data.empty:
                logger.error("Failed to fetch data: Empty dataframe returned")
                return None
                
            # Store data
            self.data = data
            
            # Update current price
            self.current_price = float(data['Close'].iloc[-1])
            
            logger.info(f"Fetched {len(data)} data points, current price: ${self.current_price:.2f}")
            
            # Save data to CSV
            data.to_csv(f"data/gold_price_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def get_current_price(self):
        """
        Get the current XAU/USD price
        
        Returns:
        float: Current price
        """
        if self.current_price is None:
            if self.data is None:
                self.fetch_live_data()
            if self.data is not None:
                self.current_price = float(self.data['Close'].iloc[-1])
                
        return self.current_price
    
    def get_price_change(self, period='1d'):
        """
        Get price change over a period
        
        Parameters:
        period (str): Period for change calculation (default: '1d' = 1 day)
        
        Returns:
        tuple: (change, percent_change)
        """
        if self.data is None:
            self.fetch_live_data(period=period)
            
        if self.data is None or len(self.data) < 2:
            logger.error("Insufficient data to calculate price change")
            return None, None
            
        current_price = float(self.data['Close'].iloc[-1])
        open_price = float(self.data['Open'].iloc[0])
        
        change = current_price - open_price
        percent_change = (change / open_price) * 100
        
        logger.info(f"Price change over {period}: ${change:.2f} ({percent_change:.2f}%)")
        
        return change, percent_change
    
    def plot_price_chart(self, save_path=None):
        """
        Plot XAU/USD price chart
        
        Parameters:
        save_path (str): Path to save the chart (optional)
        
        Returns:
        str: Path to saved chart if save_path is provided, None otherwise
        """
        if self.data is None:
            self.fetch_live_data()
            
        if self.data is None:
            logger.error("No data available for plotting")
            return None
            
        try:
            # Create figure and axis
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot close price
            ax.plot(self.data.index, self.data['Close'], label='Close Price', color='gold')
            
            # Add title and labels
            current_price = self.get_current_price()
            change, percent_change = self.get_price_change()
            
            title = f"XAU/USD Price Chart\nCurrent: ${current_price:.2f}"
            if change is not None and percent_change is not None:
                title += f" | Change: ${change:.2f} ({percent_change:.2f}%)"
                
            ax.set_title(title)
            ax.set_xlabel('Time')
            ax.set_ylabel('Price (USD)')
            
            # Add grid
            ax.grid(True, alpha=0.3)
            
            # Add legend
            ax.legend()
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save chart if save_path is provided
            if save_path:
                if not os.path.exists(os.path.dirname(save_path)):
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                plt.savefig(save_path)
                logger.info(f"Chart saved to {save_path}")
                plt.close(fig)
                return save_path
                
            return None
            
        except Exception as e:
            logger.error(f"Error plotting chart: {e}")
            return None
    
    def get_price_range(self):
        """
        Get price range (high/low) for the current data
        
        Returns:
        tuple: (low, high)
        """
        if self.data is None:
            self.fetch_live_data()
            
        if self.data is None:
            logger.error("No data available for price range calculation")
            return None, None
            
        low = float(self.data['Low'].min())
        high = float(self.data['High'].max())
        
        logger.info(f"Price range: ${low:.2f} - ${high:.2f}")
        
        return low, high
    
    def get_historical_data(self, days=30):
        """
        Get historical data for a longer period
        
        Parameters:
        days (int): Number of days of historical data (default: 30)
        
        Returns:
        pandas.DataFrame: Historical price data
        """
        try:
            logger.info(f"Fetching {days} days of historical XAU/USD data")
            
            # Fetch data from Yahoo Finance
            data = yf.download("GC=F", period=f"{days}d", interval="1d", progress=False)
            
            if data.empty:
                logger.error("Failed to fetch historical data: Empty dataframe returned")
                return None
                
            logger.info(f"Fetched {len(data)} days of historical data")
            
            # Save data to CSV
            data.to_csv(f"data/gold_historical_{days}d_{datetime.now().strftime('%Y%m%d')}.csv")
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Create Gold Price Monitor
    monitor = GoldPriceMonitor(interval='5m', period='1d')
    
    # Fetch live data
    data = monitor.fetch_live_data()
    
    if data is not None:
        # Get current price
        current_price = monitor.get_current_price()
        print(f"Current XAU/USD Price: ${current_price:.2f}")
        
        # Get price change
        change, percent_change = monitor.get_price_change()
        if change is not None and percent_change is not None:
            print(f"Price Change: ${change:.2f} ({percent_change:.2f}%)")
            
        # Get price range
        low, high = monitor.get_price_range()
        if low is not None and high is not None:
            print(f"Price Range: ${low:.2f} - ${high:.2f}")
            
        # Plot price chart
        chart_path = monitor.plot_price_chart(save_path="charts/gold_price_chart.png")
        if chart_path:
            print(f"Chart saved to {chart_path}")
