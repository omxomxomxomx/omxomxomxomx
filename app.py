from flask import Flask, render_template, jsonify
import yfinance as yf
from datetime import datetime
import random
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
_anthropic_client = None


def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _anthropic_client


# ─── Mock X/Twitter data ──────────────────────────────────────────────
# To switch to live X data:
#   pip install tweepy
#   Set X_BEARER_TOKEN in your .env file
#   Replace generate_mock_tweets() body with:
#
#   import tweepy, os
#   client = tweepy.Client(bearer_token=os.environ["X_BEARER_TOKEN"])
#   response = client.search_recent_tweets(
#       query=f"${ticker} lang:en -is:retweet",
#       max_results=20,
#       tweet_fields=["public_metrics", "author_id"],
#       expansions=["author_id"],
#       user_fields=["name", "username", "public_metrics", "verified"]
#   )

MOCK_INFLUENCERS = [
    {"handle": "@elonmusk",   "followers": "180M", "verified": True},
    {"handle": "@jimcramer",  "followers": "2.1M", "verified": True},
    {"handle": "@chamath",    "followers": "1.6M", "verified": True},
    {"handle": "@stocktwits", "followers": "890K", "verified": True},
    {"handle": "@benzinga",   "followers": "650K", "verified": True},
    {"handle": "@zerohedge",  "followers": "1.2M", "verified": False},
]

MOCK_TWEET_TEMPLATES = {
    "bullish": [
        "{ticker} looking strong today. Breaking out of resistance.",
        "Adding more {ticker} on this dip. Long-term conviction here.",
        "{ticker} earnings next week — expecting a beat. Accumulating.",
        "Technical setup on {ticker} is clean. Higher highs incoming.",
        "Institutions loading up on {ticker}. Follow the smart money.",
        "{ticker} fundamentals remain rock solid. Still my top hold.",
    ],
    "bearish": [
        "{ticker} overvalued at these levels. Taking profits here.",
        "Selling half my {ticker} position. Risk/reward unfavorable.",
        "{ticker} macro headwinds too strong. Caution warranted.",
        "Chart on {ticker} showing distribution. Be careful.",
        "Insider selling at {ticker}. Red flag for the near term.",
        "{ticker} guidance was soft. Downside risk underpriced.",
    ],
    "neutral": [
        "Watching {ticker} closely. Key level at current price.",
        "{ticker} consolidating. Waiting for direction before entering.",
        "Anyone tracking {ticker} earnings call tomorrow?",
        "{ticker} volume unusually high today. Worth monitoring.",
        "Mixed signals on {ticker}. Will update after market close.",
    ],
}

SENTIMENT_SYSTEM_PROMPT = """\
You are a financial sentiment analyst specializing in social media and stock market discussions.

Analyze each tweet about stocks and return a JSON array where each element has:
- "index": the tweet index (0-based)
- "sentiment": one of "bullish", "bearish", or "neutral"
- "compound_score": a float from -1.0 (most bearish) to +1.0 (most bullish)

Financial context rules:
- "diamond hands" / "holding" / "not selling" → bullish
- "to the moon" / "sending it" / "apes together" → bullish
- "dip buying" / "accumulating" / "adding" → bullish
- "taking profits" / "trimming" → slightly bearish
- "adding to short position" / "shorting" / "puts" → bearish
- "bag holding" / "bagholding" → bearish (stuck in a losing position)
- "weak hands" / "paper hands selling" → slightly bullish (others selling seen as opportunity)
- Sarcasm like "great earnings lol" or "totally not a bubble 🙄" → bearish
- Technical terms: "breakout" / "higher highs" → bullish; "distribution" / "lower lows" → bearish
- "overvalued" / "macro headwinds" / "guidance soft" → bearish
- "fundamentals solid" / "long-term conviction" → bullish

Return ONLY a valid JSON array, no explanation, no markdown code fences.\
"""


def analyze_sentiment_with_claude(ticker: str, posts: list) -> list:
    """
    Sends all posts to Claude in one API call and populates 'sentiment' and
    'compound_score' on each post. Falls back to keyword scoring if API fails.
    """
    texts = [p["text"] for p in posts]
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
    user_msg = f"Ticker: ${ticker}\n\nTweets:\n{numbered}"

    try:
        client = get_anthropic_client()
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": SENTIMENT_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_msg}],
        )
        results = json.loads(response.content[0].text)
        for item in results:
            idx = item["index"]
            posts[idx]["sentiment"] = item["sentiment"]
            posts[idx]["compound_score"] = round(float(item["compound_score"]), 3)
    except Exception:
        # Fallback: simple keyword scoring if Claude is unavailable
        for post in posts:
            text_lower = post["text"].lower()
            if any(w in text_lower for w in ["strong", "beat", "loading", "solid", "accumulate", "buying"]):
                post["sentiment"] = "bullish"
                post["compound_score"] = 0.5
            elif any(w in text_lower for w in ["overvalued", "selling", "soft", "caution", "bearish", "headwinds"]):
                post["sentiment"] = "bearish"
                post["compound_score"] = -0.5
            else:
                post["sentiment"] = "neutral"
                post["compound_score"] = 0.0

    return posts


