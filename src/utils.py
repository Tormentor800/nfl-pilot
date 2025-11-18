import os
import csv
import yaml
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python <3.9 fallback (probably not needed here)
    from backports.zoneinfo import ZoneInfo  # type: ignore


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"


def load_settings() -> dict:
    """
    Load config/settings.yaml into a dict.
    """
    with open(CONFIG_DIR / "settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs(*paths: str) -> None:
    """
    Ensure the given directories exist.
    """
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def today_et(tz_name: str = "America/New_York"):
    """
    Return today's date in the given timezone (default ET).
    """
    tz = ZoneInfo(tz_name)
    return datetime.now(tz).date()


def read_schema():
    """
    Read config/fields_schema.csv and return a list of field names.

    Handles UTF-8 BOM and ignores blank / commented rows.
    Expected columns: name,description
    """
    path = CONFIG_DIR / "fields_schema.csv"
    fields = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Normalize header names in case of BOM (e.g. '\ufeffname')
        if reader.fieldnames:
            reader.fieldnames = [
                (fn.lstrip("\ufeff") if fn else fn) for fn in reader.fieldnames
            ]

        for row in reader:
            # Use .get to avoid KeyError if header weirdness happens
            name = (row.get("name") or "").strip()
            if not name:
                continue
            if name.startswith("#"):
                continue
            fields.append(name)

    return fields
