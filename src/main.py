from .utils import load_settings, ensure_dirs, today_et, read_schema
from .schedule import get_matchups
from .team_stats import get_team_metrics
from .derived import get_home_road_ppg
from .starters import get_starter_metrics
from .output import write_csv


def build_row(
    date_str: str,
    game_id: str,
    team: str,
    opponent: str,
    home_away: str,
    schema,
    team_metrics: dict,
    home_road: dict | None = None,
    starter_metrics: dict | None = None,
) -> dict:
    # base fields
    row = {
        "game_date": date_str,
        "game_id": game_id,
        "team": team,
        "opponent": opponent,
        "home_away": home_away,
    }

    # initialise all schema columns to None so layout is stable
    for col in schema:
        if col not in row:
            row[col] = None

    # team metrics (NFL 1..36 etc.)
    t = team_metrics.get(team, {})
    for k, v in t.items():
        if k in row:
            row[k] = v

    # derived home/road PPG
    if home_road:
        hr = home_road.get(team, {})
        for k, v in hr.items():
            if k in row:
                row[k] = v

    # starter metrics
    if starter_metrics:
        sm = starter_metrics.get(team, {})
        for k, v in sm.items():
            if k in row:
                row[k] = v

    return row


def run():
    settings = load_settings()
    ensure_dirs(settings["output_dir"], settings["archive_dir"], settings["log_dir"])
    schema = read_schema()

    tz = settings.get("timezone", "America/New_York")
    date_str = str(today_et(tz))

    matchups = get_matchups()

    if not matchups:
        print(f"No NFL games found for {date_str}; writing empty file.")
        rows: list[dict] = []
    else:
        print(f"[schedule] {len(matchups)} rows for {date_str.replace('-', '')}")
        team_metrics = get_team_metrics()
        home_road = get_home_road_ppg()
        starter_metrics = get_starter_metrics()

        rows = [
            build_row(
                date_str,
                game_id,
                team,
                opp,
                ha,
                schema,
                team_metrics,
                home_road,
                starter_metrics,
            )
            for (game_id, team, opp, ha) in matchups
        ]

    latest_path = f'{settings["output_dir"]}/{settings["latest_filename"]}'
    write_csv(rows, schema, latest_path, settings["archive_dir"])
    print(f"✅ wrote {len(rows)} rows → {latest_path}")


if __name__ == "__main__":
    run()
