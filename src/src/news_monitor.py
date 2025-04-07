import os
import re
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/news_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("news_monitor")

class NewsMonitor:
    """
    Class for monitoring gold-related news
    """
    
    def __init__(self):
        """
        Initialize the News Monitor
        """
        self.sources = [
            {
                'name': 'Investing.com',
                'url': 'https://www.investing.com/commodities/gold-news',
                'article_selector': '.articleItem',
                'title_selector': '.title',
                'date_selector': '.date',
                'link_selector': '.title a'
            },
            {
                'name': 'Kitco',
                'url': 'https://www.kitco.com/news/gold/',
                'article_selector': '.article',
                'title_selector': 'h3',
                'date_selector': '.date',
                'link_selector': 'a'
            },
            {
                'name': 'Reuters',
                'url': 'https://www.reuters.com/markets/commodities/',
                'article_selector': '.media-story',
                'title_selector': '.media-story-title',
                'date_selector': '.story-time',
                'link_selector': 'a'
            },
            {
                'name': 'MarketWatch',
                'url': 'https://www.marketwatch.com/investing/future/gc00',
                'article_selector': '.article__content',
                'title_selector': '.article__headline',
                'date_selector': '.article__timestamp',
                'link_selector': 'a'
            }
        ]
        
        self.news_data = pd.DataFrame(columns=['title', 'source', 'date', 'url', 'impact']) 
        self.last_fetch_time = None
        
        # Create directories if they don't exist
        os.makedirs('data', exist_ok=True)
        
        logger.info("News Monitor initialized")
    
    def fetch_news_from_source(self, source):
        """
        Fetch news from a specific source
        
        Parameters:
        source (dict): Source configuration
        
        Returns:
        list: List of news articles
        """
        articles = []
        
        try:
            logger.info(f"Fetching news from {source['name']}")
            
            # Set headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Fetch the page
            response = requests.get(source['url'], headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all articles
            article_elements = soup.select(source['article_selector'])
            
            if not article_elements:
                logger.warning(f"No articles found on {source['name']}, trying alternative selectors")
                # Try alternative selectors based on the source
                if source['name'] == 'Investing.com':
                    article_elements = soup.select('.largeTitle')
                elif source['name'] == 'Kitco':
                    article_elements = soup.select('.news-item')
                elif source['name'] == 'Reuters':
                    article_elements = soup.select('.story')
                elif source['name'] == 'MarketWatch':
                    article_elements = soup.select('.element--article')
            
            logger.info(f"Found {len(article_elements)} articles on {source['name']}")
            
            # Process each article
            for article in article_elements[:10]:  # Limit to 10 articles per source
                try:
                    # Extract title
                    title_element = article.select_one(source['title_selector'])
                    if title_element:
                        title = title_element.text.strip()
                    else:
                        continue
                    
                    # Extract date
                    date_element = article.select_one(source['date_selector'])
                    if date_element:
                        date_str = date_element.text.strip()
                        # Parse date (this is simplified and may need adjustment for each source)
                        date = self._parse_date(date_str)
                    else:
                        date = datetime.now()
                    
                    # Extract link
                    link_element = article.select_one(source['link_selector'])
                    if link_element and 'href' in link_element.attrs:
                        url = link_element['href']
                        # Handle relative URLs
                        if not url.startswith('http') :
                            if url.startswith('/'):
                                base_url = '/'.join(source['url'].split('/')[:3])
                                url = base_url + url
                            else:
                                url = source['url'] + '/' + url
                    else:
                        continue
                    
                    # Calculate impact score (simplified)
                    impact = self._calculate_impact(title)
                    
                    # Add to articles list
                    articles.append({
                        'title': title,
                        'source': source['name'],
                        'date': date,
                        'url': url,
                        'impact': impact
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing article from {source['name']}: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news from {source['name']}: {e}")
            return []
    
    def _parse_date(self, date_str):
        """
        Parse date string to datetime
        
        Parameters:
        date_str (str): Date string
        
        Returns:
        datetime: Parsed date
        """
        try:
            # Try common date formats
            now = datetime.now()
            
            # Check for "X minutes/hours ago" format
            if 'ago' in date_str.lower():
                if 'minute' in date_str.lower():
                    minutes = int(re.search(r'(\d+)', date_str).group(1))
                    return now - timedelta(minutes=minutes)
                elif 'hour' in date_str.lower():
                    hours = int(re.search(r'(\d+)', date_str).group(1))
                    return now - timedelta(hours=hours)
                elif 'day' in date_str.lower():
                    days = int(re.search(r'(\d+)', date_str).group(1))
                    return now - timedelta(days=days)
                else:
                    return now
            
            # Try specific formats
            for fmt in ['%b %d, %Y', '%Y-%m-%d', '%d %b %Y', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If all else fails, return current time
            return now
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return datetime.now()
    
    def _calculate_impact(self, title):
        """
        Calculate the potential impact of a news article on gold prices
        
        Parameters:
        title (str): Article title
        
        Returns:
        float: Impact score (0.0 to 1.0)
        """
        # Keywords that might indicate high impact
        high_impact_keywords = [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'cpi', 'ppi',
            'powell', 'yellen', 'treasury', 'dollar', 'usd', 'recession',
            'war', 'conflict', 'crisis', 'surge', 'plunge', 'crash',
            'rally', 'soar', 'jump', 'spike', 'tumble', 'slump'
        ]
        
        # Keywords specifically related to gold
        gold_keywords = [
            'gold', 'xau', 'bullion', 'precious metal', 'safe haven',
            'ounce', 'troy', 'spot gold', 'gold futures', 'gold price'
        ]
        
        title_lower = title.lower()
        
        # Check if the article is about gold
        is_gold_related = any(keyword in title_lower for keyword in gold_keywords)
        
        # If not gold-related, lower the impact
        if not is_gold_related:
            return 0.3
        
        # Count high impact keywords
        impact_count = sum(1 for keyword in high_impact_keywords if keyword in title_lower)
        
        # Calculate impact score (0.5 to 1.0 for gold-related news)
        impact = 0.5 + min(0.5, impact_count * 0.1)
        
        return impact
    
    def fetch_all_news(self):
        """
        Fetch news from all sources
        
        Returns:
        pandas.DataFrame: News data
        """
        all_articles = []
        
        for source in self.sources:
            articles = self.fetch_news_from_source(source)
            all_articles.extend(articles)
        
        if not all_articles:
            logger.warning("No news found from any source, generating sample news for testing")
            all_articles = self._generate_sample_news()
        
        # Convert to DataFrame
        news_df = pd.DataFrame(all_articles)
        
        # Sort by date (newest first)
        if not news_df.empty and 'date' in news_df.columns:
            news_df = news_df.sort_values('date', ascending=False)
        
        # Update news data
        self.news_data = news_df
        self.last_fetch_time = datetime.now()
        
        # Save to CSV
        if not news_df.empty:
            news_df.to_csv(f"data/gold_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
        
        logger.info(f"Fetched {len(news_df)} news articles")
        
        return news_df
    
    def _generate_sample_news(self):
        """
        Generate sample news for testing
        
        Returns:
        list: List of sample news articles
        """
        sample_titles = [
            "Gold Prices Surge as Inflation Fears Mount",
            "Federal Reserve Decision Sends Gold to New Highs",
            "Gold Retreats as Dollar Strengthens",
            "Analysts Predict Gold to Reach $2,500 by Year End",
            "Central Banks Increase Gold Reserves Amid Economic Uncertainty",
            "Gold Mining Stocks Rally on Production Reports",
            "Safe Haven Demand Boosts Gold Amid Geopolitical Tensions",
            "Gold Faces Resistance at Key Technical Level",
            "Investors Turn to Gold as Hedge Against Inflation",
            "Gold/Silver Ratio Suggests Potential Price Movement"
        ]
        
        sample_sources = ['Investing.com', 'Kitco', 'Reuters', 'MarketWatch']
        
        now = datetime.now()
        
        sample_articles = []
        
        for i, title in enumerate(sample_titles):
            # Generate random date within the last 24 hours
            hours_ago = random.randint(0, 24)
            date = now - timedelta(hours=hours_ago)
            
            # Select random source
            source = random.choice(sample_sources)
            
            # Calculate impact
            impact = self._calculate_impact(title)
            
            # Generate sample URL
            url = f"https://example.com/gold-news/{i}"
            
            # Add to sample articles
            sample_articles.append({
                'title': title,
                'source': source,
                'date': date,
                'url': url,
                'impact': impact
            }) 
        
        return sample_articles
    
    def get_high_impact_news(self, threshold=0.7):
        """
        Get high impact news
        
        Parameters:
        threshold (float): Impact threshold (default: 0.7)
        
        Returns:
        pandas.DataFrame: High impact news
        """
        if self.news_data.empty:
            self.fetch_all_news()
            
        if self.news_data.empty:
            logger.error("No news data available")
            return pd.DataFrame()
            
        # Filter by impact
        high_impact = self.news_data[self.news_data['impact'] >= threshold]
        
        logger.info(f"Found {len(high_impact)} high impact news articles")
        
        return high_impact
    
    def get_latest_news(self, limit=5):
        """
        Get latest news
        
        Parameters:
        limit (int): Number of news articles to return (default: 5)
        
        Returns:
        pandas.DataFrame: Latest news
        """
        if self.news_data.empty:
            self.fetch_all_news()
            
        if self.news_data.empty:
            logger.error("No news data available")
            return pd.DataFrame()
            
        # Get latest news
        latest = self.news_data.head(limit)
        
        logger.info(f"Returning {len(latest)} latest news articles")
        
        return latest
    
    def analyze_news_sentiment(self):
        """
        Analyze news sentiment (simplified)
        
        Returns:
        dict: Sentiment analysis
        """
        if self.news_data.empty:
            self.fetch_all_news()
            
        if self.news_data.empty:
            logger.error("No news data available for sentiment analysis")
            return None
            
        # Positive and negative keywords
        positive_keywords = [
            'rally', 'soar', 'jump', 'spike', 'surge', 'gain', 'rise', 'climb',
            'bullish', 'uptrend', 'support', 'positive', 'optimistic'
        ]
        
        negative_keywords = [
            'plunge', 'crash', 'tumble', 'slump', 'drop', 'fall', 'decline', 'sink',
            'bearish', 'downtrend', 'resistance', 'negative', 'pessimistic'
        ]
        
        # Count sentiment keywords
        positive_count = 0
        negative_count = 0
        
        for title in self.news_data['title']:
            title_lower = title.lower()
            positive_count += sum(1 for keyword in positive_keywords if keyword in title_lower)
            negative_count += sum(1 for keyword in negative_keywords if keyword in title_lower)
        
        # Calculate sentiment score (-1.0 to 1.0)
        total_count = positive_count + negative_count
        if total_count > 0:
            sentiment_score = (positive_count - negative_count) / total_count
        else:
            sentiment_score = 0.0
        
        # Determine sentiment
        if sentiment_score > 0.2:
            sentiment = "Bullish"
        elif sentiment_score < -0.2:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"
        
        # Create sentiment analysis
        analysis = {
            'sentiment': sentiment,
            'score': sentiment_score,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'total_articles': len(self.news_data)
        }
        
        logger.info(f"News sentiment analysis: {sentiment} (Score: {sentiment_score:.2f})")
        
        return analysis

# Example usage
if __name__ == "__main__":
    # Create News Monitor
    monitor = NewsMonitor()
    
    # Fetch all news
    news = monitor.fetch_all_news()
    
    if not news.empty:
        # Print latest news
        print("Latest Gold News:")
        for i, (_, article) in enumerate(news.head(5).iterrows()):
            print(f"{i+1}. {article['title']} ({article['source']}, {article['date'].strftime('%Y-%m-%d %H:%M')})")
            print(f"   Impact: {article['impact']:.2f}, URL: {article['url']}")
            print()
        
        # Get high impact news
        high_impact = monitor.get_high_impact_news(threshold=0.7)
        if not high_impact.empty:
            print("\nHigh Impact News:")
            for i, (_, article) in enumerate(high_impact.iterrows()):
                print(f"{i+1}. {article['title']} ({article['source']}, {article['date'].strftime('%Y-%m-%d %H:%M')})")
                print(f"   Impact: {article['impact']:.2f}")
                print()
        
        # Analyze sentiment
        sentiment = monitor.analyze_news_sentiment()
        if sentiment:
            print(f"\nNews Sentiment: {sentiment['sentiment']} (Score: {sentiment['score']:.2f})")
            print(f"Positive mentions: {sentiment['positive_count']}, Negative mentions: {sentiment['negative_count']}")
