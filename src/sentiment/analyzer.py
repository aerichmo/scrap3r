import re
from typing import Dict, List, Tuple
from collections import Counter
import logging

from ..config import BULLISH_WORDS, BEARISH_WORDS


logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes market sentiment from text"""
    
    def __init__(self):
        self.ticker_pattern = re.compile(r'\b[A-Z]{2,5}\b')
        self.bullish_words = set(word.lower() for word in BULLISH_WORDS)
        self.bearish_words = set(word.lower() for word in BEARISH_WORDS)
        
    def analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of a single text"""
        text_lower = text.lower()
        
        # Count sentiment words
        bullish_count = sum(1 for word in self.bullish_words if word in text_lower)
        bearish_count = sum(1 for word in self.bearish_words if word in text_lower)
        
        # Calculate sentiment score
        total_sentiment_words = bullish_count + bearish_count
        if total_sentiment_words > 0:
            sentiment_score = (bullish_count - bearish_count) / total_sentiment_words
        else:
            sentiment_score = 0
            
        # Extract tickers
        tickers = self.extract_tickers(text)
        
        return {
            'sentiment_score': sentiment_score,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'tickers': tickers
        }
        
    def extract_tickers(self, text: str) -> List[str]:
        """Extract potential stock tickers from text"""
        # Find all uppercase words that could be tickers
        potential_tickers = self.ticker_pattern.findall(text)
        
        # Filter out common words that aren't tickers
        common_words = {
            'I', 'A', 'THE', 'AND', 'OR', 'BUT', 'IN', 'ON', 'AT', 'TO', 'FOR',
            'OF', 'UP', 'IT', 'IS', 'BE', 'AS', 'SO', 'IF', 'NO', 'NOT', 'ALL',
            'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM',
            'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY',
            'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE'
        }
        
        tickers = [t for t in potential_tickers if t not in common_words]
        return tickers
        
    def aggregate_sentiment(self, texts: List[str]) -> Dict[str, Dict]:
        """Aggregate sentiment across multiple texts"""
        ticker_sentiment = {}
        ticker_mentions = Counter()
        
        for text in texts:
            analysis = self.analyze_text(text)
            
            for ticker in analysis['tickers']:
                ticker_mentions[ticker] += 1
                
                if ticker not in ticker_sentiment:
                    ticker_sentiment[ticker] = {
                        'total_sentiment': 0,
                        'count': 0,
                        'bullish_mentions': 0,
                        'bearish_mentions': 0
                    }
                    
                ticker_sentiment[ticker]['total_sentiment'] += analysis['sentiment_score']
                ticker_sentiment[ticker]['count'] += 1
                
                if analysis['sentiment_score'] > 0:
                    ticker_sentiment[ticker]['bullish_mentions'] += 1
                elif analysis['sentiment_score'] < 0:
                    ticker_sentiment[ticker]['bearish_mentions'] += 1
                    
        # Calculate average sentiment for each ticker
        results = {}
        for ticker, data in ticker_sentiment.items():
            if data['count'] > 0:
                avg_sentiment = data['total_sentiment'] / data['count']
                results[ticker] = {
                    'sentiment': avg_sentiment,
                    'mentions': ticker_mentions[ticker],
                    'bullish_mentions': data['bullish_mentions'],
                    'bearish_mentions': data['bearish_mentions']
                }
                
        return results