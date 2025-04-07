import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/technical_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("technical_analysis")

class TechnicalAnalysis:
    """
    Class for performing technical analysis on XAU/USD (Gold) price data
    """
    
    def __init__(self, data=None):
        """
        Initialize the Technical Analysis
        
        Parameters:
        data (pandas.DataFrame): Price data (optional)
        """
        self.data = data
        
        # Create directories if they don't exist
        os.makedirs('charts', exist_ok=True)
        
        logger.info("Technical Analysis initialized")
    
    def set_data(self, data):
        """
        Set the price data
        
        Parameters:
        data (pandas.DataFrame): Price data
        """
        self.data = data
        logger.info(f"Data set with {len(data)} data points")
    
    def calculate_rsi(self, period=14):
        """
        Calculate Relative Strength Index (RSI)
        
        Parameters:
        period (int): RSI period (default: 14)
        
        Returns:
        pandas.Series: RSI values
        """
        if self.data is None or len(self.data) < period + 1:
            logger.error("Insufficient data to calculate RSI")
            return None
            
        try:
            # Calculate price changes
            delta = self.data['Close'].diff()
            
            # Separate gains and losses
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # Calculate average gain and loss
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # Calculate RS
            rs = avg_gain / avg_loss
            
            # Calculate RSI
            rsi = 100 - (100 / (1 + rs))
            
            logger.info(f"RSI calculated with period={period}")
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        """
        Calculate Moving Average Convergence Divergence (MACD)
        
        Parameters:
        fast_period (int): Fast EMA period (default: 12)
        slow_period (int): Slow EMA period (default: 26)
        signal_period (int): Signal EMA period (default: 9)
        
        Returns:
        tuple: (macd_line, signal_line, histogram)
        """
        if self.data is None or len(self.data) < slow_period + signal_period:
            logger.error("Insufficient data to calculate MACD")
            return None, None, None
            
        try:
            # Calculate EMAs
            fast_ema = self.data['Close'].ewm(span=fast_period, adjust=False).mean()
            slow_ema = self.data['Close'].ewm(span=slow_period, adjust=False).mean()
            
            # Calculate MACD line
            macd_line = fast_ema - slow_ema
            
            # Calculate signal line
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            logger.info(f"MACD calculated with fast_period={fast_period}, slow_period={slow_period}, signal_period={signal_period}")
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return None, None, None
    
    def calculate_moving_averages(self, periods=[20, 50, 200]):
        """
        Calculate Moving Averages
        
        Parameters:
        periods (list): List of periods for moving averages (default: [20, 50, 200])
        
        Returns:
        dict: Dictionary of moving averages
        """
        if self.data is None or len(self.data) < max(periods):
            logger.error("Insufficient data to calculate Moving Averages")
            return None
            
        try:
            ma_dict = {}
            
            for period in periods:
                ma = self.data['Close'].rolling(window=period).mean()
                ma_dict[f'MA{period}'] = ma
                
            logger.info(f"Moving Averages calculated for periods {periods}")
            
            return ma_dict
            
        except Exception as e:
            logger.error(f"Error calculating Moving Averages: {e}")
            return None
    
    def identify_support_resistance(self, window=10):
        """
        Identify support and resistance levels
        
        Parameters:
        window (int): Window size for local minima/maxima (default: 10)
        
        Returns:
        tuple: (support_levels, resistance_levels)
        """
        if self.data is None or len(self.data) < window * 2:
            logger.error("Insufficient data to identify support/resistance levels")
            return None, None
            
        try:
            # Get high and low prices
            highs = self.data['High'].values
            lows = self.data['Low'].values
            
            # Find local minima (support)
            support_indices = []
            for i in range(window, len(lows) - window):
                if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                    support_indices.append(i)
            
            # Find local maxima (resistance)
            resistance_indices = []
            for i in range(window, len(highs) - window):
                if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                    resistance_indices.append(i)
            
            # Get support and resistance levels
            support_levels = [float(lows[i]) for i in support_indices]
            resistance_levels = [float(highs[i]) for i in resistance_indices]
            
            logger.info(f"Identified {len(support_levels)} support levels and {len(resistance_levels)} resistance levels")
            
            return support_levels, resistance_levels
            
        except Exception as e:
            logger.error(f"Error identifying support/resistance levels: {e}")
            return None, None
    
    def generate_signals(self):
        """
        Generate trading signals based on technical indicators
        
        Returns:
        pandas.DataFrame: DataFrame with signals
        """
        if self.data is None:
            logger.error("No data available for signal generation")
            return None
            
        try:
            # Calculate indicators
            rsi = self.calculate_rsi()
            macd_line, signal_line, histogram = self.calculate_macd()
            ma_dict = self.calculate_moving_averages()
            
            if rsi is None or macd_line is None or ma_dict is None:
                logger.error("Failed to calculate indicators for signal generation")
                return None
                
            # Create signals DataFrame
            signals = pd.DataFrame(index=self.data.index)
            signals['Close'] = self.data['Close']
            signals['RSI'] = rsi
            signals['MACD'] = macd_line
            signals['MACD_Signal'] = signal_line
            signals['MACD_Histogram'] = histogram
            
            for ma_name, ma_values in ma_dict.items():
                signals[ma_name] = ma_values
            
            # Generate signal based on RSI
            signals['RSI_Signal'] = 0
            signals.loc[signals['RSI'] < 30, 'RSI_Signal'] = 1  # Oversold (buy)
            signals.loc[signals['RSI'] > 70, 'RSI_Signal'] = -1  # Overbought (sell)
            
            # Generate signal based on MACD
            signals['MACD_Cross_Signal'] = 0
            signals.loc[signals['MACD'] > signals['MACD_Signal'], 'MACD_Cross_Signal'] = 1  # Bullish
            signals.loc[signals['MACD'] < signals['MACD_Signal'], 'MACD_Cross_Signal'] = -1  # Bearish
            
            # Generate signal based on Moving Average crossovers
            if 'MA20' in signals.columns and 'MA50' in signals.columns:
                signals['MA_Cross_Signal'] = 0
                signals.loc[signals['MA20'] > signals['MA50'], 'MA_Cross_Signal'] = 1  # Bullish
                signals.loc[signals['MA20'] < signals['MA50'], 'MA_Cross_Signal'] = -1  # Bearish
            
            # Combine signals (simple average)
            signals['Signal'] = 0
            if 'RSI_Signal' in signals.columns:
                signals['Signal'] += signals['RSI_Signal']
            if 'MACD_Cross_Signal' in signals.columns:
                signals['Signal'] += signals['MACD_Cross_Signal']
            if 'MA_Cross_Signal' in signals.columns:
                signals['Signal'] += signals['MA_Cross_Signal']
            
            # Normalize signal (-1 to 1)
            num_indicators = sum(1 for col in ['RSI_Signal', 'MACD_Cross_Signal', 'MA_Cross_Signal'] if col in signals.columns)
            if num_indicators > 0:
                signals['Signal'] = signals['Signal'] / num_indicators
            
            logger.info("Trading signals generated")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return None

    def plot_indicators(self, signals=None, save_path=None):
        """
        Plot technical indicators
        
        Parameters:
        signals (pandas.DataFrame): Signals DataFrame (optional)
        save_path (str): Path to save the chart (optional)
        
        Returns:
        str: Path to saved chart if save_path is provided, None otherwise
        """
        if self.data is None:
            logger.error("No data available for plotting")
            return None
            
        if signals is None:
            signals = self.generate_signals()
            
        if signals is None:
            logger.error("Failed to generate signals for plotting")
            return None
            
        try:
            # Create figure and subplots
            fig, axs = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # Plot price and MAs
            axs[0].plot(signals.index, signals['Close'], label='Close Price', color='black')
            
            for ma_name in [col for col in signals.columns if col.startswith('MA')]:
                if not ma_name.endswith('Signal'):
                    axs[0].plot(signals.index, signals[ma_name], label=ma_name)
            
            # Add support and resistance levels
            support_levels, resistance_levels = self.identify_support_resistance()
            if support_levels and resistance_levels:
                for level in support_levels:
                    axs[0].axhline(y=level, color='green', linestyle='--', alpha=0.5)
                for level in resistance_levels:
                    axs[0].axhline(y=level, color='red', linestyle='--', alpha=0.5)
            
            # Plot MACD
            axs[1].plot(signals.index, signals['MACD'], label='MACD', color='blue')
            axs[1].plot(signals.index, signals['MACD_Signal'], label='Signal Line', color='red')
            axs[1].bar(signals.index, signals['MACD_Histogram'], label='Histogram', color='gray', alpha=0.5)
            axs[1].axhline(y=0, color='black', linestyle='-', alpha=0.2)
            
            # Plot RSI
            axs[2].plot(signals.index, signals['RSI'], label='RSI', color='purple')
            axs[2].axhline(y=70, color='red', linestyle='--', alpha=0.5)
            axs[2].axhline(y=30, color='green', linestyle='--', alpha=0.5)
            axs[2].axhline(y=50, color='black', linestyle='-', alpha=0.2)
            axs[2].set_ylim(0, 100)
            
            # Add titles and labels
            current_price = float(signals['Close'].iloc[-1])
            current_signal = float(signals['Signal'].iloc[-1])
            signal_type = "BUY" if current_signal > 0.2 else "SELL" if current_signal < -0.2 else "NEUTRAL"
            signal_color = "green" if current_signal > 0.2 else "red" if current_signal < -0.2 else "gray"
            
            fig.suptitle(f"XAU/USD Technical Analysis\nPrice: ${current_price:.2f} | Signal: {signal_type}", 
                        fontsize=16, color=signal_color)
            
            axs[0].set_title("Price Chart with Moving Averages")
            axs[1].set_title("MACD (12, 26, 9)")
            axs[2].set_title("RSI (14)")
            
            axs[0].set_ylabel("Price (USD)")
            axs[1].set_ylabel("MACD")
            axs[2].set_ylabel("RSI")
            
            axs[2].set_xlabel("Date")
            
            # Add grids
            for ax in axs:
                ax.grid(True, alpha=0.3)
            
            # Add legends
            for ax in axs:
                ax.legend()
            
            # Rotate x-axis labels for better readability
            for ax in axs:
                plt.setp(ax.get_xticklabels(), rotation=45)
            
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
            logger.error(f"Error plotting indicators: {e}")
            return None
    
    def get_signal_summary(self, signals=None):
        """
        Get a summary of the current trading signal
        
        Parameters:
        signals (pandas.DataFrame): Signals DataFrame (optional)
        
        Returns:
        dict: Signal summary
        """
        if self.data is None:
            logger.error("No data available for signal summary")
            return None
            
        if signals is None:
            signals = self.generate_signals()
            
        if signals is None or signals.empty:
            logger.error("Failed to generate signals for summary")
            return None
            
        try:
            # Get latest values
            latest = signals.iloc[-1]
            
            # Determine signal type
            signal_value = float(latest['Signal'])
            if signal_value > 0.2:
                signal_type = "BUY"
            elif signal_value < -0.2:
                signal_type = "SELL"
            else:
                signal_type = "NEUTRAL"
            
            # Create summary
            summary = {
                'timestamp': signals.index[-1],
                'price': float(latest['Close']),
                'signal_type': signal_type,
                'signal_strength': abs(signal_value),
                'rsi': float(latest['RSI']),
                'macd': float(latest['MACD']),
                'macd_signal': float(latest['MACD_Signal']),
                'macd_histogram': float(latest['MACD_Histogram'])
            }
            
            # Add moving averages
            for ma_name in [col for col in signals.columns if col.startswith('MA') and not col.endswith('Signal')]:
                summary[ma_name.lower()] = float(latest[ma_name])
            
            # Add support and resistance levels
            support_levels, resistance_levels = self.identify_support_resistance()
            if support_levels and resistance_levels:
                # Find closest support and resistance
                current_price = float(latest['Close'])
                
                # Filter levels below and above current price
                supports_below = [level for level in support_levels if level < current_price]
                resistances_above = [level for level in resistance_levels if level > current_price]
                
                # Get closest levels
                closest_support = max(supports_below) if supports_below else None
                closest_resistance = min(resistances_above) if resistances_above else None
                
                summary['support_levels'] = support_levels
                summary['resistance_levels'] = resistance_levels
                summary['closest_support'] = closest_support
                summary['closest_resistance'] = closest_resistance
            
            logger.info(f"Signal summary generated: {signal_type} with strength {abs(signal_value):.2f}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating signal summary: {e}")
            return None

