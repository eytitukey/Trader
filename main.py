import os
import requests
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import json

API_KEY = os.environ.get("ALPACA_KEY")
SECRET_KEY = os.environ.get("ALPACA_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT")

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
crypto_data_client = CryptoHistoricalDataClient(API_KEY, SECRET_KEY)

AKTIEN = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
    "META", "TSLA", "AVGO", "JPM", "LLY",
    "V", "UNH", "XOM", "MA", "COST",
    "HD", "PG", "JNJ", "NFLX", "ABBV",
    "BAC", "CRM", "ORCL", "CVX", "MRK",
    "AMD", "KO", "PEP", "TMO", "ACN",
    "CSCO", "LIN", "MCD", "ABT", "IBM",
    "GE", "NOW", "ISRG", "GS", "TXN",
    "QCOM", "INTU", "SPGI", "BKNG", "RTX",
    "CAT", "DHR", "AMGN", "BLK", "SPY"
]

KRYPTOS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD",
    "LINK/USD", "LTC/USD", "UNI/USD", "AAVE/USD", "SHIB/USD",
    "BCH/USD", "MATIC/USD", "CRV/USD", "GRT/USD", "BAT/USD",
    "MKR/USD", "DOT/USD", "XTZ/USD", "SUSHI/USD", "YFI/USD",
    "ALGO/USD", "ATOM/USD", "FIL/USD", "NEAR/USD", "APE/USD",
    "SAND/USD", "MANA/USD", "AXS/USD", "CHZ/USD", "ENJ/USD",
    "COMP/USD", "SNX/USD", "OP/USD", "ARB/USD", "LDO/USD",
    "IMX/USD", "1INCH/USD", "RPL/USD", "ZRX/USD", "BAL/USD",
    "UMA/USD", "OCEAN/USD", "ANKR/USD", "STORJ/USD", "RNDR/USD",
    "NMR/USD", "RLC/USD", "BAND/USD", "CTSI/USD", "SKL/USD"
]

MARKT_ASSETS = {
    "SPY":     ("📈", "S&P 500",      False),
    "QQQ":     ("💻", "Nasdaq 100",   False),
    "DIA":     ("🏦", "Dow Jones",    False),
    "IWM":     ("🏢", "Russell 2000", False),
    "GLD":     ("🥇", "Gold",         False),
    "USO":     ("🛢️", "Öl (WTI)",    False),
    "UUP":     ("💵", "USD Index",    False),
    "BTC/USD": ("₿",  "Bitcoin",      True),
}

MENGE = 1
RSI_PERIODE = 14
RSI_KAUFEN = 35
RSI_VERKAUFEN = 65
STOP_LOSS = 0.03
TAKE_PROFIT = 0.06

# ─────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────
def sende_telegram(nachricht):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": nachricht, "parse_mode": "HTML"}
        requests.post(url, data=data)
    except:
        print("⚠️ Telegram Fehler")

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────
def speichere_ergebnisse(ergebnisse):
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(ergebnisse, f, ensure_ascii=False)

# ─────────────────────────────────────────
# KURSDATEN
# ─────────────────────────────────────────
def get_kursdaten(symbol, krypto=False):
    try:
        if krypto:
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=120),
                end=datetime.now() - timedelta(days=1)
            )
            bars = crypto_data_client.get_crypto_bars(request)
        else:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=120),
                end=datetime.now() - timedelta(days=1)
            )
            bars = data_client.get_stock_bars(request)
        return bars[symbol]
    except:
        return None

# ─────────────────────────────────────────
# INDIKATOREN
# ─────────────────────────────────────────
def berechne_rsi(bars, periode=14):
    preise = [bar.close for bar in bars]
    gewinne, verluste = [], []
    for i in range(1, len(preise)):
        diff = preise[i] - preise[i-1]
        if diff > 0:
            gewinne.append(diff); verluste.append(0)
        else:
            gewinne.append(0); verluste.append(abs(diff))
    avg_g = sum(gewinne[-periode:]) / periode
    avg_v = sum(verluste[-periode:]) / periode
    if avg_v == 0:
        return 100
    return round(100 - (100 / (1 + avg_g / avg_v)), 2)

