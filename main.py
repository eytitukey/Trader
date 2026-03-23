from datetime import datetime
import time
from uuid import uuid4

import execution
import indicators
import market_data
from config import load_config
from execution import trading_client
from reporting import baue_positionen_liste, sende_telegram, speichere_ergebnisse, speichere_run_history
from strategies import get_strategy


CONFIG = load_config()

get_kursdaten = market_data.get_kursdaten
get_news = market_data.get_news
analysiere_sentiment = market_data.analysiere_sentiment
headline_passt_zu_symbol = market_data.headline_passt_zu_symbol

berechne_rsi = indicators.berechne_rsi
berechne_ma = indicators.berechne_ma
berechne_macd = indicators.berechne_macd
berechne_bollinger = indicators.berechne_bollinger
berechne_stochastic = indicators.berechne_stochastic
berechne_williams = indicators.berechne_williams
berechne_volume_signal = indicators.berechne_volume_signal
berechne_trend = indicators.berechne_trend
berechne_support_resistance = indicators.berechne_support_resistance
berechne_korrelation = indicators.berechne_korrelation
korrelation_label = indicators.korrelation_label

hat_position = execution.hat_position
order_kaufen = execution.order_kaufen
order_verkaufen = execution.order_verkaufen
pruefe_sl_tp = execution.pruefe_sl_tp


def berechne_signale(bars, config=CONFIG):
    strategy = get_strategy(config)
    return strategy.build_signals(bars, config)


def confluence_score(signale, config=CONFIG):
    strategy = get_strategy(config)
    return strategy.score_signals(signale)


def sterne(score, total=None, config=CONFIG):
    strategy = get_strategy(config)
    if total is None:
        return strategy.stars(score)
    return strategy.stars(score, total)


def signal_emoji(kauf, verkauf, config=CONFIG):
    strategy = get_strategy(config)
    return strategy.summary_signal(kauf, verkauf)


def erkenne_markt_regime(bars_dict, config=CONFIG):
    regime = []
    empfehlungen = []
    warnungen = []

    if bars_dict.get("SPY"):
        spy_trend = berechne_trend(bars_dict["SPY"])
        spy_rsi = berechne_rsi(bars_dict["SPY"], config["strategy"]["rsi_period"])
        if spy_trend and spy_rsi < 65:
            regime.append("📈 Bullish Aktienmarkt")
            empfehlungen.append("✅ Gutes Umfeld für Aktien-Käufe")
        elif not spy_trend:
            regime.append("📉 Bearish Aktienmarkt")
            empfehlungen.append("⚠️ Vorsicht bei Aktien-Käufen")

    if bars_dict.get("UUP"):
        uup_kurs = bars_dict["UUP"][-1].close
        uup_ma = berechne_ma(bars_dict["UUP"], 20)
        if uup_kurs > uup_ma:
            regime.append("💵 USD stark")
            empfehlungen.append("⚠️ USD stark → Druck auf Gold & BTC")
        else:
            regime.append("💵 USD schwach")
            empfehlungen.append("✅ USD schwach → Rückenwind für Gold & BTC")

    if bars_dict.get("GLD") and berechne_trend(bars_dict["GLD"]):
        regime.append("🥇 Gold im Aufwärtstrend")
        empfehlungen.append("⚠️ Gold steigt → Risikoaversion im Markt")

    if bars_dict.get("USO") and berechne_trend(bars_dict["USO"]) and berechne_rsi(bars_dict["USO"]) > 60:
        regime.append("🛢️ Öl überkauft")
        empfehlungen.append("⚠️ Öl stark → Inflationsdruck steigt")

    if bars_dict.get("BTC/USD"):
        if berechne_trend(bars_dict["BTC/USD"]):
            regime.append("₿ BTC im Aufwärtstrend")
            empfehlungen.append("✅ BTC bullish → Altcoins könnten folgen")
        else:
            regime.append("₿ BTC im Abwärtstrend")
            empfehlungen.append("⚠️ BTC bearish → Vorsicht bei Altcoins")

    if bars_dict.get("SPY") and bars_dict.get("BTC/USD"):
        korr = berechne_korrelation(bars_dict["SPY"], bars_dict["BTC/USD"])
        if korr < -0.5:
            warnungen.append(f"🚨 BTC läuft gegen S&P500 (Korr: {korr})")
        elif korr > 0.8:
            warnungen.append(f"📊 BTC & S&P500 sehr synchron (Korr: {korr})")

    if bars_dict.get("GLD") and bars_dict.get("UUP"):
        korr = berechne_korrelation(bars_dict["GLD"], bars_dict["UUP"])
        if korr > 0.4:
            warnungen.append(f"🚨 Gold & USD steigen zusammen (Korr: {korr})")

    if bars_dict.get("USO") and bars_dict.get("GLD"):
        korr = berechne_korrelation(bars_dict["USO"], bars_dict["GLD"])
        if korr > 0.6:
            warnungen.append(f"⚠️ Öl & Gold korrelieren stark (Korr: {korr})")

    return regime, empfehlungen, warnungen