# Example usage
if __name__ == "__main__":
    import gold_price_monitor
    
    # Create Gold Price Monitor
    monitor = gold_price_monitor.GoldPriceMonitor(interval='5m', period='1d')
    
    # Fetch live data
    data = monitor.fetch_live_data()
    
    if data is not None:
        # Create Technical Analysis
        ta = TechnicalAnalysis(data)
        
        # Generate signals
        signals = ta.generate_signals()
        
        if signals is not None:
            # Get signal summary
            summary = ta.get_signal_summary(signals)
            
            if summary is not None:
                print(f"Signal: {summary['signal_type']} (Strength: {summary['signal_strength']:.2f})")
                print(f"RSI: {summary['rsi']:.2f}")
                print(f"MACD: {summary['macd']:.2f}")
                print(f"MACD Signal: {summary['macd_signal']:.2f}")
                print(f"MACD Histogram: {summary['macd_histogram']:.2f}")
                
                if 'closest_support' in summary and summary['closest_support'] is not None:
                    print(f"Closest Support: ${summary['closest_support']:.2f}")
                if 'closest_resistance' in summary and summary['closest_resistance'] is not None:
                    print(f"Closest Resistance: ${summary['closest_resistance']:.2f}")
            
            # Plot indicators
            chart_path = ta.plot_indicators(signals, save_path="charts/technical_analysis.png")
            if chart_path:
                print(f"Chart saved to {chart_path}")