def berechne_ma(bars, tage):
    preise = [bar.close for bar in bars[-tage:]]
    return sum(preise) / len(preise)

def berechne_macd(bars):
    preise = [bar.close for bar in bars]
    def ema(daten, periode):
        k = 2 / (periode + 1)
        ema_wert = daten[0]
        for preis in daten[1:]:
            ema_wert = preis * k + ema_wert * (1 - k)
        return ema_wert
    ema12 = ema(preise, 12)
    ema26 = ema(preise, 26)
    macd_linie = ema12 - ema26
    signal_linie = ema(preise[-9:], 9)
    return round(macd_linie, 4), round(signal_linie, 4)

def berechne_bollinger(bars, periode=20):
    preise = [bar.close for bar in bars[-periode:]]
    ma = sum(preise) / periode
    std = (sum((p - ma) ** 2 for p in preise) / periode) ** 0.5
    return round(ma - 2 * std, 2), round(ma, 2), round(ma + 2 * std, 2)

def berechne_stochastic(bars, periode=14):
    relevante = bars[-periode:]
    hoechst = max(bar.high for bar in relevante)
    tiefst = min(bar.low for bar in relevante)
    aktuell = bars[-1].close
    if hoechst == tiefst:
        return 50
    return round((aktuell - tiefst) / (hoechst - tiefst) * 100, 2)

def berechne_williams(bars, periode=14):
    relevante = bars[-periode:]
    hoechst = max(bar.high for bar in relevante)
    tiefst = min(bar.low for bar in relevante)
    aktuell = bars[-1].close
    if hoechst == tiefst:
        return -50
    return round((hoechst - aktuell) / (hoechst - tiefst) * -100, 2)

def berechne_volume_signal(bars):
    volumes = [bar.volume for bar in bars[-20:]]
    avg_vol = sum(volumes) / len(volumes)
    aktuell_vol = bars[-1].volume
    aktuell_kurs = bars[-1].close
    vorher_kurs = bars[-2].close
    kurs_steigt = aktuell_kurs > vorher_kurs
    vol_hoch = aktuell_vol > avg_vol * 1.2
    if kurs_steigt and vol_hoch:
        return "KAUFEN"
    elif not kurs_steigt and vol_hoch:
        return "VERKAUFEN"
    return "NEUTRAL"

def berechne_trend(bars):
    ma10 = berechne_ma(bars, 10)
    ma20 = berechne_ma(bars, 20)
    ma50 = berechne_ma(bars, 50)
    return ma10 > ma20 > ma50

def berechne_support_resistance(bars, periode=20):
    recent = bars[-periode:]
    support = round(min(bar.low for bar in recent), 2)
    resistance = round(max(bar.high for bar in recent), 2)
    return support, resistance

# ─────────────────────────────────────────
# KORRELATION
# ─────────────────────────────────────────
def berechne_korrelation(bars1, bars2, tage=30):
    try:
        preise1 = [bar.close for bar in bars1[-tage:]]
        preise2 = [bar.close for bar in bars2[-tage:]]
        n = min(len(preise1), len(preise2))
        preise1 = preise1[-n:]
        preise2 = preise2[-n:]
        mean1 = sum(preise1) / n
        mean2 = sum(preise2) / n
        zaehler = sum((preise1[i] - mean1) * (preise2[i] - mean2) for i in range(n))
        nenner1 = (sum((p - mean1) ** 2 for p in preise1)) ** 0.5
        nenner2 = (sum((p - mean2) ** 2 for p in preise2)) ** 0.5
        if nenner1 * nenner2 == 0:
            return 0
        return round(zaehler / (nenner1 * nenner2), 2)
    except:
        return 0

def korrelation_label(k):
    if k >= 0.7:   return "🟢 Stark positiv"
    if k >= 0.4:   return "🟡 Mittel positiv"
    if k >= 0.1:   return "⬜ Schwach positiv"
    if k >= -0.1:  return "⬜ Neutral"
    if k >= -0.4:  return "🟡 Schwach negativ"
    if k >= -0.7:  return "🟠 Mittel negativ"
    return "🔴 Stark negativ"

