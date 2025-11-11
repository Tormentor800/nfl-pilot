from .utils import load_settings, ensure_dirs, today_et, read_schema
from .schedule import get_matchups
from .team_stats import get_team_metrics
from .output import write_csv
from .derived import get_home_road_ppg


def build_row(
    date_str: str,
    game_id: str,
    team: str,
    opponent: str,
    home_away: str,
    schema,
    team_metrics: dict,
    home_road: dict | None = None,
) -> dict:
    """Assemble a single row of NFL metrics."""
    row = {
        "game_date": date_str,
        "game_id": game_id,
        "team": team,
        "opponent": opponent,
        "home_away": home_away,
    }

    # initialize all NFL columns as blank
    for col in schema:
        if col.startswith("NFL "):
            row[col] = None

    # fill from team metrics
    m = team_metrics.get(team, {})
    for k, v in m.items():
        if k in row:
            row[k] = v

    # fill from derived metrics (home/road, etc.)
    if home_road:
        hr = home_road.get(team, {})
        for k, v in hr.items():
            if k in row:
                row[k] = v

    return row


def run():
    """Main execution pipeline."""
    settings = load_settings()
    ensure_dirs(settings["output_dir"], settings["archive_dir"], settings["log_dir"])
    schema = read_schema()

    # Determine date
    date_override = (settings.get("date_override") or "").strip()
    if date_override:
        date_str = date_override
        try:
            matchups = get_matchups(date_override)
        except TypeError:
            matchups = get_matchups()
    else:
        tz = settings.get("timezone", "America/New_York")
        date_str = str(today_et(tz))
        try:
            matchups = get_matchups()
        except TypeError:
            matchups = get_matchups(None)

    # If no matchups, write empty CSV
    if not matchups:
        print(f"No NFL games found for {date_str}; writing empty file.")
        rows: list[dict] = []
    else:
        # Fetch data
        team_metrics = get_team_metrics()
        home_road = get_home_road_ppg()

        rows = [
            build_row(date_str, game_id, team, opp, ha, schema, team_metrics, home_road)
            for (game_id, team, opp, ha) in matchups
        ]

    # Write output
    latest_path = f'{settings["output_dir"]}/{settings["latest_filename"]}'
    write_csv(rows, schema, latest_path, settings["archive_dir"])
    print(f"✅ wrote {len(rows)} rows → {latest_path}")


if __name__ == "__main__":
    run()
