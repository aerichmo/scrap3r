# SCRAP3R - Sentiment-Driven Trading Bot

An autonomous trading bot that analyzes Reddit sentiment and executes trades using Alpaca's MCP infrastructure.

## Features

- **Sentiment Analysis**: Scrapes Reddit WSB for bullish/bearish sentiment
- **MCP Integration**: Uses Alpaca's Model Context Protocol for smart execution
- **Real-time Data**: WebSocket streams for live quotes, trades, and bars
- **Risk Management**: Automatic profit-taking (5%) and stop-loss (2%)
- **Volume Detection**: Identifies unusual trading volume for better entries

## Components

1. **scraper.py** - Pre-market sentiment analysis (runs at 6:30 AM EST)
2. **mcp_trader.py** - Real-time trading with MCP integration
3. **GitHub Actions** - Automated scheduling and deployment

## Setup

1. Add secrets to GitHub repository:
   - `SCRAP3R_KEY` - Alpaca API key
   - `SCRAP3R_SECRET` - Alpaca API secret

2. Deploy MCP trader to persistent service (Railway/Render recommended)

## Trading Logic

- Monitors Reddit for ticker mentions
- Calculates sentiment score based on keywords
- Only trades when sentiment > 30% positive
- Enters on volume spikes or price momentum
- Exits at 5% profit or 2% loss

## Safety

- Uses Alpaca paper trading by default
- Limited to $100 per position
- One position at a time per symbol