import json
import os

import requests


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT")


def sende_telegram(nachricht, config):
    if not config["reporting"]["telegram_enabled"]:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": nachricht, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"⚠️ Telegram Fehler: {exc}")


def speichere_ergebnisse(ergebnisse, config):
    if not config["reporting"]["dashboard_enabled"]:
        return
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w", encoding="utf-8") as handle:
        json.dump(ergebnisse, handle, ensure_ascii=False)


def baue_positionen_liste(positionen):
    ergebnis = []
    for pos in positionen:
        pl = float(pos.unrealized_pl)
        pl_pct = float(pos.unrealized_plpc) * 100
        ergebnis.append({
            "symbol": pos.symbol,
            "qty": str(pos.qty),
            "einstieg": str(float(pos.avg_entry_price)),
            "kurs": str(float(pos.current_price)),
            "pl": str(pl),
            "pl_pct": str(pl_pct),
        })
    return ergebnis
