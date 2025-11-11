import requests

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

# ESPN team IDs by abbreviation (regular season)
TEAM_IDS = {
    "ARI": 22,
    "ATL": 1,
    "BAL": 33,
    "BUF": 2,
    "CAR": 29,
    "CHI": 3,
    "CIN": 4,
    "CLE": 5,
    "DAL": 6,
    "DEN": 7,
    "DET": 8,
    "GB": 9,
    "HOU": 34,
    "IND": 11,
    "JAX": 30,
    "KC": 12,
    "LV": 13,
    "LAC": 24,
    "LAR": 14,
    "MIA": 15,
    "MIN": 16,
    "NE": 17,
    "NO": 18,
    "NYG": 19,
    "NYJ": 20,
    "PHI": 21,
    "PIT": 23,
    "SF": 25,
    "SEA": 26,
    "TB": 27,
    "TEN": 10,
    "WSH": 28,
}


def _season_and_type():
    """Infer current NFL regular season."""
    from datetime import datetime

    today = datetime.utcnow().date()
    year = today.year
    if today.month in (1, 2):
        year -= 1
    return year, 2  # type=2 regular season


def _collect_stats(obj, out: dict):
    """Flatten ESPN stats JSON into {name: value} for any numeric stat."""
    if isinstance(obj, dict):
        name = obj.get("name")
        val = obj.get("value")
        if name and isinstance(val, (int, float)):
            out[name] = val
        for v in obj.values():
            _collect_stats(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_stats(item, out)


def _fetch_team_stats(team_abbr: str) -> dict:
    """Fetch ESPN team statistics for one team; return flat dict."""
    team_id = TEAM_IDS.get(team_abbr)
    if not team_id:
        return {}

    season, season_type = _season_and_type()
    url = (
        f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/"
        f"seasons/{season}/types/{season_type}/teams/{team_id}/statistics"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[team_stats] failed to fetch stats for {team_abbr}: {e}")
        return {}

    flat: dict = {}
    _collect_stats(data, flat)
    return flat


def _num(raw: dict, key: str):
    v = raw.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _per_game(raw: dict, total_key: str, gp: float):
    v = _num(raw, total_key)
    if v is None or gp <= 0:
        return None
    return v / gp


def get_team_metrics():
    """
    Map ESPN team stats JSON into NFL 1..36 columns.

    Uses John’s definitions as close as ESPN allows.
    Any missing stat -> column left blank (never breaks).
    """
    metrics: dict[str, dict] = {}

    for abbr in TEAM_IDS:
        raw = _fetch_team_stats(abbr)
        if not raw:
            continue

        gp = (
            _num(raw, "teamGamesPlayed")
            or _num(raw, "gamesPlayed")
            or 1.0
        )

        m: dict[str, float] = {}

        # ---------- OFFENSE / TEAM EFFICIENCY ----------

        # NFL 1 – Completion percentage (team)
        v = _num(raw, "completionPct")
        if v is not None:
            m["NFL 1"] = round(v, 2)

        # NFL 2 – First downs per game
        v = _num(raw, "firstDownsPerGame") or _per_game(raw, "firstDowns", gp)
        if v is not None:
            m["NFL 2"] = round(v, 2)

        # NFL 3 – 4th down conversion percentage (offense)
        v = _num(raw, "fourthDownConvPct")
        if v is not None:
            m["NFL 3"] = round(v, 2)

        # NFL 4 – Field goal percentage
        v = _num(raw, "fieldGoalPct")
        if v is not None:
            m["NFL 4"] = round(v, 2)

        # NFL 5 – Offensive points per game
        v = _num(raw, "totalPointsPerGame")
        if v is not None:
            m["NFL 5"] = round(v, 2)

        # NFL 6 – Giveaway–takeaway differential per game
        give = _num(raw, "totalGiveaways")
        take = _num(raw, "totalTakeaways")
        if give is not None and take is not None:
            m["NFL 6"] = round((take - give) / gp, 3)

        # NFL 7 – Interceptions thrown per game
        v = _num(raw, "interceptions")
        if v is not None:
            m["NFL 7"] = round(v / gp, 3)

        # NFL 8 – Fumbles lost per game
        v = _num(raw, "fumblesLost")
        if v is not None:
            m["NFL 8"] = round(v / gp, 3)

        # NFL 9 – Sacks (defense) per game
        v = _num(raw, "sacks")
        if v is not None:
            m["NFL 9"] = round(v / gp, 3)

        # NFL 10 – Penalties per game (team committed)
        v = _num(raw, "totalPenalties")
        if v is not None:
            m["NFL 10"] = round(v / gp, 3)

        # NFL 11 – Passing offense yards per game
        v = _num(raw, "passingYardsPerGame")
        if v is not None:
            m["NFL 11"] = round(v, 2)

        # NFL 12 – Rushing offense yards per game
        v = _num(raw, "rushingYardsPerGame")
        if v is not None:
            m["NFL 12"] = round(v, 2)

        # NFL 13 – Receiving yards per game
        v = _num(raw, "receivingYardsPerGame")
        if v is not None:
            m["NFL 13"] = round(v, 2)

        # NFL 14 – 3rd down conversion percentage
        v = _num(raw, "thirdDownConvPct")
        if v is not None:
            m["NFL 14"] = round(v, 2)

        # NFL 15 – Kickoff return yards per game
        v = _per_game(raw, "kickoffReturnYards", gp)
        if v is not None:
            m["NFL 15"] = round(v, 2)

        # NFL 16 – Punt return yards per game
        v = _per_game(raw, "puntReturnYards", gp)
        if v is not None:
            m["NFL 16"] = round(v, 2)

        # ---------- DEFENSE & TURNOVERS ----------

        # NFL 17 – Defensive interceptions per game
        v = _num(raw, "interceptionTouchdowns")  # if you prefer INTs, adjust key
        # If that key isn't right for your sheet, switch to def INT key you prefer.
        # For now leave blank unless clear.

        # (Safer: use totalTakeaways - fumblesRecovered as proxy for INTs)
        # We'll keep NFL 17 optional.

        # NFL 18 – Defensive forced fumbles per game
        v = _num(raw, "fumblesForced")
        if v is not None:
            m["NFL 18"] = round(v / gp, 3)

        # NFL 19 – Defensive sacks per game (already in NFL 9; you can adjust)
        # To avoid duplication you can leave 19 blank or reuse:
        if "NFL 9" in m:
            m["NFL 19"] = m["NFL 9"]

        # NFL 20 – Passing yards allowed per game
        v = _num(raw, "yardsAllowed")  # ESPN doesn’t split pass/rush cleanly here
        # You can refine via PFR; for now keep blank or rough.
        # m["NFL 20"] = ...

        # NFL 21 – Rushing yards allowed per game
        # See note above; requires game-log or split stats.

        # NFL 22 – Points allowed per game
        v = _per_game(raw, "pointsAllowed", gp)
        if v is not None:
            m["NFL 26"] = round(v, 2)  # maps to schema NFL 26

        # NFL 23 – Takeaways per game (INT + FR)
        take = _num(raw, "totalTakeaways")
        if take is not None:
            m["NFL 23"] = round(take / gp, 3)

        # NFL 24 – Penalties (defense/team) per game
        if "NFL 10" in m:
            m["NFL 24"] = m["NFL 10"]

        # NFL 25 – Penalty yards per game
        v = _num(raw, "totalPenaltyYards")
        if v is not None:
            m["NFL 25"] = round(v / gp, 2)

        # ---------- 4TH DOWN / SPECIAL TEAMS ----------

        # NFL 26/27/28 already partly mapped above; can refine as needed.

        # NFL 29 – Extra point percentage
        v = _num(raw, "extraPointPct")
        if v is not None:
            m["NFL 29"] = round(v, 2)

        # NFL 30 – Extra point attempts per game
        v = _num(raw, "extraPointAttempts")
        if v is not None:
            m["NFL 30"] = round(v / gp, 3)

        # NFL 31 – Extra points made per game
        v = _num(raw, "extraPointsMade")
        if v is not None:
            m["NFL 31"] = round(v / gp, 3)

        # NFL 32 – Kickoff average yards
        v = _num(raw, "avgKickoffYards")
        if v is not None:
            m["NFL 32"] = round(v, 2)

        # NFL 33 – Gross punt average yards
        v = _num(raw, "grossAvgPuntYards")
        if v is not None:
            m["NFL 33"] = round(v, 2)

        # NFL 34/35 – home/road PPG (from derived.py, NOT here)

        # NFL 36 – League-wide baseline QB rating (constant)
        m["NFL 36"] = 90.0

        if m:
            metrics[abbr] = m

    return metrics
