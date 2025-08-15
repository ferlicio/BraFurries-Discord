import discord
from datetime import datetime

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

    channel = guild.get_channel(int(config["log_channel"]))
    if channel is None:
        return

    embed = discord.Embed(
        title="Alteração de perfil",
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )
    embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    embed.set_footer(text=f"ID: {user.id}")

    for field, (before_value, after_value) in changes.items():
        embed.add_field(
            name=field,
            value=f"{before_value or 'N/A'} -> {after_value or 'N/A'}",
            inline=False,
        )

    await channel.send(embed=embed)


