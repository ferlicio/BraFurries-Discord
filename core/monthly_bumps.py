from typing import Dict

from core.database import pooled_connection


def save_monthly_bumps(guild_id: int, bumps: Dict[int, int]) -> None:
    """Persist bump counts in the ``user_records`` table."""
    with pooled_connection() as cursor:
        sql = (
            "INSERT INTO user_records (server_guild_id, user_id, bumps) "
            "VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE bumps = VALUES(bumps);"
        )
        for user_id, count in bumps.items():
            cursor.execute(sql, (guild_id, user_id, count))


def get_monthly_bump_records(
    guild_id: int, limit: int = 10
) -> list[dict]:
    """Return top bump records sorted by bump count."""
    with pooled_connection() as cursor:
        sql = (
            "SELECT discord_user.discord_user_id, r.bumps AS bumps "
            "FROM user_records AS r "
            "JOIN discord_user ON discord_user.user_id = r.user_id "
            "WHERE r.server_guild_id = %s AND r.bumps IS NOT NULL "
            "ORDER BY r.bumps DESC "
            "LIMIT %s;"
        )
        cursor.execute(sql, (guild_id, limit))
        rows = cursor.fetchall()
        return [
            {"user_id": row["discord_user_id"], "bumps": row["bumps"]}
            for row in rows
        ]
