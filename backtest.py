from datetime import UTC, datetime

from market_data import get_historical_bars
from reporting import speichere_run_history
from strategies import get_strategy


def berechne_drawdown(equity_curve):
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]["equity"]
    max_drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak if peak else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return round(max_drawdown * 100, 2)


def backtest_strategy(symbol, bars, config, initial_cash=10000.0):
    strategy = get_strategy(config)
    cash = float(initial_cash)
    shares = 0.0
    entry_price = 0.0
    trades = []
    equity_curve = []

    for index in range(50, len(bars)):
        window = bars[: index + 1]
        analyse = strategy.evaluate(window, config)
        price = float(analyse["kurs"])
        timestamp = getattr(bars[index], "timestamp", None)
        label = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(index)

        if shares == 0 and strategy.should_buy(analyse["kauf_score"], analyse["verkauf_score"]):
            shares = cash / price if price else 0.0
            entry_price = price
            cash = 0.0
            trades.append({
                "type": "BUY",
                "symbol": symbol,
                "price": round(price, 2),
                "shares": round(shares, 6),
                "time": label,
                "strategy": strategy.name,
            })
        elif shares > 0 and strategy.should_sell(analyse["kauf_score"], analyse["verkauf_score"]):
            cash = shares * price
            pnl = cash - (shares * entry_price)
            trades.append({
                "type": "SELL",
                "symbol": symbol,
                "price": round(price, 2),
                "shares": round(shares, 6),
                "time": label,
                "strategy": strategy.name,
                "pnl": round(pnl, 2),
            })
            shares = 0.0
            entry_price = 0.0

        equity = cash if shares == 0 else shares * price
        equity_curve.append({
            "time": label,
            "equity": round(equity, 2),
            "price": round(price, 2),
            "position": round(shares, 6),
        })

    final_equity = equity_curve[-1]["equity"] if equity_curve else round(initial_cash, 2)
    winning_trades = sum(1 for trade in trades if trade["type"] == "SELL" and trade.get("pnl", 0) > 0)
    closed_trades = sum(1 for trade in trades if trade["type"] == "SELL")
    win_rate = (winning_trades / closed_trades * 100) if closed_trades else 0.0

    return {
        "run_id": f"backtest-{strategy.name}-{symbol}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "mode": "backtest",
        "symbol": symbol,
        "strategy": strategy.name,
        "initial_cash": round(initial_cash, 2),
        "final_equity": round(final_equity, 2),
        "return_pct": round(((final_equity - initial_cash) / initial_cash) * 100, 2),
        "max_drawdown_pct": berechne_drawdown(equity_curve),
        "trade_count": len(trades),
        "closed_trade_count": closed_trades,
        "win_rate": round(win_rate, 2),
        "trades": trades,
        "equity_curve": equity_curve,
    }


def run_backtest(symbol, start, end, config, initial_cash=10000.0, krypto=False):
    bars = get_historical_bars(symbol, start, end, krypto=krypto)
    if not bars or len(bars) < 60:
        raise ValueError(f"Nicht genug historische Daten für {symbol}")

    result = backtest_strategy(symbol, bars, config, initial_cash=initial_cash)
    result["start"] = str(start)
    result["end"] = str(end)
    result["asset_type"] = "crypto" if krypto else "stock"
    result["config"] = {
        "strategy": config["strategy"]["name"],
        "trading_mode": config.get("trading_mode", "backtest"),
    }
    return result


def speichere_backtest_history(result):
    speichere_run_history({
        "run_id": result["run_id"],
        "mode": result["mode"],
        "zeitpunkt": datetime.now(UTC).strftime("%d.%m.%Y %H:%M"),
        "portfolio": str(result["final_equity"]),
        "kontostand": str(result["final_equity"]),
        "metrics": {
            "return_pct": result["return_pct"],
            "max_drawdown_pct": result["max_drawdown_pct"],
            "trade_count": result["trade_count"],
            "closed_trade_count": result["closed_trade_count"],
            "win_rate": result["win_rate"],
        },
        "config": result["config"],
        "scan_results": [],
        "backtest": {
            "symbol": result["symbol"],
            "asset_type": result["asset_type"],
            "start": result["start"],
            "end": result["end"],
            "initial_cash": result["initial_cash"],
            "final_equity": result["final_equity"],
            "trades": result["trades"],
        },
    })