def korrelations_analyse(bars_dict):
    paare = [
        ("SPY", "BTC/USD", "S&P500 ↔ BTC"),
        ("SPY", "GLD", "S&P500 ↔ Gold"),
        ("GLD", "UUP", "Gold ↔ USD"),
        ("UUP", "BTC/USD", "USD ↔ BTC"),
        ("USO", "GLD", "Öl ↔ Gold"),
        ("USO", "SPY", "Öl ↔ S&P500"),
        ("BTC/USD", "ETH/USD", "BTC ↔ ETH"),
        ("QQQ", "BTC/USD", "Nasdaq ↔ BTC"),
    ]
    ergebnisse = []
    for sym1, sym2, label in paare:
        if bars_dict.get(sym1) and bars_dict.get(sym2):
            korr = berechne_korrelation(bars_dict[sym1], bars_dict[sym2])
            ergebnisse.append({"label": label, "korrelation": korr, "beschreibung": korrelation_label(korr)})
    return ergebnisse


def baue_scan_result(symbol, asset_type, strategy_name, analyse, sentiment, sentiment_score, grund, headlines, position, action):
    return {
        "symbol": symbol,
        "asset_type": asset_type,
        "strategy": strategy_name,
        "action": action,
        "kurs": round(analyse["kurs"], 2),
        "kauf_score": analyse["kauf_score"],
        "verkauf_score": analyse["verkauf_score"],
        "summary_signal": analyse["summary_signal"],
        "position_open": position,
        "sentiment": {
            "label": sentiment,
            "score": sentiment_score,
            "grund": grund,
            "headlines": headlines[:3],
        },
        "signale": {
            name: {"signal": signal, "detail": detail}
            for name, (signal, detail) in analyse["signale"].items()
        },
    }


def baue_run_metrics(kauf_aktien, kauf_krypto, verkauf_aktien, verkauf_krypto, positionen, scan_results):
    return {
        "buy_signals": len(kauf_aktien) + len(kauf_krypto),
        "sell_signals": len(verkauf_aktien) + len(verkauf_krypto),
        "open_positions": len(positionen),
        "scanned_assets": len(scan_results),
    }


