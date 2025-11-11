import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def _get_soup(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"[espn] fetch error for {url}: {e}")
        return None

def fetch_team_offense(team):
    """
    Returns offense stats (subset for now).
    If page/table not found, returns None fields (pipeline still runs).
    """
    data = {
        "team_pass_yds_pg": None,
        "team_rush_yds_pg": None,
        "team_recv_yds_pg": None,
        "first_downs_total": None,
        "third_down_made_pg": None,
        "kick_return_yds_pg": None,
        "punt_return_yds_pg": None,
    }

    url = "https://www.espn.com/nfl/stats/team/_/view/offense"
    soup = _get_soup(url)
    if soup is None:
        print("[espn] soup is None; leaving offense fields empty")
        return data

    # ESPN often renders via JS; try to find any table with rows resembling stats.
    table = soup.find("table")
    if not table:
        print("[espn] offense table not found; leaving fields empty")
        return data

    rows = table.find_all("tr")
    if not rows or len(rows) < 2:
        print("[espn] offense table rows missing; leaving fields empty")
        return data

    # Minimal mapping for your current test teams (expand later)
    team_map = {
        "Dallas Cowboys": "DAL",
        "Washington Commanders": "WAS",
    }

    # Try to parse rows; if columns don't match, skip gracefully
    for tr in rows[1:]:
        cols = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cols) < 4:
            continue
        name = cols[1] if len(cols) > 1 else ""
        code = team_map.get(name)
        if code == team:
            # Try to read a plausible Pass Yds/G column if present
            # (index may differ — guard conversions carefully)
            try:
                # Commonly: cols[3] might be Pass Yds/G; adjust as we refine
                val = cols[3].replace(",", "")
                data["team_pass_yds_pg"] = float(val) if val.replace(".", "", 1).isdigit() else None
            except Exception:
                pass
            return data

    # If not found, still return safely
    print(f"[espn] no offense row matched team={team}")
    return data

def fetch_team_defense(team):
    # Leave placeholders for now; will wire real parsing next
    return {
        "def_team_int_pg": None,
        "def_team_ff_pg": None,
        "def_team_sacks_pg": None,
        "give_take_diff": None,
        "def_pass_yds_allowed_pg": None,
        "def_recv_yds_allowed_pg": None,
    }

def fetch_starters(team):
    return {
        "starter_qb_pass_yds": None,
        "starter_rb_rush_yds": None,
        "starter_wr_recv_yds": None,
        "starter_k_fg_pct": None,
    }
