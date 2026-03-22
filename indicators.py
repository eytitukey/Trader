def berechne_rsi(bars, periode=14):
    preise = [bar.close for bar in bars]
    gewinne, verluste = [], []
    for i in range(1, len(preise)):
        diff = preise[i] - preise[i - 1]
        if diff > 0:
            gewinne.append(diff)
            verluste.append(0)
        else:
            gewinne.append(0)
            verluste.append(abs(diff))
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

    ema12_werte = []
    ema26_werte = []
    ema12 = preise[0]
    ema26 = preise[0]
    k12 = 2 / (12 + 1)
    k26 = 2 / (26 + 1)

    for preis in preise:
        ema12 = preis * k12 + ema12 * (1 - k12)
        ema26 = preis * k26 + ema26 * (1 - k26)
        ema12_werte.append(ema12)
        ema26_werte.append(ema26)

    macd_serie = [ema12_werte[i] - ema26_werte[i] for i in range(len(preise))]
    macd_linie = macd_serie[-1]
    signal_linie = ema(macd_serie[-9:], 9)
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
    if not kurs_steigt and vol_hoch:
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
    except (TypeError, ValueError, ZeroDivisionError, AttributeError):
        return 0


def korrelation_label(k):
    if k >= 0.7:
        return "🟢 Stark positiv"
    if k >= 0.4:
        return "🟡 Mittel positiv"
    if k >= 0.1:
        return "⬜ Schwach positiv"
    if k >= -0.1:
        return "⬜ Neutral"
    if k >= -0.4:
        return "🟡 Schwach negativ"
    if k >= -0.7:
        return "🟠 Mittel negativ"
    return "🔴 Stark negativ"