def scan(symbole, krypto=False, config=CONFIG):
    starke_kaufsignale = []
    starke_verkaufsignale = []
    news_zusammenfassung = []
    scan_results = []
    strategy = get_strategy(config)

    typ = "KRYPTO" if krypto else "AKTIEN"
    print(f"\n{'=' * 45}")
    print(f"{typ} SCAN – {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 45}")

    for symbol in symbole:
        print(f"\n📊 {symbol}")
        bars = get_kursdaten(symbol, krypto)
        if bars is None or len(bars) < 50:
            print("   ⚠️ Nicht genug Daten")
            continue

        analyse = strategy.evaluate(bars, config)
        signale = analyse["signale"]
        kurs = analyse["kurs"]
        kauf_score = analyse["kauf_score"]
        verkauf_score = analyse["verkauf_score"]
        position, einstieg, qty = hat_position(symbol)

        headlines = get_news(symbol, config)
        sentiment, sentiment_score, grund, _ = analysiere_sentiment(symbol, headlines)
        print(f"   Kurs: ${kurs:.2f} | 🟢 {kauf_score}/7 | 📰 {sentiment} ({sentiment_score})")
        action = "HOLD"

        if headlines:
            news_zusammenfassung.append({
                "symbol": symbol,
                "sentiment": sentiment,
                "score": sentiment_score,
                "grund": grund,
                "headlines": headlines[:3],
            })

        if position:
            aktion, pct = pruefe_sl_tp(kurs, einstieg, config)
            if aktion == "verkaufen":
                verkauft, fehler = order_verkaufen(symbol, qty, config)
                grund_sl = "🛑 Stop Loss" if pct < 0 else "🎯 Take Profit"
                if verkauft:
                    starke_verkaufsignale.append(f"🔴 {symbol}: {grund_sl} ({pct:+.1f}%)")
                    action = "SELL_SLTP"
                else:
                    starke_verkaufsignale.append(
                        f"⚠️ <b>{symbol}</b>: Verkauf fehlgeschlagen\n"
                        f"   Grund: {fehler}\n"
                        f"   Anlass: {grund_sl} ({pct:+.1f}%)"
                    )
                    action = "SELL_FAILED"
            elif strategy.should_sell(kauf_score, verkauf_score):
                verkauft, fehler = order_verkaufen(symbol, qty, config)
                if verkauft:
                    starke_verkaufsignale.append(
                        f"🔴 <b>{symbol}</b> – {verkauf_score} VERKAUFEN {sterne(verkauf_score, config=config)}\n"
                        f"   💰 ${kurs:.2f} | 📰 {sentiment} ({sentiment_score}/100)\n"
                    )
                    action = "SELL_SIGNAL"
                else:
                    starke_verkaufsignale.append(
                        f"⚠️ <b>{symbol}</b>: Verkauf fehlgeschlagen\n"
                        f"   Grund: {fehler}\n"
                        f"   Signal: {verkauf_score} VERKAUFEN {sterne(verkauf_score, config=config)}\n"
                    )
                    action = "SELL_FAILED"
            elif sentiment == "NEGATIV" and sentiment_score < 25:
                print("   ⚠️ Sehr negative News für bestehende Position!")
                starke_verkaufsignale.append(
                    f"⚠️ <b>{symbol}</b>: Sehr negative News!\n"
                    f"   📰 Score: {sentiment_score}/100 – {grund}"
                )
                action = "WARN_NEGATIVE_NEWS"
            else:
                print(f"   ⏳ HALTEN | G&V: {pct:+.1f}%")
                action = "HOLD_POSITION"
        elif strategy.should_buy(kauf_score, verkauf_score) and sentiment in ["POSITIV", "NEUTRAL"]:
            gekauft, sl, tp, fehler = order_kaufen(symbol, kurs, config)
            if gekauft:
                zeile = (
                    f"🟢 <b>{symbol}</b> – {kauf_score} KAUFEN {sterne(kauf_score, config=config)}\n"
                    f"   💰 ${kurs:.2f} | SL: ${sl} | TP: ${tp}\n"
                    f"   📰 News: {sentiment} ({sentiment_score}/100) – {grund}\n"
                )
                for ind, (sig, detail) in signale.items():
                    emoji = "✅" if sig == "KAUFEN" else "❌" if sig == "VERKAUFEN" else "➖"
                    zeile += f"   {emoji} {ind}: {sig} ({detail})\n"
                starke_kaufsignale.append(zeile)
                action = "BUY_SIGNAL"
            else:
                starke_verkaufsignale.append(
                    f"⚠️ <b>{symbol}</b>: Kauf fehlgeschlagen\n"
                    f"   Grund: {fehler}\n"
                    f"   Signal: {kauf_score} KAUFEN {sterne(kauf_score, config=config)}\n"
                    f"   💰 ${kurs:.2f} | 📰 {sentiment} ({sentiment_score}/100) – {grund}"
                )
                action = "BUY_FAILED"
        elif strategy.should_buy(kauf_score, verkauf_score) and sentiment == "NEGATIV":
            print(f"   🚫 Kaufsignal blockiert – Negative News ({sentiment_score}/100): {grund}")
            starke_verkaufsignale.append(
                f"🚫 <b>{symbol}</b>: Kaufsignal blockiert\n"
                f"   📰 Negative News ({sentiment_score}/100): {grund}"
            )
            action = "BLOCKED_NEGATIVE_NEWS"
        else:
            print("   ⏳ Kein starkes Signal")
            action = "NO_SIGNAL"

        scan_results.append(
            baue_scan_result(
                symbol=symbol,
                asset_type="crypto" if krypto else "stock",
                strategy_name=strategy.name,
                analyse=analyse,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                grund=grund,
                headlines=headlines,
                position=position,
                action=action,
            )
        )

        time.sleep(0.5)

    return starke_kaufsignale, starke_verkaufsignale, news_zusammenfassung, scan_results


