# src/schedule.py

from datetime import datetime
import requests

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def _parse_date(target_date: str | None) -> str:
    """
    target_date: 'YYYY-MM-DD' or None.
    Returns ESPN 'YYYYMMDD'.
    """
    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        dt = datetime.utcnow()
    return dt.strftime("%Y%m%d")


def get_matchups(target_date: str | None = None):
    """
    Return list of (game_id, team, opponent, home_away)
    for all scheduled NFL games on target_date.

    - team/opponent are ESPN abbreviations (DAL, PHI, etc.)
    - home_away is 'H' for the listed team if home, 'A' if away.
    """
    datestr = _parse_date(target_date)

    try:
        resp = requests.get(
            SCOREBOARD_URL,
            params={"dates": datestr},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[schedule] failed to fetch scoreboard for {datestr}: {e}")
        return []

    matchups = []

    for ev in data.get("events", []):
        gid = ev.get("id", "")
        comps = ev.get("competitions") or []
        if not comps:
            continue

        comp = comps[0]
        competitors = comp.get("competitors") or []
        if len(competitors) != 2:
            continue

        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue

        home_team = (home.get("team") or {}).get("abbreviation")
        away_team = (away.get("team") or {}).get("abbreviation")
        if not home_team or not away_team:
            continue

        # Two rows per game: one from each side's perspective
        matchups.append((gid, home_team, away_team, "H"))
        matchups.append((gid, away_team, home_team, "A"))

    print(f"[schedule] {len(matchups)} rows for {datestr}")
    return matchups
