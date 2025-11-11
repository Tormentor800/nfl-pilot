# src/sources/pfr.py
import pandas as pd
from ..http import fetch

TEAM_PFR = {
    "DAL": "dal",
    "WAS": "was",
    # add all teams as you go (BUF: 'buf', KC: 'kan', etc.)
}

def _read_html_tables(url: str):
    # Some PFR tables are inside HTML comments; pandas handles many cases.
    resp = fetch(url)
    html = resp.text
    # Try normal read first
    try:
        return pd.read_html(html, flavor="lxml")
    except ValueError:
        # Fallback: strip HTML comments that sometimes wrap tables
        import re
        uncommented = re.sub(r"<!--|-->", "", html)
        return pd.read_html(uncommented, flavor="lxml")

def team_game_log_year(team_code: str, season: int):
    """
    Returns (raw_df, agg_dict) for a team's season schedule & game results.
    Computes per-game means for the metrics we need.
    """
    slug = TEAM_PFR[team_code]
    url = f"https://www.pro-football-reference.com/teams/{slug}/{season}.htm"
    tables = _read_html_tables(url)

    # Heuristic: pick the largest table that contains 'Date' and 'Pts'
    candidate = None
    for t in tables:
        if "Date" in t.columns and "Pts" in t.columns:
            candidate = t if candidate is None or t.shape[0] > candidate.shape[0] else candidate
    if candidate is None:
        return pd.DataFrame(), {}

    df = candidate.copy()

    # Keep rows that look like real games (PFR often formats as YYYY-MM-DD)
    mask = df["Date"].astype(str).str.match(r"\d{4}-\d{2}-\d{2}", na=False)
    df = df[mask].reset_index(drop=True)

    # H/A column: on many pages away has '@' in an unnamed column
    if "Unnamed: 5" in df.columns:
        df["H/A"] = df["Unnamed: 5"].fillna("").map(lambda x: "A" if str(x).strip()=="@" else "H")
    elif "H/A" not in df.columns:
        df["H/A"] = "H"

    # Normalize numeric cols helper
    def num(series_name, default=None):
        if series_name not in df.columns:
            return default
        return pd.to_numeric(df[series_name], errors="coerce")

    # Quarter points: column names vary (try both variants)
    q1 = "1st" if "1st" in df.columns else ("1stQ" if "1stQ" in df.columns else None)
    q4 = "4th" if "4th" in df.columns else ("4thQ" if "4thQ" in df.columns else None)

    # Attempts/completions
    cmp_c = "Cmp" if "Cmp" in df.columns else ("Cmp.1" if "Cmp.1" in df.columns else None)
    att_c = "Att" if "Att" in df.columns else ("Att.1" if "Att.1" in df.columns else None)
    rush_att = "Rush Att" if "Rush Att" in df.columns else ("Att.2" if "Att.2" in df.columns else None)

    out = {}
    n = len(df)
    if n == 0:
        return df, out

    # Offense by quarter
    if q1: out["off_1q_pts_pg"] = num(q1).mean()
    if q4: out["off_4q_pts_pg"] = num(q4).mean()

    # Allowed by quarter (if present as opponent columns; many pages don’t expose — we can add boxscore fetch later)
    opp_q1 = "Opp 1st" if "Opp 1st" in df.columns else ("Opp1" if "Opp1" in df.columns else None)
    opp_q4 = "Opp 4th" if "Opp 4th" in df.columns else ("Opp4" if "Opp4" in df.columns else None)
    if opp_q1: out["def_1q_pts_allowed_pg"] = num(opp_q1).mean()
    if opp_q4: out["def_4q_pts_allowed_pg"] = num(opp_q4).mean()

    # Passing & rushing volume
    if rush_att: out["rush_att_pg"] = num(rush_att).mean()
    if att_c: out["pass_att_pg"] = num(att_c).mean()
    if cmp_c:
        comp = num(cmp_c)
        out["pass_comp_pg"] = comp.mean()
        if "pass_att_pg" in out and out["pass_att_pg"]:
            out["pass_comp_pct"] = (out["pass_comp_pg"] / out["pass_att_pg"]) * 100

    # Home/Road PPG
    if "Pts" in df.columns:
        pts = num("Pts")
        out["pts_pg_home"] = pts[df["H/A"]=="H"].mean()
        out["pts_pg_road"] = pts[df["H/A"]=="A"].mean()

    # Round floats to 2 decimals
    for k, v in list(out.items()):
        if v is not None and pd.notna(v):
            out[k] = round(float(v), 2)
        else:
            out[k] = None

    return df, out