def erkenne_markt_regime(bars_dict):
    regime = []
    empfehlungen = []
    warnungen = []

    # S&P500 Trend
    if "SPY" in bars_dict and bars_dict["SPY"]:
        spy_trend = berechne_trend(bars_dict["SPY"])
        spy_rsi = berechne_rsi(bars_dict["SPY"])
        if spy_trend and spy_rsi < 65:
            regime.append("📈 Bullish Aktienmarkt")
            empfehlungen.append("✅ Gutes Umfeld für Aktien-Käufe")
        elif not spy_trend:
            regime.append("📉 Bearish Aktienmarkt")
            empfehlungen.append("⚠️ Vorsicht bei Aktien-Käufen")

    # USD Stärke
    if "UUP" in bars_dict and bars_dict["UUP"]:
        uup_kurs = bars_dict["UUP"][-1].close
        uup_ma = berechne_ma(bars_dict["UUP"], 20)
        usd_stark = uup_kurs > uup_ma
        if usd_stark:
            regime.append("💵 USD stark")
            empfehlungen.append("⚠️ USD stark → Druck auf Gold & BTC")
        else:
            regime.append("💵 USD schwach")
            empfehlungen.append("✅ USD schwach → Rückenwind für Gold & BTC")

    # Gold Signal
    if "GLD" in bars_dict and bars_dict["GLD"]:
        gld_trend = berechne_trend(bars_dict["GLD"])
        if gld_trend:
            regime.append("🥇 Gold im Aufwärtstrend")
            empfehlungen.append("⚠️ Gold steigt → Risikoaversion im Markt")

    # Öl Signal
    if "USO" in bars_dict and bars_dict["USO"]:
        uso_trend = berechne_trend(bars_dict["USO"])
        uso_rsi = berechne_rsi(bars_dict["USO"])
        if uso_trend and uso_rsi > 60:
            regime.append("🛢️ Öl überkauft")
            empfehlungen.append("⚠️ Öl stark → Inflationsdruck steigt")

    # BTC Dominanz
    if "BTC/USD" in bars_dict and bars_dict["BTC/USD"]:
        btc_trend = berechne_trend(bars_dict["BTC/USD"])
        if btc_trend:
            regime.append("₿ BTC im Aufwärtstrend")
            empfehlungen.append("✅ BTC bullish → Altcoins könnten folgen")
        else:
            regime.append("₿ BTC im Abwärtstrend")
            empfehlungen.append("⚠️ BTC bearish → Vorsicht bei Altcoins")

    # Korrelations-Warnungen
    if "SPY" in bars_dict and "BTC/USD" in bars_dict and bars_dict["SPY"] and bars_dict["BTC/USD"]:
        korr = berechne_korrelation(bars_dict["SPY"], bars_dict["BTC/USD"])
        if korr < -0.5:
            warnungen.append(f"🚨 BTC läuft gegen S&P500 (Korr: {korr}) – ungewöhnlich!")
        elif korr > 0.8:
            warnungen.append(f"📊 BTC & S&P500 sehr synchron (Korr: {korr})")

    if "GLD" in bars_dict and "UUP" in bars_dict and bars_dict["GLD"] and bars_dict["UUP"]:
        korr = berechne_korrelation(bars_dict["GLD"], bars_dict["UUP"])
        if korr > 0.4:
            warnungen.append(f"🚨 Gold & USD steigen zusammen (Korr: {korr}) – Krisenzeichen!")

    if "USO" in bars_dict and "GLD" in bars_dict and bars_dict["USO"] and bars_dict["GLD"]:
        korr = berechne_korrelation(bars_dict["USO"], bars_dict["GLD"])
        if korr > 0.6:
            warnungen.append(f"⚠️ Öl & Gold korrelieren stark (Korr: {korr}) – Inflationsdruck!")

    return regime, empfehlungen, warnungen

