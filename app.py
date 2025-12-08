import os
import requests
from flask import Flask, render_template
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

load_dotenv()

app = Flask(__name__)


# ---------- Weather (Open-Meteo, no API key needed) ----------

def get_weather_data():
    """
    Fetch current weather for Ottawa using Open-Meteo (no API key).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 45.4215,    # Ottawa
        "longitude": -75.6972,
        "current_weather": "true",
    }

    # Simple mapping of weather codes to descriptions
    weather_code_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        80: "Rain showers",
        81: "Rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        cw = data.get("current_weather", {})
        print("DEBUG: Weather API status code:", resp.status_code)
        print("DEBUG: Weather API data:", cw)

        if not cw:
            return None

        code = cw.get("weathercode")
        description = weather_code_map.get(code, "Current conditions")

        weather = {
            "city": "Ottawa",
            "temp": round(cw.get("temperature", 0)),
            "description": description,
        }
        return weather
    except Exception as e:
        print("DEBUG: Weather API error:", e)
        return None


# ---------- Market / Crypto News via RSS ----------

def get_news_data(limit=8):
    """
    Fetch finance/crypto-focused headlines from multiple RSS feeds.
    We combine them and take the first `limit` items.
    """
    FEEDS = [
        # General finance / markets
        "https://finance.yahoo.com/news/rssindex",
        # Crypto-focused feeds
        "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
        "https://cointelegraph.com/rss",
    ]

    items = []

    for feed_url in FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10)
            resp.raise_for_status()
            print(f"DEBUG: News feed status for {feed_url}: {resp.status_code}")

            root = ET.fromstring(resp.text)
            channel = root.find("channel")
            if channel is None:
                continue

            for item in channel.findall("item"):
                title_el = item.find("title")
                link_el = item.find("link")
                if title_el is not None and link_el is not None:
                    items.append(
                        {"title": title_el.text, "url": link_el.text}
                    )
        except Exception as e:
            print("DEBUG: News feed error for", feed_url, "->", e)
            continue

    # You could sort here if you wanted, but RSS usually already gives recent first.
    return items[:limit]


# ---------- Crypto (CoinGecko top 5) ----------

def get_crypto_data():
    """
    Fetch top 5 cryptocurrencies by market cap from CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 5,
        "page": 1,
        "price_change_percentage": "24h",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("DEBUG: Crypto API status code:", resp.status_code)

        crypto_list = []
        for item in data:
            crypto_list.append(
                {
                    "name": item.get("name"),
                    "symbol": item.get("symbol", "").upper(),
                    "price": float(item.get("current_price", 0.0)),
                    "change_24h": float(
                        item.get("price_change_percentage_24h", 0.0)
                    ),
                }
            )
        return crypto_list
    except Exception as e:
        print("DEBUG: Crypto API error:", e)
        return None


# ---------- Stocks (top 5, requires API key) ----------

SAMPLE_STOCKS = [
    {"name": "Apple Inc.", "symbol": "AAPL", "price": 190.12, "change_24h": 0.75},
    {"name": "Microsoft Corp.", "symbol": "MSFT", "price": 415.33, "change_24h": 1.20},
    {"name": "Alphabet Inc. (Class A)", "symbol": "GOOGL", "price": 172.84, "change_24h": -0.45},
    {"name": "Amazon.com Inc.", "symbol": "AMZN", "price": 175.92, "change_24h": 0.10},
    {"name": "Meta Platforms Inc.", "symbol": "META", "price": 330.05, "change_24h": -0.80},
]


def get_stock_data():
    """
    Fetch quotes for 5 large-cap US stocks using Yahoo Finance's public quote API.
    If the API is rate-limited or fails (e.g., 429 Too Many Requests), fall back
    to SAMPLE_STOCKS so the dashboard always has data to display.
    """
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = {"symbols": ",".join(symbols)}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("DEBUG: Stocks API status code:", resp.status_code)

        quotes = data.get("quoteResponse", {}).get("result", [])
        stock_list = []
        for q in quotes:
            stock_list.append(
                {
                    "name": q.get("shortName") or q.get("longName") or q.get("symbol"),
                    "symbol": q.get("symbol"),
                    "price": float(q.get("regularMarketPrice", 0.0)),
                    "change_24h": float(q.get("regularMarketChangePercent", 0.0)),
                }
            )

        # If API returned nothing for some reason, use fallback sample data
        if not stock_list:
            print("DEBUG: Stocks API returned empty result, using SAMPLE_STOCKS")
            return SAMPLE_STOCKS

        return stock_list

    except Exception as e:
        print("DEBUG: Stocks API error:", e)
        print("DEBUG: Using SAMPLE_STOCKS fallback data for stocks")
        return SAMPLE_STOCKS

# ---------- Routes ----------

@app.route("/")
def home():
    weather = get_weather_data()
    news = get_news_data()
    crypto = get_crypto_data()
    stocks = get_stock_data()
    return render_template(
        "home.html",
        weather=weather,
        news=news,
        crypto=crypto,
        stocks=stocks,
    )


if __name__ == "__main__":
    app.run(debug=True)
