import argparse
import json

from backtest import run_backtest, speichere_backtest_history
from config import load_config


def parse_args():
    parser = argparse.ArgumentParser(description="Fuehrt einen einfachen Strategie-Backtest aus.")
    parser.add_argument("--symbol", required=True, help="Zu testendes Symbol, z.B. AAPL oder BTC/USD")
    parser.add_argument("--start", required=True, help="Startdatum im Format YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Enddatum im Format YYYY-MM-DD")
    parser.add_argument("--strategy", required=True, help="Strategiename, z.B. confluence_v1")
    parser.add_argument("--initial-cash", type=float, default=10000.0, help="Startkapital")
    parser.add_argument("--crypto", action="store_true", help="Behandle Symbol als Krypto")
    parser.add_argument("--save-history", action="store_true", help="Backtest-Ergebnis in data/history.json speichern")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()
    config["strategy"] = dict(config["strategy"])
    config["strategy"]["name"] = args.strategy

    result = run_backtest(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        config=config,
        initial_cash=args.initial_cash,
        krypto=args.crypto,
    )

    if args.save_history:
        speichere_backtest_history(result)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
