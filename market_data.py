import json
import os
import re
from datetime import UTC, datetime, timedelta

import requests
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

try:
    import openai
except ImportError:
    openai = None


API_KEY = os.environ.get("ALPACA_KEY")
SECRET_KEY = os.environ.get("ALPACA_SECRET")
NEWS_API_KEY = os.environ.get("NEWS_KEY")
OPENAI_KEY = os.environ.get("OPENAI_KEY")

data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
crypto_data_client = CryptoHistoricalDataClient(API_KEY, SECRET_KEY)
openai_client = openai.OpenAI(api_key=OPENAI_KEY) if openai and OPENAI_KEY else None
CRYPTO_SYMBOL_PATTERN = re.compile(r"^[A-Z]+/[A-Z]+$")


def ist_gueltiges_krypto_symbol(symbol):
    return bool(CRYPTO_SYMBOL_PATTERN.match(symbol))


def headline_passt_zu_symbol(symbol, title, config):
    text = (title or "").lower()
    keywords = config["news_keywords"].get(symbol, [symbol.replace("/USD", "").lower()])
    return any(keyword in text for keyword in keywords)


def get_news(symbol, config, limit=5):
    if symbol not in config["news_symbols"]:
        return []
    try:
        clean = symbol.replace("/USD", "")
        url = (
            f"https://newsapi.org/v2/everything"
            f"?q={clean}+stock"
            f"&language=en"
            f"&sortBy=publishedAt"
            f"&pageSize={limit}"
            f"&apiKey={NEWS_API_KEY}"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("status") != "ok":
            print(f"   ⚠️ NewsAPI: {data.get('message')}")
            return []

        headlines = [
            article["title"] for article in data.get("articles", [])
            if article.get("title")
            and "[Removed]" not in article["title"]
            and headline_passt_zu_symbol(symbol, article["title"], config)
        ]
        print(f"   📰 {len(headlines)} Headlines gefunden")
        return headlines[:limit]
    except Exception as exc:
        print(f"   ⚠️ News Fehler: {exc}")
        return []


def analysiere_sentiment(symbol, headlines):
    if not headlines:
        return "NEUTRAL", 50, "Keine News verfügbar", []
    if openai_client is None:
        return "NEUTRAL", 50, "OpenAI nicht verfügbar", headlines

    try:
        headlines_text = "\n".join([f"- {headline}" for headline in headlines])
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[{
                "role": "system",
                "content": "Du bist ein präziser Finanz-Analyst. Antworte NUR mit validem JSON, kein Markdown, keine Erklärungen."
            }, {
                "role": "user",
                "content": f"""Analysiere diese Finanz-Headlines für {symbol}:

{headlines_text}

Antworte NUR mit diesem JSON Format:
{{"sentiment": "POSITIV", "score": 75, "grund": "Starke Quartalszahlen erwartet"}}

Sentiment: POSITIV (score 60-100) / NEGATIV (score 0-40) / NEUTRAL (score 41-59)"""
            }]
        )
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        sentiment = result.get("sentiment", "NEUTRAL")
        score = int(result.get("score", 50))
        grund = result.get("grund", "")
        return sentiment, score, grund, headlines
    except Exception as exc:
        print(f"   ⚠️ Sentiment Fehler: {exc}")
        return "NEUTRAL", 50, "Analyse fehlgeschlagen", headlines


def get_kursdaten(symbol, krypto=False):
    try:
        if krypto:
            if not ist_gueltiges_krypto_symbol(symbol):
                print(f"   ⚠️ Krypto-Symbol übersprungen: {symbol}")
                return None
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=120),
                end=datetime.now() - timedelta(days=1),
            )
            bars = crypto_data_client.get_crypto_bars(request)
        else:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=120),
                end=datetime.now() - timedelta(days=1),
            )
            bars = data_client.get_stock_bars(request)
        return bars[symbol]
    except Exception as exc:
        print(f"   ⚠️ Kursdaten Fehler für {symbol}: {exc}")
        return None


def get_historical_bars(symbol, start, end, krypto=False):
    try:
        start_dt = start if isinstance(start, datetime) else datetime.fromisoformat(str(start))
        end_dt = end if isinstance(end, datetime) else datetime.fromisoformat(str(end))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=UTC)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=UTC)

        if krypto:
            if not ist_gueltiges_krypto_symbol(symbol):
                print(f"   ⚠️ Krypto-Symbol übersprungen: {symbol}")
                return None
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
            )
            bars = crypto_data_client.get_crypto_bars(request)
        else:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
            )
            bars = data_client.get_stock_bars(request)
        return bars[symbol]
    except Exception as exc:
        print(f"   ⚠️ Historische Daten Fehler für {symbol}: {exc}")
        return None
