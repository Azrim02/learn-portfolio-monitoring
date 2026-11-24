"""Raw downloads. Files are written once and never changed."""
import datetime as dt

from . import config


def save(source, target, name, text):
    folder = config.DATA / "raw" / source / target.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = folder / f"{stamp}_{name}"
    with open(path, "x", encoding="utf-8") as f:
        f.write(text)
    return path
