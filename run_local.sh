#!/bin/bash

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    echo "ALPACA_KEY=your_key_here" > .env
    echo "ALPACA_SECRET=your_secret_here" >> .env
    echo "Please edit .env with your actual Alpaca credentials"
    exit 1
fi

# Load environment variables
export $(cat .env | xargs)

# Install dependencies
pip install -r requirements.txt

# Run the MCP trader
echo "Starting SCRAP3R MCP Trader..."
python mcp_trader.py