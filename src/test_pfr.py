from .sources.pfr import team_game_log_year
if __name__ == "__main__":
    df, agg = team_game_log_year("DAL", 2025)
    print("rows:", len(df), "agg:", agg)
