from pathlib import Path

USER_AGENT = "hackalod-harvester/1.0"
DELAY = 0.5
SEP = " | "

SOURCE_DIR = Path("source")  # hand-made inputs that are not harvested
CACHE_DIR = Path("cache")  # cached responses
DATA_DIR = Path("../presentation_layer/data")  # serves the front-end


def make_cache_dir(path):
    """Keep git out of what gets downloaded into it."""
    path.mkdir(parents=True, exist_ok=True)
    ignore = path / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    return path
