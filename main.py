def main():
    kauf_aktien, verkauf_aktien = scan(AKTIEN, krypto=False)
    kauf_krypto, verkauf_krypto = scan(KRYPTOS, krypto=True)
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
        "positionen": positionen_liste
    }
    speichere_ergebnisse(ergebnisse)

# Einmal ausführen und fertig!
main()
