import discord
from datetime import datetime
from core.time_functions import now

from core.database import getLogConfig

def checkRolesUpdate(before:discord.member.Member, after:discord.member.Member):
    if before.roles != after.roles:
        todosCargos = before.roles + after.roles
        #vamos remover os cargos repetidos e @everyone
        todosCargos = list(dict.fromkeys(todosCargos))
        todosCargos.remove(after.guild.default_role)
        cargosAlterados = {'adicionados': [], 'removidos': []}
        #agora vamos percorrer a lista de cargos e ver quais foram adicionados e quais foram removidos
        for cargo in todosCargos:
            if not before.roles.__contains__(cargo):
                cargosAlterados['adicionados'].append(cargo)
            if not after.roles.__contains__(cargo):
                cargosAlterados['removidos'].append(cargo)
        ##print(f'Os cargos alterados foram: {cargosAlterados}')
        return cargosAlterados
    else:
        return False


async def logProfileChange(bot: discord.Client, guild: discord.Guild, user: discord.abc.User, changes: dict):
    """Send a profile update log message if logging is enabled."""
    config = getLogConfig(guild.id, "profile")
    if not config or not config.get("enabled") or not config.get("log_channel"):
        return

    channel = guild.get_channel_or_thread(int(config["log_channel"]))
    if channel is None:
        return

    embed = discord.Embed(
        title="Alteração de perfil",
        color=discord.Color.blurple(),
        timestamp=now()
    )
    embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    embed.set_footer(text=f"ID: {user.id}")

    for field, (before_value, after_value) in changes.items():
        embed.add_field(
            name=field,
            value=f"{before_value or 'N/A'} -> {after_value or 'N/A'}",
            inline=False,
        )

    if isinstance(channel, (discord.TextChannel, discord.Thread)):
        await channel.send(embed=embed)


async def logWarn(
    guild: discord.Guild,
    member: discord.abc.User,
    moderator: discord.abc.User,
    reason: str,
    warnings_count: int,
):
    """Send a warn log message if logging is enabled for this guild."""
    config = getLogConfig(guild.id, "warn")
    if not config or not config.get("enabled") or not config.get("log_channel"):
        return

    channel = guild.get_channel_or_thread(int(config["log_channel"]))
    if channel is None:
        return

    embed = discord.Embed(
        title="Warn aplicado",
        color=discord.Color.orange(),
        timestamp=now(),
    )
    embed.add_field(name="Membro", value=f"{member.mention} ({member.id})", inline=True)
    embed.add_field(name="Total de warns", value=str(warnings_count), inline=True)
    embed.add_field(name="Motivo", value=reason or "N/A", inline=False)
    embed.add_field(name="Moderador", value=moderator.mention, inline=False)
    embed.set_footer(text=f"ID: {member.id}")

    if isinstance(channel, (discord.TextChannel, discord.Thread)):
        await channel.send(embed=embed)


def getStaffRoles(guild: discord.Guild) -> list[discord.Role]:
    """Return roles considered staff for moderation commands.

    This is a temporary mock that grants staff permissions to the roles
    with the IDs 1100331034542886933, 775483946501799947 and
    829140185777307658. Once role configuration is stored in the database
    this helper should be updated to fetch that information dynamically.
    """

    role_ids = (
        1100331034542886933,
        775483946501799947,
        829140185777307658,
    )
    roles: list[discord.Role] = []
    for role_id in role_ids:
        role = guild.get_role(role_id)
        if role is not None:
            roles.append(role)
    return roles


