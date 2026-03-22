from indicators import (
    berechne_bollinger,
    berechne_rsi,
    berechne_stochastic,
    berechne_williams,
)

from .base import BaseStrategy


class MeanReversionV1Strategy(BaseStrategy):
    name = "mean_reversion_v1"

    def build_signals(self, bars, config):
        kurs = bars[-1].close
        signale = {}

        rsi = berechne_rsi(bars, 14)
        if rsi <= 30:
            signale["RSI"] = ("KAUFEN", f"RSI={rsi}")
        elif rsi >= 70:
            signale["RSI"] = ("VERKAUFEN", f"RSI={rsi}")
        else:
            signale["RSI"] = ("NEUTRAL", f"RSI={rsi}")

        bb_low, bb_mid, bb_high = berechne_bollinger(bars, 20)
        if kurs < bb_low:
            signale["Bollinger"] = ("KAUFEN", f"Unter Band ${bb_low}")
        elif kurs > bb_high:
            signale["Bollinger"] = ("VERKAUFEN", f"Über Band ${bb_high}")
        else:
            signale["Bollinger"] = ("NEUTRAL", f"Richtung Mitte ${bb_mid}")

        stoch = berechne_stochastic(bars, 14)
        if stoch <= 20:
            signale["Stochastic"] = ("KAUFEN", f"Stoch={stoch}")
        elif stoch >= 80:
            signale["Stochastic"] = ("VERKAUFEN", f"Stoch={stoch}")
        else:
            signale["Stochastic"] = ("NEUTRAL", f"Stoch={stoch}")

        williams = berechne_williams(bars, 14)
        if williams <= -80:
            signale["Williams"] = ("KAUFEN", f"W%R={williams}")
        elif williams >= -20:
            signale["Williams"] = ("VERKAUFEN", f"W%R={williams}")
        else:
            signale["Williams"] = ("NEUTRAL", f"W%R={williams}")

        return signale, kurs

    def summary_signal(self, kauf_score, verkauf_score):
        if kauf_score >= 3:
            return "🟢 KAUFEN"
        if verkauf_score >= 3:
            return "🔴 VERKAUFEN"
        if kauf_score >= 2:
            return "🟡 NEUTRAL+"
        return "⏳ NEUTRAL"

    def stars(self, score, total=4):
        return super().stars(score, total)

    def should_buy(self, kauf_score, verkauf_score):
        return kauf_score >= 3

    def should_sell(self, kauf_score, verkauf_score):
        return verkauf_score >= 3