def korrelations_analyse(bars_dict):
    paare = [
        ("SPY",     "BTC/USD", "S&P500 ↔ BTC"),
        ("SPY",     "GLD",     "S&P500 ↔ Gold"),
        ("GLD",     "UUP",     "Gold ↔ USD"),
        ("UUP",     "BTC/USD", "USD ↔ BTC"),
        ("USO",     "GLD",     "Öl ↔ Gold"),
        ("USO",     "SPY",     "Öl ↔ S&P500"),
        ("BTC/USD", "ETH/USD", "BTC ↔ ETH"),
        ("QQQ",     "BTC/USD", "Nasdaq ↔ BTC"),
    ]

    ergebnisse = []
    for sym1, sym2, label in paare:
        if sym1 in bars_dict and sym2 in bars_dict:
            if bars_dict[sym1] and bars_dict[sym2]:
                k = berechne_korrelation(bars_dict[sym1], bars_dict[sym2])
                ergebnisse.append({
                    "label": label,
                    "korrelation": k,
                    "beschreibung": korrelation_label(k)
                })
    return ergebnisse

# ─────────────────────────────────────────
# SIGNAL BERECHNUNG
# ─────────────────────────────────────────
def berechne_signale(bars):
    kurs = bars[-1].close
    signale = {}

    rsi = berechne_rsi(bars, RSI_PERIODE)
    if rsi < RSI_KAUFEN:
        signale["RSI"] = ("KAUFEN", f"RSI={rsi}")
    elif rsi > RSI_VERKAUFEN:
        signale["RSI"] = ("VERKAUFEN", f"RSI={rsi}")
    else:
        signale["RSI"] = ("NEUTRAL", f"RSI={rsi}")

    trend = berechne_trend(bars)
    if trend:
        signale["MA"] = ("KAUFEN", "MA10>MA20>MA50")
    else:
        signale["MA"] = ("VERKAUFEN", "Kein Aufwärtstrend")

    macd, signal = berechne_macd(bars)
    if macd > signal:
        signale["MACD"] = ("KAUFEN", f"MACD={macd}")
    else:
        signale["MACD"] = ("VERKAUFEN", f"MACD={macd}")

    bb_low, bb_mid, bb_high = berechne_bollinger(bars)
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

def confluence_score(signale):
    kaufen = sum(1 for s, _ in signale.values() if s == "KAUFEN")
    verkaufen = sum(1 for s, _ in signale.values() if s == "VERKAUFEN")
    return kaufen, verkaufen

def sterne(score, total=7):
    filled = round(score / total * 5)
    return "⭐" * filled + "☆" * (5 - filled)

def signal_emoji(kauf, verkauf):
    if kauf >= 5:    return "🟢 KAUFEN"
    if verkauf >= 5: return "🔴 VERKAUFEN"
    if kauf >= 3:    return "🟡 NEUTRAL+"
    return "⏳ NEUTRAL"

# ─────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────
def hat_position(symbol):
    try:
        pos = trading_client.get_open_position(symbol)
        return True, float(pos.avg_entry_price)
    except:
        return False, 0

def kaufen(symbol, kurs):
    sl = round(kurs * (1 - STOP_LOSS), 2)
    tp = round(kurs * (1 + TAKE_PROFIT), 2)
    order = MarketOrderRequest(
        symbol=symbol, qty=MENGE,
        side=OrderSide.BUY, time_in_force=TimeInForce.GTC
    )
    trading_client.submit_order(order)
    print(f"   ✅ GEKAUFT @ ${kurs:.2f}")
    return sl, tp

def verkaufen(symbol):
    order = MarketOrderRequest(
        symbol=symbol, qty=MENGE,
        side=OrderSide.SELL, time_in_force=TimeInForce.GTC
    )
    trading_client.submit_order(order)
    print(f"   🔴 VERKAUFT")

def pruefe_sl_tp(symbol, kurs, einstieg):
    pct = (kurs - einstieg) / einstieg * 100
    if pct <= -STOP_LOSS * 100:
        return "verkaufen", pct
    if pct >= TAKE_PROFIT * 100:
        return "verkaufen", pct
    return "halten", pct

