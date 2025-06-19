"""Application-wide constants"""

# Default symbols to trade when Reddit scraping fails
DEFAULT_SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']

# Sentiment analysis keywords
BULLISH_WORDS = [
    'moon', 'rocket', 'buy', 'calls', 'squeeze', 'pump', 'long', 
    'tendies', 'gains', 'yolo', 'diamond hands', 'hodl', 'bull',
    'breakout', 'mooning', 'printing', 'green', 'bullish', 'up'
]

BEARISH_WORDS = [
    'puts', 'short', 'sell', 'dump', 'crash', 'drill', 'tank',
    'bear', 'red', 'down', 'loss', 'bearish', 'overvalued',
    'bubble', 'correction', 'decline', 'fall', 'drop', 'rip'
]

# Market hours (EST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# Pre-market hours
PRE_MARKET_OPEN_HOUR = 4
PRE_MARKET_OPEN_MINUTE = 0

# WebSocket subscription limits
MAX_WEBSOCKET_SYMBOLS = 30