def markt_uebersicht(config=CONFIG):
    strategy = get_strategy(config)
    print("\n" + "=" * 45)
    print(f"🌍 MARKTÜBERSICHT – {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 45)

    markt_liste = []
    bars_dict = {}
    for symbol, meta in config["market_assets"].items():
        bars_dict[symbol] = get_kursdaten(symbol, meta["krypto"])
    bars_dict["ETH/USD"] = get_kursdaten("ETH/USD", krypto=True)

    regime, empfehlungen, warnungen = erkenne_markt_regime(bars_dict, config)
    korrelationen = korrelations_analyse(bars_dict)

    nachricht = f"🌍 <b>MARKTÜBERSICHT</b> – {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    nachricht += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    abschnitte = {
        "📈 BÖRSENINDIZES": ["SPY", "QQQ", "DIA", "IWM"],
        "🛍️ ROHSTOFFE & FX": ["GLD", "USO", "UUP"],
        "₿ KRYPTO": ["BTC/USD"],
    }

    for titel, symbole in abschnitte.items():
        nachricht += f"\n<b>{titel}</b>\n"
        for symbol in symbole:
            meta = config["market_assets"][symbol]
            bars = bars_dict.get(symbol)
            if bars is None or len(bars) < 50:
                nachricht += f"{meta['emoji']} {meta['name']}: ⚠️ Keine Daten\n"
                continue

            kurs = bars[-1].close
            rsi = berechne_rsi(bars, config["strategy"]["rsi_period"])
            analyse = strategy.evaluate(bars, config)
            kauf_score = analyse["kauf_score"]
            verkauf_score = analyse["verkauf_score"]
            support, resistance = berechne_support_resistance(bars)
            trend = berechne_trend(bars)
            sig = analyse["summary_signal"]

            print(f"{meta['emoji']} {meta['name']}: ${kurs:.2f} | RSI {rsi} | {sig}")
            nachricht += (
                f"{meta['emoji']} <b>{meta['name']}</b>: ${kurs:.2f}\n"
                f"   RSI: {rsi} | Trend: {'📈' if trend else '📉'} | {sig}\n"
                f"   🛡️ Support: ${support} | 🎯 Resist: ${resistance}\n"
            )
            markt_liste.append({
                "symbol": symbol,
                "name": meta["name"],
                "emoji": meta["emoji"],
                "kurs": str(round(kurs, 2)),
                "rsi": str(rsi),
                "trend": "📈" if trend else "📉",
                "signal": sig,
                "support": str(support),
                "resistance": str(resistance),
            })
        nachricht += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    nachricht += "\n🌡️ <b>MARKTREGIME</b>\n"
    for item in regime:
        nachricht += f"  {item}\n"

    if warnungen:
        nachricht += "\n🚨 <b>WARNUNGEN</b>\n"
        for item in warnungen:
            nachricht += f"  {item}\n"

    nachricht += "\n💡 <b>EMPFEHLUNGEN</b>\n"
    for item in empfehlungen:
        nachricht += f"  {item}\n"

    nachricht += "\n🔗 <b>KORRELATIONEN</b>\n"
    for item in korrelationen:
        nachricht += f"  {item['label']}: {item['korrelation']} {item['beschreibung']}\n"

    sende_telegram(nachricht, config)
    print("📱 Marktübersicht gesendet!")
    return markt_liste, regime, empfehlungen, warnungen, korrelationen


