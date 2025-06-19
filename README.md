# SCRAP3R - Autonomous Stock Trading Bot

An intelligent trading bot that executes trades based on market sentiment and real-time data analysis.

## Architecture

```
SCRAP3R/
├── src/
│   ├── config/        # Configuration management
│   ├── trading/       # Trading logic and execution
│   ├── sentiment/     # Market sentiment analysis
│   ├── data/          # Real-time data handling
│   ├── models/        # Data models
│   └── utils/         # Utilities and helpers
├── main.py            # Main application (real-time trading)
├── run_scraper.py     # Sentiment-based scanner (scheduled)
└── requirements.txt   # Dependencies
```

## Features

- **Modular Architecture**: Clean separation of concerns with organized modules
- **Sentiment Analysis**: Scrapes Reddit for market sentiment
- **Real-time Trading**: WebSocket integration for live market data
- **Risk Management**: Position sizing, stop-loss, and profit targets
- **Multi-position Support**: Manage multiple positions simultaneously
- **Automated Monitoring**: Continuous position monitoring and exit management

## Components

### Configuration (`src/config/`)
- `settings.py`: Centralized configuration management
- `constants.py`: Application-wide constants

### Trading (`src/trading/`)
- `client.py`: Alpaca API wrapper
- `position_manager.py`: Position tracking and P&L management
- `risk_manager.py`: Risk controls and validation

### Sentiment Analysis (`src/sentiment/`)
- `analyzer.py`: Text sentiment analysis
- `reddit_scraper.py`: Reddit data collection

### Data (`src/data/`)
- `stream_handler.py`: Real-time market data processing

### Models (`src/models/`)
- `trade.py`: Trade order representation
- `position.py`: Position tracking
- `signal.py`: Trading signal generation

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   export ALPACA_KEY=your_alpaca_key
   export ALPACA_SECRET=your_alpaca_secret
   ```

## Usage

### Real-time Trading Bot
```bash
python main.py
```

### Sentiment Scanner (for scheduled runs)
```bash
python run_scraper.py
```

### Local Development
```bash
./run_local.sh
```

## Configuration

Key settings in `src/config/settings.py`:
- `profit_target`: Target profit percentage (default: 5%)
- `stop_loss`: Stop loss percentage (default: 2%)
- `max_positions`: Maximum concurrent positions (default: 5)
- `min_sentiment`: Minimum sentiment score to trade (default: 0.3)

## Deployment

### GitHub Actions
Automated pre-market scanning at 6:30 AM EST via `.github/workflows/pre-market-scan.yml`

### Render
Deploy as a background worker using `render.yaml`

## Error Monitoring

SCRAP3R includes a web dashboard for monitoring errors:

### Local Dashboard
```bash
# Test error logging
python test_dashboard.py

# Run the dashboard
python web_dashboard.py

# Open in browser
http://localhost:5000
```

### Production Dashboard
When deployed to Render, the dashboard will be available at:
- `https://scrap3r-dashboard.onrender.com`

### Features
- Real-time error tracking
- Critical error alerts
- Download error logs for debugging
- Clear error history
- Auto-refresh every 30 seconds

## Testing

Run tests (when implemented):
```bash
pytest tests/
```

## License

Private repository - All rights reserved