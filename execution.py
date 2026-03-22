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


def order_kaufen(symbol, kurs, config):
    sl = round(kurs * (1 - config["risk"]["stop_loss"]), 2)
    tp = round(kurs * (1 + config["risk"]["take_profit"]), 2)
    if config["trading_mode"] == "off":
        print(f"   🧪 KAUF übersprungen (trading_mode=off) @ ${kurs:.2f}")
        return sl, tp

    order = MarketOrderRequest(
        symbol=symbol,
        qty=config["risk"]["order_qty"],
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC,
    )
    trading_client.submit_order(order)
    print(f"   ✅ GEKAUFT @ ${kurs:.2f}")
    return sl, tp


def order_verkaufen(symbol, qty, config):
    if config["trading_mode"] == "off":
        print(f"   🧪 VERKAUF übersprungen (trading_mode=off) qty={qty}")
        return

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.GTC,
    )
    trading_client.submit_order(order)
    print(f"   🔴 VERKAUFT {qty}")


def pruefe_sl_tp(kurs, einstieg, config):
    pct = (kurs - einstieg) / einstieg * 100
    if pct <= -config["risk"]["stop_loss"] * 100:
        return "verkaufen", pct
    if pct >= config["risk"]["take_profit"] * 100:
        return "verkaufen", pct
    return "halten", pct
