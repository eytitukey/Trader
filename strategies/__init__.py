from .confluence_v1 import ConfluenceV1Strategy


STRATEGIES = {
    ConfluenceV1Strategy.name: ConfluenceV1Strategy,
}


def get_strategy(config):
    name = config["strategy"]["name"]
    strategy_cls = STRATEGIES.get(name)
    if strategy_cls is None:
        raise ValueError(f"Unbekannte Strategie: {name}")
    return strategy_cls()
