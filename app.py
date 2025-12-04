import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template

# Load variables from .env file (like OPENWEATHER_API_KEY)
load_dotenv()

app = Flask(__name__)


def get_weather(city="Ottawa", country="CA"):
    """Call OpenWeatherMap API and return a small dictionary of weather info."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("DEBUG: No OPENWEATHER_API_KEY found in environment.")
        return None

    # Don't print the whole key, just the first few characters
    print("DEBUG: Using API key starting with:", api_key[:5])

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": f"{city},{country}",
        "units": "metric",
        "appid": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        print("DEBUG: Weather API status code:", response.status_code)
        print("DEBUG: Weather API response (truncated):", response.text[:200])

        response.raise_for_status()
        data = response.json()

        weather = {
            "city": data.get("name"),
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"].title(),
        }
        return weather
    except requests.RequestException as e:
        print("DEBUG: Error calling weather API:", e)
        return None


def get_news(limit=5):
    """Fetch top front-page stories from Hacker News (no API key needed)."""
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "tags": "front_page",   # front page stories
        "hitsPerPage": limit,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        print("DEBUG: News API status code:", response.status_code)
        response.raise_for_status()
        data = response.json()

        articles = []
        for hit in data.get("hits", []):
            title = hit.get("title") or hit.get("story_title")
            link = hit.get("url") or hit.get("story_url")
            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                })

        return articles
    except requests.RequestException as e:
        print("DEBUG: Error calling news API:", e)
        return []


@app.route("/")
def home():
    weather = get_weather()          # default: Ottawa, CA
    news = get_news(limit=5)         # top 5 headlines
    return render_template(
        "home.html",
        title="Public API Dashboard",
        weather=weather,
        news=news,
    )


if __name__ == "__main__":
    app.run(debug=True)
