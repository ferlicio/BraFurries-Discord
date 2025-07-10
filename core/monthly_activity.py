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


def add_time(
    game: str,
    seconds: int,
    guild_id: int,
    month: str | None = None,
    week: str | None = None,
    end_time: datetime | None = None,
) -> None:
    """Record play time for a game for a guild.

    ``seconds`` represents the time elapsed since the last presence update. The
    ``end_time`` parameter is used together with the stored ``last_update``
    timestamp to ensure that only the real time difference is added to the
    accumulated total. This allows missing time to be recovered when the bot was
    offline and presence events were lost.
    """

    month = month or current_month()
    week = week or current_week()
    end_dt = end_time or datetime.now()

    with pooled_connection() as cursor:
        # Retrieve previous update times
        cursor.execute(
            "SELECT last_update FROM stats_monthly_game_activity "
            "WHERE server_guild_id = %s AND month = %s AND game_name = %s;",
            (guild_id, month, game),
        )
        row = cursor.fetchone()
        month_diff = seconds
        if row and row["last_update"]:
            month_diff = int((end_dt - row["last_update"]).total_seconds())
            if month_diff < 0:
                month_diff = 0

        cursor.execute(
            "SELECT last_update FROM stats_weekly_game_activity "
            "WHERE server_guild_id = %s AND week = %s AND game_name = %s;",
            (guild_id, week, game),
        )
        row = cursor.fetchone()
        week_diff = seconds
        if row and row["last_update"]:
            week_diff = int((end_dt - row["last_update"]).total_seconds())
            if week_diff < 0:
                week_diff = 0

        sql_month = """
        INSERT INTO stats_monthly_game_activity (server_guild_id, month, game_name, seconds, last_update)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            seconds = seconds + VALUES(seconds),
            last_update = VALUES(last_update);
        """
        cursor.execute(sql_month, (guild_id, month, game, month_diff, end_dt))

        sql_week = """
        INSERT INTO stats_weekly_game_activity (server_guild_id, week, game_name, seconds, last_update)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            seconds = seconds + VALUES(seconds),
            last_update = VALUES(last_update);
        """
        cursor.execute(sql_week, (guild_id, week, game, week_diff, end_dt))


def get_trending_games(guild_id: int, month: str = None) -> Dict[str, int]:
    """Return a mapping of game names to total seconds for a guild.

    If ``month`` is provided the data is taken from ``stats_monthly_game_activity``
    for that month. Otherwise the function aggregates the play time from the last
    four weeks stored in ``stats_weekly_game_activity``. This ensures a non empty
    result even when the current month has no entries yet.
    """
    with pooled_connection() as cursor:
        if month is not None:
            sql = """
            SELECT game_name, seconds
              FROM stats_monthly_game_activity
             WHERE server_guild_id = %s AND month = %s
             ORDER BY seconds DESC;
            """
            cursor.execute(sql, (guild_id, month))
            rows = cursor.fetchall()
            return {row["game_name"]: int(row["seconds"]) for row in rows}

        # Aggregate from the last four weeks
        now = datetime.now()
        monday = now - timedelta(days=now.weekday())
        start = monday - timedelta(weeks=3)
        start_week = start.strftime('%Y-%m-%d')
        sql = """
        SELECT game_name, SUM(seconds) AS total
          FROM stats_weekly_game_activity
         WHERE server_guild_id = %s AND week >= %s
         GROUP BY game_name
         ORDER BY total DESC;
        """
        cursor.execute(sql, (guild_id, start_week))
        rows = cursor.fetchall()
        return {row["game_name"]: int(row["total"]) for row in rows}


def get_total_games(guild_id: int) -> Dict[str, int]:
    """Return total seconds played for each game for a guild across all months."""
    with pooled_connection() as cursor:
        sql = """
        SELECT game_name, SUM(seconds) AS total
          FROM stats_monthly_game_activity
         WHERE server_guild_id = %s
         GROUP BY game_name
         ORDER BY total DESC;
        """
        cursor.execute(sql, (guild_id,))
        rows = cursor.fetchall()
        return {row["game_name"]: int(row["total"]) for row in rows}


def get_games_for_months(guild_id: int, months: List[str]) -> Dict[str, int]:
    """Return the total seconds played for the given months in a guild."""
    if not months:
        return {}
    placeholders = ", ".join(["%s"] * len(months))
    with pooled_connection() as cursor:
        sql = f"""
        SELECT game_name, SUM(seconds) AS total
          FROM stats_monthly_game_activity
         WHERE server_guild_id = %s AND month IN ({placeholders})
         GROUP BY game_name
         ORDER BY total DESC;
        """
        cursor.execute(sql, (guild_id, *months))
        rows = cursor.fetchall()
        return {row["game_name"]: int(row["total"]) for row in rows}


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
