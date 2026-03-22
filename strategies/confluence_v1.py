from indicators import (
    berechne_bollinger,
    berechne_macd,
    berechne_rsi,
    berechne_stochastic,
    berechne_trend,
    berechne_volume_signal,
    berechne_williams,
)

from .base import BaseStrategy


class ConfluenceV1Strategy(BaseStrategy):
    name = "confluence_v1"

    def build_signals(self, bars, config):
        kurs = bars[-1].close
        signale = {}
        strategy_cfg = config["strategy"]

        rsi = berechne_rsi(bars, strategy_cfg["rsi_period"])
        if rsi < strategy_cfg["rsi_buy"]:
            signale["RSI"] = ("KAUFEN", f"RSI={rsi}")
        elif rsi > strategy_cfg["rsi_sell"]:
            signale["RSI"] = ("VERKAUFEN", f"RSI={rsi}")
        else:
            signale["RSI"] = ("NEUTRAL", f"RSI={rsi}")

        trend = berechne_trend(bars)
        signale["MA"] = ("KAUFEN", "MA10>MA20>MA50") if trend else ("VERKAUFEN", "Kein Aufwärtstrend")

        macd, signal = berechne_macd(bars)
        signale["MACD"] = ("KAUFEN", f"MACD={macd}") if macd > signal else ("VERKAUFEN", f"MACD={macd}")

        bb_low, _, bb_high = berechne_bollinger(bars)
        if kurs < bb_low:
            signale["Bollinger"] = ("KAUFEN", f"Unter Band ${bb_low}")
        elif kurs > bb_high:
            signale["Bollinger"] = ("VERKAUFEN", f"Über Band ${bb_high}")
        else:
            signale["Bollinger"] = ("NEUTRAL", "Im Band")

        stoch = berechne_stochastic(bars)
        if stoch < 20:
            signale["Stochastic"] = ("KAUFEN", f"Stoch={stoch}")
        elif stoch > 80:
            signale["Stochastic"] = ("VERKAUFEN", f"Stoch={stoch}")
        else:
            signale["Stochastic"] = ("NEUTRAL", f"Stoch={stoch}")

        williams = berechne_williams(bars)
        if williams < -80:
            signale["Williams"] = ("KAUFEN", f"W%R={williams}")
        elif williams > -20:
            signale["Williams"] = ("VERKAUFEN", f"W%R={williams}")
        else:
            signale["Williams"] = ("NEUTRAL", f"W%R={williams}")

        vol_signal = berechne_volume_signal(bars)
        signale["Volume"] = (vol_signal, "Vol>120% Avg" if vol_signal != "NEUTRAL" else "Normales Vol")
        return signale, kurs
