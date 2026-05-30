# StockTrends — Yahoo Finance + X

A dark-themed web dashboard that combines real stock data from Yahoo Finance with X/Twitter sentiment analysis.

## Features

- **Live stock data** via `yfinance` (no API key needed)
- **Price charts** with 1D / 1W / 1M / 3M / 1Y timeframes
- **Key metrics**: price, change %, volume, market cap, P/E, 52-week range
- **X sentiment analysis** using VADER NLP (mock data by default, real X API ready)
- **Influencer mentions** feed with sentiment labels and engagement stats
- **Trending tickers** sidebar (AAPL, TSLA, NVDA, MSFT, META, AMZN, GOOGL, AMD)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open in browser
# http://localhost:5000
```

## Enabling Live X/Twitter Data

By default the app uses mock X posts. To switch to real tweets:

1. Get a free X API Bearer Token at <https://developer.twitter.com/en/portal/dashboard>
2. Copy `.env.example` to `.env` and set your token:
   ```
   X_BEARER_TOKEN=your_token_here
   ENABLE_LIVE_X=true
   ```
3. In `app.py`, replace the body of `generate_mock_tweets()` with the Tweepy snippet shown in the comments.

## Stack

| Layer    | Tech |
|----------|------|
| Backend  | Python · Flask · yfinance · VADER |
| Frontend | Bootstrap 5 · Chart.js · Bootstrap Icons |
| X API    | Tweepy (scaffold included) |
