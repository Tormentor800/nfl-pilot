# src/transform.py
from datetime import datetime
from .sources.pfr import team_game_log_year

def compute_derived(team, raw):
    season = datetime.now().year
    try:
        _, agg = team_game_log_year(team, season)
    except Exception as e:
        print(f"[derive] PFR error for {team}: {e}")
        agg = {}

    # Default frame
    base = {
        "off_1q_pts_pg": None,
        "off_4q_pts_pg": None,
        "def_1q_pts_allowed_pg": None,
        "def_4q_pts_allowed_pg": None,
        "rush_att_pg": None,
        "pass_att_pg": None,
        "pass_comp_pg": None,
        "pass_comp_pct": None,
        "league_qb_rating": 90.0,
        "penalties_pg": None,
        "fourth_down_off_pct": None,
        "pts_pg_home": None,
        "pts_pg_road": None,
    }
    base.update(agg)
    return base
