import json
from copy import deepcopy
from pathlib import Path


CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG = {
    "trading_mode": "paper",
    "reporting": {
        "telegram_enabled": True,
        "dashboard_enabled": True,
    },
    "risk": {
        "order_qty": 1,
        "stop_loss": 0.03,
        "take_profit": 0.06,
    },
    "strategy": {
        "name": "confluence_v1",
        "rsi_period": 14,
        "rsi_buy": 35,
        "rsi_sell": 65,
    },
    "universes": {
        "stocks": [
            "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
            "META", "TSLA", "AVGO", "JPM", "LLY",
            "V", "UNH", "XOM", "MA", "COST",
            "HD", "PG", "JNJ", "NFLX", "ABBV",
            "BAC", "CRM", "ORCL", "CVX", "MRK",
            "AMD", "KO", "PEP", "TMO", "ACN",
            "CSCO", "LIN", "MCD", "ABT", "IBM",
            "GE", "NOW", "ISRG", "GS", "TXN", "PYPL",
            "QCOM", "INTU", "SPGI", "BKNG", "RTX",
            "CAT", "DHR", "AMGN", "BLK", "SPY",
        ],
        "crypto": [
            "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD",
            "LINK/USD", "LTC/USD", "UNI/USD", "AAVE/USD", "SHIB/USD",
            "BCH/USD", "MATIC/USD", "CRV/USD", "GRT/USD", "BAT/USD",
            "MKR/USD", "DOT/USD", "XTZ/USD", "SUSHI/USD", "YFI/USD",
            "ALGO/USD", "ATOM/USD", "FIL/USD", "NEAR/USD", "APE/USD",
            "SAND/USD", "MANA/USD", "AXS/USD", "CHZ/USD", "ENJ/USD",
            "COMP/USD", "SNX/USD", "OP/USD", "ARB/USD", "LDO/USD",
            "IMX/USD", "1INCH/USD", "RPL/USD", "ZRX/USD", "BAL/USD",
            "UMA/USD", "OCEAN/USD", "ANKR/USD", "STORJ/USD", "RNDR/USD",
            "NMR/USD", "RLC/USD", "BAND/USD", "CTSI/USD", "SKL/USD",
        ],
    },
    "market_assets": {
        "SPY": {"emoji": "📈", "name": "S&P 500", "krypto": False},
        "QQQ": {"emoji": "💻", "name": "Nasdaq 100", "krypto": False},
        "DIA": {"emoji": "🏦", "name": "Dow Jones", "krypto": False},
        "IWM": {"emoji": "🏢", "name": "Russell 2000", "krypto": False},
        "GLD": {"emoji": "🥇", "name": "Gold", "krypto": False},
        "USO": {"emoji": "🛢️", "name": "Öl (WTI)", "krypto": False},
        "UUP": {"emoji": "💵", "name": "USD Index", "krypto": False},
        "BTC/USD": {"emoji": "₿", "name": "Bitcoin", "krypto": True},
    },
    "news_symbols": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
        "META", "TSLA", "JPM", "BTC/USD", "ETH/USD", "PYPL",
    ],
    "news_keywords": {
        "AAPL": ["aapl", "apple", "iphone", "ipad", "macbook"],
        "MSFT": ["msft", "microsoft", "azure", "windows", "xbox"],
        "NVDA": ["nvda", "nvidia", "geforce", "cuda"],
        "GOOGL": ["googl", "google", "alphabet", "youtube", "gemini"],
        "AMZN": ["amzn", "amazon", "aws", "prime"],
        "META": ["meta", "facebook", "instagram", "whatsapp", "threads"],
        "TSLA": ["tsla", "tesla", "elon musk", "model 3", "model y"],
        "JPM": ["jpm", "jpmorgan", "jp morgan", "jamie dimon"],
        "PYPL": ["pypl", "paypal", "venmo"],
        "BTC/USD": ["btc", "bitcoin", "btc/usd"],
        "ETH/USD": ["eth", "ethereum", "ether", "eth/usd"],
    },
}


def _merge_dicts(base, override):
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path=CONFIG_PATH):
    config = deepcopy(DEFAULT_CONFIG)
    if not Path(path).exists():
        return config

    with open(path, "r", encoding="utf-8") as handle:
        user_config = json.load(handle)
    return _merge_dicts(config, user_config)
