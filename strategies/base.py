class BaseStrategy:
    name = "base"

    def build_signals(self, bars, config):
        raise NotImplementedError

    def score_signals(self, signale):
        kaufen = sum(1 for signal, _ in signale.values() if signal == "KAUFEN")
        verkaufen = sum(1 for signal, _ in signale.values() if signal == "VERKAUFEN")
        return kaufen, verkaufen

    def stars(self, score, total=7):
        filled = round(score / total * 5)
        return "⭐" * filled + "☆" * (5 - filled)

    def summary_signal(self, kauf_score, verkauf_score):
        if kauf_score >= 5:
            return "🟢 KAUFEN"
        if verkauf_score >= 5:
            return "🔴 VERKAUFEN"
        if kauf_score >= 3:
            return "🟡 NEUTRAL+"
        return "⏳ NEUTRAL"

    def evaluate(self, bars, config):
        signale, kurs = self.build_signals(bars, config)
        kauf_score, verkauf_score = self.score_signals(signale)
        return {
            "signale": signale,
            "kurs": kurs,
            "kauf_score": kauf_score,
            "verkauf_score": verkauf_score,
            "summary_signal": self.summary_signal(kauf_score, verkauf_score),
        }

    def should_buy(self, kauf_score, verkauf_score):
        return kauf_score >= 5

    def should_sell(self, kauf_score, verkauf_score):
        return verkauf_score >= 5
