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
