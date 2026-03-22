import importlib
import sys
import types
import unittest
from unittest.mock import patch


def install_fake_dependencies():
    alpaca = types.ModuleType("alpaca")
    trading = types.ModuleType("alpaca.trading")
    trading_client = types.ModuleType("alpaca.trading.client")
    trading_requests = types.ModuleType("alpaca.trading.requests")
    trading_enums = types.ModuleType("alpaca.trading.enums")
    data = types.ModuleType("alpaca.data")
    data_historical = types.ModuleType("alpaca.data.historical")
    data_requests = types.ModuleType("alpaca.data.requests")
    data_timeframe = types.ModuleType("alpaca.data.timeframe")
    openai = types.ModuleType("openai")

    class DummyTradingClient:
        def __init__(self, *args, **kwargs):
            pass

    class DummyHistoricalClient:
        def __init__(self, *args, **kwargs):
            pass

    class DummyRequest:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

    class DummyTimeFrame:
        Day = "day"

    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_: None))

    trading_client.TradingClient = DummyTradingClient
    trading_requests.MarketOrderRequest = DummyRequest
    trading_enums.OrderSide = types.SimpleNamespace(BUY="BUY", SELL="SELL")
    trading_enums.TimeInForce = types.SimpleNamespace(GTC="GTC")
    data_historical.StockHistoricalDataClient = DummyHistoricalClient
    data_historical.CryptoHistoricalDataClient = DummyHistoricalClient
    data_requests.StockBarsRequest = DummyRequest
    data_requests.CryptoBarsRequest = DummyRequest
    data_timeframe.TimeFrame = DummyTimeFrame
    openai.OpenAI = DummyOpenAI

    sys.modules["alpaca"] = alpaca
    sys.modules["alpaca.trading"] = trading
    sys.modules["alpaca.trading.client"] = trading_client
    sys.modules["alpaca.trading.requests"] = trading_requests
    sys.modules["alpaca.trading.enums"] = trading_enums
    sys.modules["alpaca.data"] = data
    sys.modules["alpaca.data.historical"] = data_historical
    sys.modules["alpaca.data.requests"] = data_requests
    sys.modules["alpaca.data.timeframe"] = data_timeframe
    sys.modules["openai"] = openai


install_fake_dependencies()
main = importlib.import_module("main")


class Bar:
    def __init__(self, close, high=None, low=None, volume=100):
        self.close = close
        self.high = high if high is not None else close
        self.low = low if low is not None else close
        self.volume = volume


class MainTests(unittest.TestCase):
    def test_strategy_loader_laed_confluence_v1(self):
        strategy = main.get_strategy(main.CONFIG)

        self.assertEqual(strategy.name, "confluence_v1")

    def test_headline_passt_zu_symbol_filtert_irrelevante_titel(self):
        self.assertTrue(main.headline_passt_zu_symbol("PYPL", "PayPal launches new checkout features", main.CONFIG))
        self.assertFalse(main.headline_passt_zu_symbol("PYPL", "Coinbase launches 24/7 stock perps", main.CONFIG))

    def test_get_news_entfernt_irrelevante_headlines(self):
        payload = {
            "status": "ok",
            "articles": [
                {"title": "PayPal launches new checkout features"},
                {"title": "Coinbase launches 24/7 stock perps"},
            ],
        }

        with patch.object(main.market_data.requests, "get", return_value=types.SimpleNamespace(json=lambda: payload)):
            headlines = main.get_news("PYPL", main.CONFIG)

        self.assertEqual(headlines, ["PayPal launches new checkout features"])

    def test_berechne_macd_gibt_valide_werte_zurueck(self):
        bars = [Bar(close=float(i)) for i in range(1, 40)]

        macd, signal = main.berechne_macd(bars)

        self.assertIsInstance(macd, float)
        self.assertIsInstance(signal, float)
        self.assertNotEqual(macd, signal)

    def test_invalides_krypto_symbol_wird_vor_api_call_uebersprungen(self):
        bars = main.market_data.get_kursdaten("1INCH/USD", krypto=True)

        self.assertIsNone(bars)

    def test_scan_verkauft_gesamte_positionsgroesse_bei_verkaufssignal(self):
        bars = [Bar(close=float(i), high=float(i) + 1, low=float(i) - 1, volume=100 + i) for i in range(1, 60)]
        analyse = {
            "signale": {"MA": ("VERKAUFEN", "Kein Aufwärtstrend")},
            "kurs": 59.0,
            "kauf_score": 1,
            "verkauf_score": 5,
            "summary_signal": "🔴 VERKAUFEN",
        }

        with patch.object(main, "get_kursdaten", return_value=bars), \
             patch.object(main, "hat_position", return_value=(True, 100.0, 3.5)), \
             patch.object(main, "get_news", return_value=[]), \
             patch.object(main, "analysiere_sentiment", return_value=("NEUTRAL", 50, "Keine News verfügbar", [])), \
             patch.object(main, "pruefe_sl_tp", return_value=("halten", 1.0)), \
             patch("main.get_strategy", return_value=types.SimpleNamespace(
                 name="confluence_v1",
                 evaluate=lambda *_args, **_kwargs: analyse,
                 stars=lambda score, total=7: "⭐⭐⭐⭐☆",
             )), \
             patch.object(main, "order_verkaufen") as order_verkaufen:
            _, verkauf, _ = main.scan(["AAPL"], krypto=False, config=main.CONFIG)

        order_verkaufen.assert_called_once_with("AAPL", 3.5, main.CONFIG)
        self.assertEqual(len(verkauf), 1)


if __name__ == "__main__":
    unittest.main()
