from datetime import datetime
from dateutil import tz
import csv
from pathlib import Path
import yaml

def load_settings(path="config/settings.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

def today_et(tz_name="America/New_York"):
    tz_et = tz.gettz(tz_name)
    return datetime.now(tz_et).date()

def read_schema(path="config/fields_schema.csv"):
    fields = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fields.append(row["name"])
    return fields
