import os

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest


API_KEY = os.environ.get("ALPACA_KEY")
SECRET_KEY = os.environ.get("ALPACA_SECRET")

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)


def hat_position(symbol):
    try:
        pos = trading_client.get_open_position(symbol)
        return True, float(pos.avg_entry_price), float(pos.qty)
    except Exception:
        return False, 0, 0


def ist_krypto_symbol(symbol):
    return "/" in symbol


def order_kaufen(symbol, kurs, config):
    sl = round(kurs * (1 - config["risk"]["stop_loss"]), 2)
    tp = round(kurs * (1 + config["risk"]["take_profit"]), 2)
    if config["trading_mode"] == "off":
        print(f"   🧪 KAUF übersprungen (trading_mode=off) @ ${kurs:.2f}")
        return True, sl, tp, "trading_mode=off"

    order_kwargs = {
        "symbol": symbol,
        "side": OrderSide.BUY,
        "time_in_force": TimeInForce.GTC,
    }

    if ist_krypto_symbol(symbol):
        notional = max(config["risk"]["order_qty"] * kurs, 10.0)
        order_kwargs["notional"] = round(notional, 2)
    else:
        order_kwargs["qty"] = config["risk"]["order_qty"]

    order = MarketOrderRequest(**order_kwargs)
    try:
        trading_client.submit_order(order)
        print(f"   ✅ GEKAUFT @ ${kurs:.2f}")
        return True, sl, tp, None
    except Exception as exc:
        print(f"   ⚠️ Kauf fehlgeschlagen für {symbol}: {exc}")
        return False, sl, tp, str(exc)


def order_verkaufen(symbol, qty, config):
    if config["trading_mode"] == "off":
        print(f"   🧪 VERKAUF übersprungen (trading_mode=off) qty={qty}")
        return True, "trading_mode=off"

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.GTC,
    )
    try:
        trading_client.submit_order(order)
        print(f"   🔴 VERKAUFT {qty}")
        return True, None
    except Exception as exc:
        print(f"   ⚠️ Verkauf fehlgeschlagen für {symbol}: {exc}")
        return False, str(exc)


def pruefe_sl_tp(kurs, einstieg, config):
    pct = (kurs - einstieg) / einstieg * 100
    if pct <= -config["risk"]["stop_loss"] * 100:
        return "verkaufen", pct
    if pct >= config["risk"]["take_profit"] * 100:
        return "verkaufen", pct
    return "halten", pct
