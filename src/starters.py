import requests
from .team_stats import TEAM_IDS, _season_and_type

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

BASE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"


def _get_json(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[starters] GET failed {url}: {e}")
        return None


def _pick_depth_chart_starter(team_id: int, pos_abbr: str) -> str | None:
    """
    Try to find the first-listed depth chart player for a given position.
    Returns athlete API URL or None. Very defensive: if anything looks weird,
    we just return None and leave that field blank.
    """
    url = f"{BASE}/teams/{team_id}/depthcharts"
    root = _get_json(url)
    if not root:
        return None

    items = root.get("items") or []
    for item in items:
        chart = item
        ref = item.get("$ref") or item.get("href")
        if ref:
            tmp = _get_json(ref)
            if tmp:
                chart = tmp

        label = (
            (chart.get("position") or chart.get("positionAbbreviation") or "")
            .upper()
            .strip()
        )
        if pos_abbr not in label:
            continue

        slots = chart.get("items") or chart.get("slots") or []
        for s in slots:
            # modern shape: s["athlete"]["$ref"]
            a = s.get("athlete") or {}
            aref = a.get("$ref")
            if aref:
                return aref

    return None


def _collect_numeric_stats(obj, out: dict):
    if isinstance(obj, dict):
        name = obj.get("name")
        val = obj.get("value")
        if name and isinstance(val, (int, float)):
            out[name] = val
        for v in obj.values():
            _collect_numeric_stats(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_numeric_stats(v, out)


def _get_player_stats(athlete_url: str, season: int, season_type: int) -> dict:
    """
    Fetch numeric season stats for a single player.
    If ESPN shape changes, returns {} and we fail gracefully.
    """
    # Best-effort pattern; if it 404s we just bail for that player.
    url = f"{athlete_url}/statistics/{season}/type/{season_type}"
    data = _get_json(url)
    if not data:
        return {}

    out: dict = {}
    _collect_numeric_stats(data, out)
    return out


def get_starter_metrics() -> dict[str, dict]:
    """
    Returns dict keyed by team abbr:

    {
      "DAL": {
        "QB_YDS": ...,
        "RB_YDS": ...,
        "WR_YDS": ...,
        "K_FG_PCT": ...,
      },
      ...
    }

    Missing pieces are simply omitted → CSV cells stay blank.
    """
    season, season_type = _season_and_type()
    result: dict[str, dict] = {}

    for abbr, team_id in TEAM_IDS.items():
        row: dict[str, float] = {}

        # QB
        qb_ref = _pick_depth_chart_starter(team_id, "QB")
        if qb_ref:
            s = _get_player_stats(qb_ref, season, season_type)
            yds = s.get("passingYards") or s.get("passYards")
            if yds is not None:
                row["QB_YDS"] = float(yds)

        # RB
        rb_ref = _pick_depth_chart_starter(team_id, "RB")
        if rb_ref:
            s = _get_player_stats(rb_ref, season, season_type)
            yds = s.get("rushingYards") or s.get("rushYards")
            if yds is not None:
                row["RB_YDS"] = float(yds)

        # WR
        wr_ref = _pick_depth_chart_starter(team_id, "WR")
        if wr_ref:
            s = _get_player_stats(wr_ref, season, season_type)
            yds = s.get("receivingYards")
            if yds is not None:
                row["WR_YDS"] = float(yds)

        # K
        k_ref = _pick_depth_chart_starter(team_id, "K")
        if k_ref:
            s = _get_player_stats(k_ref, season, season_type)
            pct = s.get("fieldGoalPct")
            if pct is not None:
                row["K_FG_PCT"] = round(float(pct), 2)

        if row:
            result[abbr] = row

    print(f"[starters] built starter metrics for {len(result)} teams")
    return result
