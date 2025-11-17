from __future__ import annotations

import argparse
from typing import Dict, Any, List, Optional

from .utils import load_settings, ensure_dirs, today_et, read_schema
from .schedule import get_matchups
from .team_stats import get_team_metrics
from .output import write_csv
from .derived import get_home_road_ppg
from .starters import get_starter_metrics


def build_row(
    date_str: str,
    game_id: str,
    team: str,
    opponent: str,
    home_away: str,
    schema: List[str],
    team_metrics: Dict[str, Dict[str, float]],
    starters: Optional[Dict[str, Dict[str, float]]] = None,
    home_road: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "game_date": date_str,
        "game_id": game_id,
        "team": team,
        "opponent": opponent,
        "home_away": home_away,
    }

    # Initialize all NFL columns
    for col in schema:
        if col.startswith("NFL "):
            row[col] = None

    # 1) Team-level metrics (NFL 5..32)
    tm = team_metrics.get(team, {})
    for k, v in tm.items():
        if k in row and v is not None:
            row[k] = v

    # 2) Starter metrics → NFL 1–4 (if available)
    if starters:
        st = starters.get(team, {})
        rb = st.get("RB_YDS")
        qb = st.get("QB_YDS")
        wr = st.get("WR_YDS")
        k_fg = st.get("K_FG_PCT")

        if rb is not None:
            row["NFL 1"] = rb
        if qb is not None:
            row["NFL 2"] = qb
        if k_fg is not None:
            row["NFL 3"] = k_fg
        if wr is not None:
            row["NFL 4"] = wr

    # 3) Home/Road PPG → NFL 33 (road), NFL 34 (home)
    if home_road:
        hr = home_road.get(team, {})
        home_ppg = hr.get("home_ppg")
        road_ppg = hr.get("road_ppg")
        if road_ppg is not None:
            row["NFL 33"] = road_ppg
        if home_ppg is not None:
            row["NFL 34"] = home_ppg

    return row


def run(target_date: Optional[str] = None) -> None:
    settings = load_settings()
    ensure_dirs(settings["output_dir"], settings["archive_dir"], settings["log_dir"])
    schema = read_schema()

    if target_date:
        date_str = target_date
        matchups = get_matchups(target_date)
    else:
        date_str = str(today_et(settings.get("timezone", "America/New_York")))
        matchups = get_matchups()

    if not matchups:
        print(f"No NFL games found for {date_str}; writing empty file.")
        rows: List[Dict[str, Any]] = []
    else:
        team_metrics = get_team_metrics()
        home_road = get_home_road_ppg()
        starters = get_starter_metrics() if callable(get_starter_metrics) else None

        rows = [
            build_row(
                date_str,
                game_id,
                team,
                opp,
                ha,
                schema,
                team_metrics,
                starters,
                home_road,
            )
            for (game_id, team, opp, ha) in matchups
        ]

    latest_path = f'{settings["output_dir"]}/{settings["latest_filename"]}'
    write_csv(rows, schema, latest_path, settings["archive_dir"])
    print(f"✅ wrote {len(rows)} rows → {latest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD", default=None)
    args = parser.parse_args()
    run(target_date=args.date)
