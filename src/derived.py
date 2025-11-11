# src/derived.py

"""
Compute derived metrics that need season splits / game logs.

Right now:
- NFL 34: Home points per game
- NFL 35: Road points per game
- NFL 36: League-wide baseline QB rating (constant for now)

We reuse ESPN's statistics endpoint via team_stats._fetch_team_stats.
If a key is missing for a team, we simply skip it.
"""

from .team_stats import _fetch_team_stats, TEAM_IDS


def _first_existing(raw: dict, keys: list[str]):
    """Return first raw[k] that exists and is numeric-like."""
    for k in keys:
        v = raw.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def get_home_road_ppg() -> dict:
    """
    Returns:
        {
          "DAL": {"NFL 34": home_ppg, "NFL 35": road_ppg, "NFL 36": 90.0},
          ...
        }

    Safe:
    - If we can't find the needed fields for a team, we just don't add that team.
    - main.py will leave those NFL columns blank for that team.
    """
    results: dict[str, dict] = {}

    for abbr in TEAM_IDS.keys():
        raw = _fetch_team_stats(abbr)
        if not raw:
            continue

        # These keys are based on ESPN stats JSON naming patterns.
        # We try multiple variants to be robust.
        home_pts = _first_existing(
            raw,
            [
                "homePointsFor",
                "pointsForHome",
                "homePointsScored",
                "pointsScoredHome",
            ],
        )
        home_g = _first_existing(
            raw,
            [
                "homeGamesPlayed",
                "homeGames",
                "gamesPlayedHome",
            ],
        )

        road_pts = _first_existing(
            raw,
            [
                "roadPointsFor",
                "pointsForAway",
                "roadPointsScored",
                "pointsScoredAway",
            ],
        )
        road_g = _first_existing(
            raw,
            [
                "roadGamesPlayed",
                "roadGames",
                "gamesPlayedAway",
            ],
        )

        row: dict = {}

        if home_pts is not None and home_g and home_g > 0:
            row["NFL 34"] = round(home_pts / home_g, 2)

        if road_pts is not None and road_g and road_g > 0:
            row["NFL 35"] = round(road_pts / road_g, 2)

        # Baseline league QB rating constant for now
        # (John: "quarterback rating, per league")
        row["NFL 36"] = 90.0

        if row:
            results[abbr] = row

    print(f"[derived] computed home/road PPG for {len(results)} teams")
    return results