# ─────────────────────────────────────────
# HAUPT SCAN
# ─────────────────────────────────────────
def scan(symbole, krypto=False):
    starke_kaufsignale = []
    starke_verkaufsignale = []

    typ = "KRYPTO" if krypto else "AKTIEN"
    print(f"\n{'='*45}")
    print(f"{typ} SCAN – {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*45}")

    for symbol in symbole:
        print(f"\n📊 {symbol}")
        bars = get_kursdaten(symbol, krypto)

        if bars is None or len(bars) < 50:
            print(f"   ⚠️ Nicht genug Daten")
            continue

        signale, kurs = berechne_signale(bars)
        kauf_score, verkauf_score = confluence_score(signale)
        position, einstieg = hat_position(symbol)

        print(f"   Kurs: ${kurs:.2f} | 🟢 {kauf_score}/7 Kauf | 🔴 {verkauf_score}/7 Verkauf")

        if position:
            aktion, pct = pruefe_sl_tp(symbol, kurs, einstieg)
            if aktion == "verkaufen":
                verkaufen(symbol)
                grund = "🛑 Stop Loss" if pct < 0 else "🎯 Take Profit"
                starke_verkaufsignale.append(f"🔴 {symbol}: {grund} ({pct:+.1f}%)")
            else:
                print(f"   ⏳ HALTEN | G&V: {pct:+.1f}%")

        elif kauf_score >= 5:
            sl, tp = kaufen(symbol, kurs)
            zeile = (
                f"🟢 <b>{symbol}</b> – {kauf_score}/7 KAUFEN {sterne(kauf_score)}\n"
                f"   💰 ${kurs:.2f} | SL: ${sl} | TP: ${tp}\n"
            )
            for ind, (sig, detail) in signale.items():
                emoji = "✅" if sig == "KAUFEN" else "❌" if sig == "VERKAUFEN" else "➖"
                zeile += f"   {emoji} {ind}: {sig} ({detail})\n"
            starke_kaufsignale.append(zeile)

        elif verkauf_score >= 5 and position:
            verkaufen(symbol)
            zeile = (
                f"🔴 <b>{symbol}</b> – {verkauf_score}/7 VERKAUFEN {sterne(verkauf_score)}\n"
                f"   💰 ${kurs:.2f}\n"
            )
            starke_verkaufsignale.append(zeile)

        else:
            print(f"   ⏳ Kein starkes Signal")

        time.sleep(0.3)

    return starke_kaufsignale, starke_verkaufsignale

