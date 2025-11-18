from __future__ import annotations

import argparse
from typing import Dict, List, Any

from .utils import load_settings, ensure_dirs, today_et, read_schema
from .schedule import get_matchups
from .team_stats import get_team_metrics
from .derived import get_home_road_ppg
from .output import write_csv


def build_row(
    date_str: str,
    game_id: str,
    team: str,
    opponent: str,
    home_away: str,
    schema: List[str],
    team_metrics: Dict[str, Dict[str, Any]],
    home_road: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Build one output row for team vs opponent.

    - Ensures every column in schema exists in the row.
    - Fills from team_metrics, then home/road splits.
    """
    row: Dict[str, Any] = {
        "game_date": date_str,
        "game_id": game_id,
        "team": team,
        "opponent": opponent,
        "home_away": home_away,
    }

    # Initialize all schema columns as blank strings so CSV has no missing keys
    for col in schema:
        if col not in row:
            row[col] = ""

    # Team-level metrics
    m = team_metrics.get(team, {})
    for k, v in m.items():
        if k in row and v is not None:
            row[k] = v

    # Home/Road splits
    if home_road is not None:
        hr = home_road.get(team, {})
        for k, v in hr.items():
            if k in row and v is not None:
                row[k] = v

    return row


def run(target_date: str | None = None) -> None:
    settings = load_settings()
    ensure_dirs(settings["output_dir"], settings["archive_dir"], settings["log_dir"])
    schema = read_schema()

    # Determine date
    if target_date:
        date_str = target_date
    else:
        date_str = str(today_et(settings.get("timezone", "America/New_York")))

    matchups = get_matchups(date_str)

    if not matchups:
        print(f"No NFL games found for {date_str}; writing empty file.")
        rows: List[Dict[str, Any]] = []
    else:
        team_metrics = get_team_metrics()
        home_road = get_home_road_ppg()

        rows = [
            build_row(
                date_str=date_str,
                game_id=game_id,
                team=team,
                opponent=opp,
                home_away=ha,
                schema=schema,
                team_metrics=team_metrics,
                home_road=home_road,
            )
            for (game_id, team, opp, ha) in matchups
        ]

    latest_path = f'{settings["output_dir"]}/{settings["latest_filename"]}'
    write_csv(rows, schema, latest_path, settings["archive_dir"])
    print(f"✅ wrote {len(rows)} rows → {latest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL pilot feed generator")
    parser.add_argument(
        "--date",
        help="Target date in YYYY-MM-DD (defaults to today ET)",
        default=None,
    )
    args = parser.parse_args()
    run(target_date=args.date)


if __name__ == "__main__":
    main()
