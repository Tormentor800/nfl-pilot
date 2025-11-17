import requests
from datetime import datetime
from typing import Dict, Any, Optional


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
TEAM_IDS: Dict[str, int] = {
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
    "LV": 13,   # Raiders
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
    "WSH": 28,  # Commanders
}


def _season_and_type() -> (int, int):
    """
    Decide which season + type to query.
    For now: infer from current year; this is simple and safe enough.
    """
    today = datetime.utcnow().date()
    year = today.year
    # For games from Jan–Feb, use previous season
    if today.month in (1, 2):
        year -= 1
    # type=2 is regular season
    return year, 2


def _collect_stats(obj: Any, out: Dict[str, Any]) -> None:
    """
    Recursively walk ESPN JSON and pull any numeric {name, value} stats.
    """
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


def _fetch_team_stats(team_abbr: str) -> Dict[str, Any]:
    """
    Call ESPN's team statistics endpoint for a single team and return a flat dict of stats.
    If anything fails, return {} so we never break the pipeline.
    """
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

    out: Dict[str, Any] = {}
    _collect_stats(data, out)
    return out


def get_team_metrics() -> Dict[str, Dict[str, float]]:
    """
    Map ESPN team stats JSON into NFL 5..32 columns from John's 34-metric spec.

    NFL 1..4 are starter-based (QB/RB/WR/K) and are filled in main.py via the
    `starters` module.
    NFL 33..34 (road/home PPG) are filled in main.py via derived.get_home_road_ppg().

    This function focuses on team-level stats: NFL 5..32.
    """
    metrics: Dict[str, Dict[str, float]] = {}

    for abbr in TEAM_IDS.keys():
        raw = _fetch_team_stats(abbr)
        if not raw:
            continue

        m: Dict[str, float] = {}
        gp = float(
            raw.get("gamesPlayed")
            or raw.get("teamGamesPlayed")
            or 1.0
        )

        def per_game(key: str) -> Optional[float]:
            v = raw.get(key)
            if v is None:
                return None
            try:
                return float(v) / gp
            except Exception:
                return None

        # ---- NFL 5: Team offensive passing yards per game ----
        v = (
            raw.get("passingYardsPerGame")
            or raw.get("netPassingYardsPerGame")
            or (per_game("netPassingYards") if "netPassingYards" in raw else None)
        )
        if v is None and "passingYards" in raw:
            v = per_game("passingYards")
        if v is not None:
            m["NFL 5"] = round(float(v), 2)

        # ---- NFL 6: Team offensive rushing yards per game ----
        v = raw.get("rushingYardsPerGame") or per_game("rushingYards")
        if v is not None:
            m["NFL 6"] = round(float(v), 2)

        # ---- NFL 7: Team receiving yards per game ----
        v = raw.get("receivingYardsPerGame") or per_game("receivingYards")
        if v is not None:
            m["NFL 7"] = round(float(v), 2)

        # ---- NFL 8: Team first downs per game ----
        v = raw.get("firstDownsPerGame") or per_game("firstDowns")
        if v is not None:
            m["NFL 8"] = round(float(v), 2)

        # ---- NFL 9: Team 3rd-down conversion percentage ----
        v = raw.get("thirdDownConvPct")
        if v is not None:
            m["NFL 9"] = round(float(v), 2)

        # ---- NFL 10: Team kickoff return yards per game ----
        v = per_game("kickoffReturnYards")
        if v is not None:
            m["NFL 10"] = round(float(v), 2)

        # ---- NFL 11: Team punt return yards per game ----
        v = per_game("puntReturnYards")
        if v is not None:
            m["NFL 11"] = round(float(v), 2)

        # ---- NFL 12: Team sacks per game (defense) ----
        v = per_game("sacks")
        if v is not None:
            m["NFL 12"] = round(float(v), 3)

        # ---- NFL 13: Defensive interceptions per game (proxy for top defender INTs) ----
        v = raw.get("defInterceptions") or raw.get("interceptionsAgainst")
        if v is None:
            take = raw.get("totalTakeaways")
            fum_rec = raw.get("fumbleRecoveries") or raw.get("fumblesRecovered")
            if take is not None:
                try:
                    v = float(take) - float(fum_rec or 0)
                except Exception:
                    v = None
        if v is not None:
            m["NFL 13"] = round(float(v) / gp, 3)

        # ---- NFL 14: Defensive forced fumbles per game ----
        v = per_game("fumblesForced")
        if v is not None:
            m["NFL 14"] = round(float(v), 3)

        # ---- NFL 15: Team passing yards allowed per game ----
        v = (
            raw.get("passYardsAllowedPerGame")
            or raw.get("passingYardsAllowedPerGame")
        )
        if v is None and "yardsAllowed" in raw and "rushingYardsAllowedPerGame" in raw:
            try:
                v = float(raw["yardsAllowed"]) / gp - float(
                    raw["rushingYardsAllowedPerGame"]
                )
            except Exception:
                v = None
        if v is not None:
            m["NFL 15"] = round(float(v), 2)

        # ---- NFL 16: Team rushing yards allowed per game ----
        v = raw.get("rushYardsAllowedPerGame") or raw.get("rushingYardsAllowedPerGame")
        if v is not None:
            m["NFL 16"] = round(float(v), 2)

        # ---- NFL 17: Team receiving yards allowed per game ----
        v = m.get("NFL 15")
        if v is not None:
            m["NFL 17"] = v

        # ---- NFL 18: Giveaway–takeaway differential per game ----
        give = raw.get("totalGiveaways") or raw.get("giveaways")
        take = raw.get("totalTakeaways") or raw.get("takeaways")
        if give is not None and take is not None:
            try:
                m["NFL 18"] = round((float(take) - float(give)) / gp, 3)
            except Exception:
                pass

        # ---- NFL 19: Team defensive interceptions per game (full defense) ----
        v = raw.get("defInterceptions") or raw.get("interceptionsAgainst")
        if v is not None:
            m["NFL 19"] = round(float(v) / gp, 3)

        # ---- NFL 20: Team fumbles per game (offense giveaways via fumbles) ----
        v = per_game("fumblesLost")
        if v is not None:
            m["NFL 20"] = round(float(v), 3)

        # ---- NFL 21: Team sacks per game (duplicate) ----
        if "NFL 12" in m:
            m["NFL 21"] = m["NFL 12"]

        # ---- NFL 22–25: quarter-based scoring placeholders (numeric, non-blank) ----
        m.setdefault("NFL 22", 0.0)
        m.setdefault("NFL 23", 0.0)
        m.setdefault("NFL 24", 0.0)
        m.setdefault("NFL 25", 0.0)

        # ---- NFL 26: Rushing attempts per game ----
        v = per_game("rushingAttempts")
        if v is not None:
            m["NFL 26"] = round(float(v), 3)

        # ---- NFL 27: Passing attempts per game ----
        v = per_game("passingAttempts")
        if v is not None:
            m["NFL 27"] = round(float(v), 3)

        # ---- NFL 28: Completions per game ----
        v = per_game("completions")
        if v is not None:
            m["NFL 28"] = round(float(v), 3)

        # ---- NFL 29: QB rating ----
        v = raw.get("quarterbackRating") or raw.get("QBRating")
        if v is not None:
            m["NFL 29"] = round(float(v), 2)

        # ---- NFL 30: Completion percentage ----
        v = raw.get("completionPct")
        if v is not None:
            m["NFL 30"] = round(float(v), 2)

        # ---- NFL 31: Penalties per game ----
        v = per_game("totalPenalties") or per_game("penalties")
        if v is not None:
            m["NFL 31"] = round(float(v), 3)

        # ---- NFL 32: 4th-down conversion percentage (offense) ----
        v = raw.get("fourthDownConvPct")
        if v is not None:
            m["NFL 32"] = round(float(v), 2)

        if m:
            metrics[abbr] = m

    return metrics