# ─────────────────────────────────────────
# MARKTÜBERSICHT
# ─────────────────────────────────────────
def markt_uebersicht():
    print("\n" + "="*45)
    print(f"🌍 MARKTÜBERSICHT – {datetime.now().strftime('%H:%M:%S')}")
    print("="*45)

    markt_liste = []
    bars_dict = {}

    # Alle Markt-Kursdaten laden
    for symbol, (emoji, name, krypto) in MARKT_ASSETS.items():
        bars = get_kursdaten(symbol, krypto)
        bars_dict[symbol] = bars

    # Für Korrelation ETH auch laden
    bars_dict["ETH/USD"] = get_kursdaten("ETH/USD", krypto=True)

    # Markt Regime & Korrelationen berechnen
    regime, empfehlungen, warnungen = erkenne_markt_regime(bars_dict)
    korrelationen = korrelations_analyse(bars_dict)

    # Telegram Marktübersicht
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
            emoji, name, krypto = MARKT_ASSETS[symbol]
            bars = bars_dict.get(symbol)

            if bars is None or len(bars) < 50:
                nachricht += f"{emoji} {name}: ⚠️ Keine Daten\n"
                continue

            kurs = bars[-1].close
            rsi = berechne_rsi(bars, RSI_PERIODE)
            signale, _ = berechne_signale(bars)
            kauf_score, verkauf_score = confluence_score(signale)
            support, resistance = berechne_support_resistance(bars)
            trend = berechne_trend(bars)
            sig = signal_emoji(kauf_score, verkauf_score)

            print(f"{emoji} {name}: ${kurs:.2f} | RSI {rsi} | {sig}")

            nachricht += (
                f"{emoji} <b>{name}</b>: ${kurs:.2f}\n"
                f"   RSI: {rsi} | Trend: {'📈' if trend else '📉'} | {sig}\n"
                f"   🛡️ Support: ${support} | 🎯 Resist: ${resistance}\n"
            )

            markt_liste.append({
                "symbol": symbol,
                "name": name,
                "emoji": emoji,
                "kurs": str(round(kurs, 2)),
                "rsi": str(rsi),
                "trend": "📈" if trend else "📉",
                "signal": sig,
                "support": str(support),
                "resistance": str(resistance)
            })

        nachricht += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    # Markt Regime
    nachricht += "\n🌡️ <b>MARKTREGIME</b>\n"
    for r in regime:
        nachricht += f"  {r}\n"

    # Warnungen
    if warnungen:
        nachricht += "\n🚨 <b>WARNUNGEN</b>\n"
        for w in warnungen:
            nachricht += f"  {w}\n"

    # Empfehlungen
    nachricht += "\n💡 <b>EMPFEHLUNGEN</b>\n"
    for e in empfehlungen:
        nachricht += f"  {e}\n"

    # Korrelationen
    nachricht += "\n🔗 <b>KORRELATIONEN (30 Tage)</b>\n"
    for k in korrelationen:
        nachricht += f"  {k['label']}: {k['korrelation']} {k['beschreibung']}\n"

    sende_telegram(nachricht)
    print("📱 Marktübersicht gesendet!")

    return markt_liste, regime, empfehlungen, warnungen, korrelationen

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    kauf_aktien, verkauf_aktien = scan(AKTIEN, krypto=False)
    kauf_krypto, verkauf_krypto = scan(KRYPTOS, krypto=True)
    markt_liste, regime, empfehlungen, warnungen, korrelationen = markt_uebersicht()
    account = trading_client.get_account()

    nachricht = f"📊 <b>SCAN ABGESCHLOSSEN</b> – {datetime.now().strftime('%H:%M:%S')}\n\n"

    if kauf_aktien:
        nachricht += "🟢 <b>STARKE KAUFSIGNALE – AKTIEN</b>\n"
        nachricht += "\n".join(kauf_aktien)
    if kauf_krypto:
        nachricht += "\n🟢 <b>STARKE KAUFSIGNALE – KRYPTO</b>\n"
        nachricht += "\n".join(kauf_krypto)
    if verkauf_aktien or verkauf_krypto:
        nachricht += "\n🔴 <b>VERKAUFSSIGNALE</b>\n"
        nachricht += "\n".join(verkauf_aktien + verkauf_krypto)
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
                f"   Ø Kaufpreis: ${float(pos.avg_entry_price):.2f} | "
                f"Kurs: ${float(pos.current_price):.2f}\n"
                f"   G&V: {pl_emoji} ${pl:+.2f} ({pl_pct:+.2f}%)\n"
            )
    else:
        nachricht += "\n\n📦 <b>MEIN BESTAND</b>\nKeine offenen Positionen"

    print("\n" + "="*45)
    print("TELEGRAM ZUSAMMENFASSUNG:")
    print(nachricht)
    print("="*45)

    sende_telegram(nachricht)

    # Positionen für Website
    positionen_liste = []
    for pos in positionen:
        pl = float(pos.unrealized_pl)
        pl_pct = float(pos.unrealized_plpc) * 100
        positionen_liste.append({
            "symbol": pos.symbol,
            "qty": str(pos.qty),
            "einstieg": str(float(pos.avg_entry_price)),
            "kurs": str(float(pos.current_price)),
            "pl": str(pl),
            "pl_pct": str(pl_pct)
        })

    ergebnisse = {
        "zeitpunkt": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "portfolio": str(account.portfolio_value),
        "kontostand": str(account.cash),
        "kaufsignale": kauf_aktien + kauf_krypto,
        "verkaufsignale": verkauf_aktien + verkauf_krypto,
        "positionen": positionen_liste,
        "markt": markt_liste,
        "regime": regime,
        "empfehlungen": empfehlungen,
        "warnungen": warnungen,
        "korrelationen": korrelationen
    }
    speichere_ergebnisse(ergebnisse)

# Einmal ausführen und fertig!
main()