def generate_mock_tweets(ticker: str, change_pct: float) -> list:
    """Returns mock X posts with Claude-powered sentiment. Swap body for tweepy calls to use live data."""
    random.seed(hash(ticker + str(datetime.now().date())))

    if change_pct > 1.5:
        weights = [0.65, 0.15, 0.20]
    elif change_pct < -1.5:
        weights = [0.15, 0.65, 0.20]
    else:
        weights = [0.35, 0.35, 0.30]

    tweets = []
    used_influencers = []
    for _ in range(8):
        sentiment_template = random.choices(["bullish", "bearish", "neutral"], weights=weights)[0]
        text = random.choice(MOCK_TWEET_TEMPLATES[sentiment_template]).format(ticker=f"${ticker}")

        remaining = [i for i in MOCK_INFLUENCERS if i not in used_influencers]
        if not remaining:
            remaining = MOCK_INFLUENCERS
        influencer = random.choice(remaining)
        used_influencers.append(influencer)

        likes = random.randint(20, 8000)
        retweets = random.randint(1, max(1, likes // 4))

        tweets.append({
            "handle":         influencer["handle"],
            "followers":      influencer["followers"],
            "verified":       influencer["verified"],
            "text":           text,
            "sentiment":      sentiment_template,
            "compound_score": 0.0,
            "likes":          likes,
            "retweets":       retweets,
            "time_ago":       f"{random.randint(1, 23)}h ago",
        })

    tweets = analyze_sentiment_with_claude(ticker, tweets)
    tweets.sort(key=lambda t: t["likes"], reverse=True)
    return tweets


# ─── Routes ───────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stock/<ticker>")
def get_stock(ticker):
    ticker = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        hist = stock.history(period="1y")
        if hist.empty:
            return jsonify({"error": f"No data found for {ticker}"}), 404

        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or float(hist["Close"].iloc[-1])
        )
        prev_close = info.get("previousClose") or (
            float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        )
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        chart_data = {
            "1d": _period_data(stock, "1d",  "5m"),
            "1w": _period_data(stock, "5d",  "30m"),
            "1m": _period_data(stock, "1mo", "1d"),
            "3m": _period_data(stock, "3mo", "1d"),
            "1y": _period_data(stock, "1y",  "1wk"),
        }

        return jsonify({
            "ticker":       ticker,
            "name":         info.get("longName", ticker),
            "price":        round(price, 2),
            "change":       round(change, 2),
            "change_pct":   round(change_pct, 2),
            "volume":       info.get("volume", 0),
            "avg_volume":   info.get("averageVolume", 0),
            "market_cap":   info.get("marketCap", 0),
            "pe_ratio":     info.get("trailingPE"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low":  info.get("fiftyTwoWeekLow"),
            "sector":       info.get("sector", "N/A"),
            "chart_data":   chart_data,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _period_data(stock, period: str, interval: str) -> dict:
    try:
        hist = stock.history(period=period, interval=interval)
        if interval in ("5m", "15m", "30m"):
            labels = [i.strftime("%H:%M") for i in hist.index]
        else:
            labels = [str(i.date()) for i in hist.index]
        return {
            "labels": labels,
            "prices": [round(float(p), 2) for p in hist["Close"]],
        }
    except Exception:
        return {"labels": [], "prices": []}


@app.route("/api/sentiment/<ticker>")
def get_sentiment(ticker):
    ticker = ticker.upper()
    try:
        hist = yf.Ticker(ticker).history(period="2d")
        change_pct = 0.0
        if len(hist) >= 2:
            change_pct = float(
                (hist["Close"].iloc[-1] - hist["Close"].iloc[-2])
                / hist["Close"].iloc[-2] * 100
            )

        tweets = generate_mock_tweets(ticker, change_pct)
        scores = [t["compound_score"] for t in tweets]
        avg = sum(scores) / len(scores) if scores else 0

        breakdown = {
            "bullish": sum(1 for t in tweets if t["sentiment"] == "bullish"),
            "bearish": sum(1 for t in tweets if t["sentiment"] == "bearish"),
            "neutral": sum(1 for t in tweets if t["sentiment"] == "neutral"),
        }
        overall = "Bullish" if avg > 0.05 else "Bearish" if avg < -0.05 else "Neutral"

        return jsonify({
            "ticker":              ticker,
            "overall_sentiment":   overall,
            "avg_score":           round(avg, 3),
            "sentiment_breakdown": breakdown,
            "tweets":              tweets,
            "data_source":         "mock",
            "note":                "Add X_BEARER_TOKEN to .env to enable live tweet data.",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


TRENDING_TICKERS = ["AAPL", "TSLA", "NVDA", "MSFT", "META", "AMZN", "GOOGL", "AMD"]


@app.route("/api/trending")
def get_trending():
    results = []
    for sym in TRENDING_TICKERS:
        try:
            info = yf.Ticker(sym).info
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0
            prev  = info.get("previousClose", price) or price
            pct   = ((price - prev) / prev * 100) if prev else 0
            results.append({
                "ticker":     sym,
                "name":       info.get("shortName", sym),
                "price":      round(price, 2),
                "change_pct": round(pct, 2),
            })
        except Exception:
            pass
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