def main(config=None):
    runtime_config = config or load_config()
    run_id = uuid4().hex
    kauf_aktien, verkauf_aktien, news_aktien, scan_aktien = scan(runtime_config["universes"]["stocks"], False, runtime_config)
    kauf_krypto, verkauf_krypto, news_krypto, scan_krypto = scan(runtime_config["universes"]["crypto"], True, runtime_config)
    markt_liste, regime, empfehlungen, warnungen, korrelationen = markt_uebersicht(runtime_config)
    account = trading_client.get_account()

    nachricht = f"📊 <b>SCAN ABGESCHLOSSEN</b> – {datetime.now().strftime('%H:%M:%S')}\n\n"
    if kauf_aktien:
        nachricht += "🟢 <b>STARKE KAUFSIGNALE – AKTIEN</b>\n" + "\n".join(kauf_aktien)
    if kauf_krypto:
        nachricht += "\n🟢 <b>STARKE KAUFSIGNALE – KRYPTO</b>\n" + "\n".join(kauf_krypto)
    if verkauf_aktien or verkauf_krypto:
        nachricht += "\n🔴 <b>VERKAUFS & WARNUNGEN</b>\n" + "\n".join(verkauf_aktien + verkauf_krypto)
    if not kauf_aktien and not kauf_krypto and not verkauf_aktien and not verkauf_krypto:
        nachricht += "⏳ Keine starken Signale gefunden\n"

    nachricht += f"\n💰 Kontostand: ${float(account.cash):,.2f}"
    nachricht += f"\n📈 Portfolio: ${float(account.portfolio_value):,.2f}"

    positionen = trading_client.get_all_positions()
    if positionen:
        nachricht += "\n\n📦 <b>MEIN BESTAND</b>\n"
        for pos in positionen:
            pl = float(pos.unrealized_pl)
            pl_pct = float(pos.unrealized_plpc) * 100
            pl_emoji = "🟢" if pl >= 0 else "🔴"
            nachricht += (
                f"{pl_emoji} <b>{pos.symbol}</b>: {pos.qty} Stk.\n"
                f"   Ø Kaufpreis: ${float(pos.avg_entry_price):.2f} | Kurs: ${float(pos.current_price):.2f}\n"
                f"   G&V: {pl_emoji} ${pl:+.2f} ({pl_pct:+.2f}%)\n"
            )
    else:
        nachricht += "\n\n📦 <b>MEIN BESTAND</b>\nKeine offenen Positionen"

    print("\n" + "=" * 45)
    print("TELEGRAM ZUSAMMENFASSUNG:")
    print(nachricht)
    print("=" * 45)

    sende_telegram(nachricht, runtime_config)
    scan_results = scan_aktien + scan_krypto
    run_metrics = baue_run_metrics(kauf_aktien, kauf_krypto, verkauf_aktien, verkauf_krypto, positionen, scan_results)
    ergebnisse = {
        "run_id": run_id,
        "zeitpunkt": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "portfolio": str(account.portfolio_value),
        "kontostand": str(account.cash),
        "kaufsignale": kauf_aktien + kauf_krypto,
        "verkaufsignale": verkauf_aktien + verkauf_krypto,
        "positionen": baue_positionen_liste(positionen),
        "markt": markt_liste,
        "regime": regime,
        "empfehlungen": empfehlungen,
        "warnungen": warnungen,
        "korrelationen": korrelationen,
        "news": news_aktien + news_krypto,
        "scan_results": scan_results,
        "metrics": run_metrics,
        "config": {
            "trading_mode": runtime_config["trading_mode"],
            "strategy": runtime_config["strategy"]["name"],
        },
    }
    speichere_ergebnisse(ergebnisse, runtime_config)
    speichere_run_history({
        "run_id": run_id,
        "zeitpunkt": ergebnisse["zeitpunkt"],
        "portfolio": ergebnisse["portfolio"],
        "kontostand": ergebnisse["kontostand"],
        "metrics": run_metrics,
        "config": ergebnisse["config"],
        "scan_results": scan_results,
    })


if __name__ == "__main__":
    main()
