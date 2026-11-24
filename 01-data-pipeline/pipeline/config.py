import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(path=ROOT / "config.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


def market_priced(cfg):
    """Instruments that must have a market price. Treasuries get model prices later."""
    return [i["id"] for i in cfg["instruments"] if i["type"] in ("equity", "etf")]
