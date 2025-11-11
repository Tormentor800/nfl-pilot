import csv
from pathlib import Path
from datetime import datetime

def write_csv(rows, fields, latest_path, archive_dir):
    # latest
    Path(latest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(latest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # archive snapshot (UTC date-based filename)
    ts = datetime.utcnow().strftime("%Y-%m-%d")
    apath = Path(archive_dir) / f"{ts}.csv"
    apath.parent.mkdir(parents=True, exist_ok=True)
    with open(apath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
