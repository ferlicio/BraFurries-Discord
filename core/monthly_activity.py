from datetime import datetime, timedelta
from typing import Dict, List

from dateutil import relativedelta

from core.database import pooled_connection


def current_month() -> str:
    """Return the current month formatted as YYYY-MM."""
    return datetime.now().strftime('%Y-%m')


def current_week() -> str:
    """Return the start date of the current week formatted as YYYY-MM-DD."""
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    return monday.strftime('%Y-%m-%d')


def previous_months(amount: int) -> List[str]:
    """Return a list of the last ``amount`` months including the current one."""
    months: List[str] = []
    now = datetime.now()
    for i in range(amount):
        dt = now - relativedelta.relativedelta(months=i)
        months.append(dt.strftime('%Y-%m'))
    return months


def add_time(game: str, seconds: int, month: str | None = None, week: str | None = None) -> None:
    """Record play time for a game in the given month and week."""
    month = month or current_month()
    week = week or current_week()
    with pooled_connection() as cursor:
        sql_month = """
        INSERT INTO stats_monthly_game_activity (month, game_name, seconds)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE seconds = seconds + VALUES(seconds);
        """
        cursor.execute(sql_month, (month, game, seconds))
        sql_week = """
        INSERT INTO stats_weekly_game_activity (week, game_name, seconds)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE seconds = seconds + VALUES(seconds);
        """
        cursor.execute(sql_week, (week, game, seconds))


def get_trending_games(month: str | None = None) -> Dict[str, int]:
    """Return a mapping of game names to total seconds for the given month."""
    month = month or current_month()
    with pooled_connection() as cursor:
        sql = """
        SELECT game_name, seconds
          FROM stats_monthly_game_activity
         WHERE month = %s
         ORDER BY seconds DESC;
        """
        cursor.execute(sql, (month,))
        rows = cursor.fetchall()
        return {row["game_name"]: row["seconds"] for row in rows}


def get_total_games() -> Dict[str, int]:
    """Return total seconds played for each game across all months."""
    with pooled_connection() as cursor:
        sql = """
        SELECT game_name, SUM(seconds) AS total
          FROM stats_monthly_game_activity
         GROUP BY game_name
         ORDER BY total DESC;
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        return {row["game_name"]: row["total"] for row in rows}


def get_games_for_months(months: List[str]) -> Dict[str, int]:
    """Return the total seconds played for the given list of months."""
    if not months:
        return {}
    placeholders = ", ".join(["%s"] * len(months))
    with pooled_connection() as cursor:
        sql = f"""
        SELECT game_name, SUM(seconds) AS total
          FROM stats_monthly_game_activity
         WHERE month IN ({placeholders})
         GROUP BY game_name
         ORDER BY total DESC;
        """
        cursor.execute(sql, months)
        rows = cursor.fetchall()
        return {row["game_name"]: row["total"] for row in rows}


def cleanup_old_weekly_entries(max_age_weeks: int = 4) -> None:
    """Delete weekly records older than ``max_age_weeks`` weeks."""
    threshold = datetime.now() - timedelta(weeks=max_age_weeks)
    monday = threshold - timedelta(days=threshold.weekday())
    limit = monday.strftime('%Y-%m-%d')
    with pooled_connection() as cursor:
        sql = """
        DELETE FROM stats_weekly_game_activity
              WHERE week < %s;
        """
        cursor.execute(sql, (limit,))
