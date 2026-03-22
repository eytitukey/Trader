import importlib
import json
import tempfile
import sys
import types
import unittest
from pathlib import Path
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
reporting = importlib.import_module("reporting")
backtest = importlib.import_module("backtest")
execution = importlib.import_module("execution")


class Bar:
    def __init__(self, close, high=None, low=None, volume=100):
        self.close = close
        self.high = high if high is not None else close
        self.low = low if low is not None else close
        self.volume = volume


class MainTests(unittest.TestCase):
    def test_strategy_loader_laed_confluence_v1(self):
        config = dict(main.CONFIG)
        config["strategy"] = dict(main.CONFIG["strategy"])
        config["strategy"]["name"] = "confluence_v1"
        strategy = main.get_strategy(config)

        self.assertEqual(strategy.name, "confluence_v1")

    def test_strategy_loader_laed_mean_reversion_v1(self):
        config = dict(main.CONFIG)
        config["strategy"] = dict(main.CONFIG["strategy"])
        config["strategy"]["name"] = "mean_reversion_v1"

        strategy = main.get_strategy(config)

        self.assertEqual(strategy.name, "mean_reversion_v1")

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

    def test_order_kaufen_nutzt_fuer_krypto_mindestens_10_usd_notional(self):
        config = dict(main.CONFIG)
        config["risk"] = dict(main.CONFIG["risk"])
        config["risk"]["order_qty"] = 1

        with patch.object(execution, "MarketOrderRequest") as order_request, \
             patch.object(execution.trading_client, "submit_order", create=True):
            execution.order_kaufen("DOGE/USD", 0.2, config)

        kwargs = order_request.call_args.kwargs
        self.assertEqual(kwargs["symbol"], "DOGE/USD")
        self.assertEqual(kwargs["notional"], 10.0)
        self.assertNotIn("qty", kwargs)

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
                 should_buy=lambda kauf, verkauf: kauf >= 5,
                 should_sell=lambda kauf, verkauf: verkauf >= 5,
             )), \
             patch.object(main, "order_verkaufen") as order_verkaufen:
            _, verkauf, _, scan_results = main.scan(["AAPL"], krypto=False, config=main.CONFIG)

        order_verkaufen.assert_called_once_with("AAPL", 3.5, main.CONFIG)
        self.assertEqual(len(verkauf), 1)
        self.assertEqual(scan_results[0]["action"], "SELL_SIGNAL")
        self.assertEqual(scan_results[0]["strategy"], "confluence_v1")

    def test_speichere_run_history_schreibt_json_liste(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            reporting.speichere_run_history({"run_id": "run-1"}, path=history_path)
            reporting.speichere_run_history({"run_id": "run-2"}, path=history_path)

            with open(history_path, "r", encoding="utf-8") as handle:
                history = json.load(handle)

        self.assertEqual([entry["run_id"] for entry in history], ["run-1", "run-2"])

    def test_backtest_strategy_gibt_grundlegende_kennzahlen_zurueck(self):
        bars = [Bar(close=float(i), high=float(i) + 1, low=float(i) - 1, volume=100 + i) for i in range(1, 80)]
        config = dict(main.CONFIG)
        config["strategy"] = dict(main.CONFIG["strategy"])
        config["strategy"]["name"] = "mean_reversion_v1"

        with patch("backtest.get_strategy", return_value=types.SimpleNamespace(
            name="mean_reversion_v1",
            evaluate=lambda window, _config: {
                "kurs": float(window[-1].close),
                "kauf_score": 3 if len(window) == 51 else 0,
                "verkauf_score": 3 if len(window) == 60 else 0,
                "signale": {},
                "summary_signal": "🟢 KAUFEN",
            },
            should_buy=lambda kauf, verkauf: kauf >= 3,
            should_sell=lambda kauf, verkauf: verkauf >= 3,
        )):
            result = backtest.backtest_strategy("AAPL", bars, config, initial_cash=1000)

        self.assertEqual(result["mode"], "backtest")
        self.assertEqual(result["symbol"], "AAPL")
        self.assertGreaterEqual(result["trade_count"], 2)
        self.assertIn("final_equity", result)
        self.assertIn("max_drawdown_pct", result)


if __name__ == "__main__":
    unittest.main()
