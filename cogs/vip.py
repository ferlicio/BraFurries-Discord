from discord.ext import commands, tasks
from discord import app_commands
import discord
import re
from core.auxiliar_functions import edit_role_colors
from core.routine_functions import colorIsAvailable, addVipRole
from core.database import saveCustomRole
from settings import DISCORD_VIP_ROLES_ID
from core.time_functions import now


class VipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
        self.configForVips.start()

    def cog_unload(self):
        self.configForVips.cancel()
        
    @app_commands.command(name='vip-mudar_cor', description='Muda a cor do cargo VIP do membro')
    async def changeVipColor(self, ctx: discord.Interaction, cor: str):
        userVipRoles = [role.id for role in ctx.user.roles if DISCORD_VIP_ROLES_ID.__contains__(role.id)]
        if userVipRoles:
            if not re.match(r'^#(?:[a-fA-F0-9]{3}){1,2}$', cor):
                return await ctx.response.send_message(content='''# Cor invalida!\nVocê precisa informar uma cor no formato Hex (#000000).\nVocê pode procurar por uma cor em https://htmlcolorcodes.com/color-picker/ e testa-la usando o comando "?color #000000"''', ephemeral=False)
            if not await colorIsAvailable(cor):
                return await ctx.response.send_message(content='''Cor inválida! você precisa informar uma cor que não seja muito parecida com a cor de algum cargo da staff''', ephemeral=True)
            corFormatada = int(cor.replace('#','0x'),16)
            customRole = await addVipRole(ctx)
            await customRole.edit(color=corFormatada)
            await ctx.response.send_message(content=f'Cor do cargo VIP alterada para {cor} com sucesso!', ephemeral=False)
            return saveCustomRole(ctx.guild_id, ctx.user, color=corFormatada)
        return await ctx.response.send_message(content='Você não é vip! você não pode fazer isso', ephemeral=True)

    @app_commands.command(name='vip-mudar_icone', description='Muda o icone do cargo VIP do membro')
    async def changeVipIcon(self, ctx: discord.Interaction, icon: str):
        userVipRoles = [role.id for role in ctx.user.roles if DISCORD_VIP_ROLES_ID.__contains__(role.id)]
        if userVipRoles:
            try:
                customRole = await addVipRole(ctx)
                if '<' in icon or '>' in icon or ':' in icon:
                    try:
                        emoji = ctx.guild.get_emoji(int(icon.replace('<','').replace('>','').split(':')[2]))
                    except:
                        return await ctx.response.send_message(content='''Ícone inválido! apenas emojis do servidor são permitidos''', ephemeral=True)
                    icon = await emoji.read()
                await customRole.edit(display_icon=icon)
                await ctx.response.send_message(content='Ícone do cargo VIP alterado com sucesso!', ephemeral=False)
                if 'emoji' in locals() and emoji is not None:
                    return saveCustomRole(ctx.guild_id, ctx.user, iconId=emoji.id)
                return saveCustomRole(ctx.guild_id, ctx.user, iconId=None)
            except Exception as e:
                print(e)
                return await ctx.response.send_message(content='''Algo deu errado, avise o titio sobre!''', ephemeral=True)
        return await ctx.response.send_message(content='Você não é vip! você não pode fazer isso', ephemeral=True)
    
    @app_commands.command(name='vip-customizar', description='customiza o cargo VIP do membro')
    async def customizeVipRole(self, ctx: discord.Interaction, cor: str = None, cor2: str = None, icone: str = None):
        if cor is None and cor2 is None and icone is None:
            return await ctx.response.send_message(content='Você precisa informar pelo menos uma cor ou um ícone para customizar o cargo VIP', ephemeral=True)
        userVipRoles = [role.id for role in ctx.user.roles if DISCORD_VIP_ROLES_ID.__contains__(role.id)]
        if userVipRoles:
            if cor is not None:
                if not re.match(r'^#(?:[a-fA-F0-9]{3}){1,2}$', cor):
                    return await ctx.response.send_message(content='''# Cor invalida!\nVocê precisa informar uma cor no formato Hex (#000000).\nVocê pode procurar por uma cor em https://htmlcolorcodes.com/color-picker/ e testa-la usando o comando "?color #000000"''', ephemeral=False)
                if not await colorIsAvailable(cor):
                    return await ctx.response.send_message(content='''Cor inválida! você precisa informar uma cor que não seja muito parecida com a cor de algum cargo da staff''', ephemeral=True)
            if icone is not None:
                if '<' in icone or '>' in icone or ':' in icone:
                    try:
                        emoji = ctx.guild.get_emoji(int(icone.replace('<','').replace('>','').split(':')[2]))
                    except:
                        return await ctx.response.send_message(content='''Ícone inválido! apenas emojis do servidor são permitidos''', ephemeral=True)
                    icone_bytes = await emoji.read()
            await ctx.response.defer()
            customRole = await addVipRole(ctx)
            colors = [cor, cor2]
            colors = [c for c in colors if c is not None]
            if colors:
                try:
                    await edit_role_colors(self.bot, customRole, colors)
                except Exception as e:
                    print(e)
                    return await ctx.followup.send(content='''Algo deu errado ao mudar a cor do cargo VIP, avise o titio sobre!''', ephemeral=False)
            if icone is not None:
                try:
                    await customRole.edit(display_icon=icone_bytes)
                except Exception as e:
                    print(e)
                    return await ctx.followup.send(content='''Algo deu errado ao mudar o ícone do cargo VIP, avise o titio sobre!''', ephemeral=False)
            await ctx.followup.send(content=f'Cargo VIP personalizado com sucesso! \n- Cores: {colors}, \n- Ícone: {icone}', ephemeral=False)
            return saveCustomRole(ctx.guild_id, ctx.user, color=colors, iconId=emoji.id if 'emoji' in locals() and emoji is not None else None)
        return

    @tasks.loop(hours=1)
    async def configForVips(self):
        if now().hour == 3:
            guild = bot.get_guild(DISCORD_GUILD_ID)
            vip_roles = getVIPConfigurations(guild)['VIPRoles']
            vip_role_ids = [r.id for r in vip_roles]

            if not vip_roles:
                print(f'Não foi possível encontrar um cargo VIP no servidor {guild.name}')
                return

            for role in guild.roles:
                if DISCORD_VIP_CUSTOM_ROLE_PREFIX in role.name:
                    if role.color == discord.Color.default() and role.display_icon is None:
                        await role.delete()
                        continue

                    for serverMember in list(role.members):
                        member_role_ids = [r.id for r in serverMember.roles]
                        if not any(vip_id in member_role_ids for vip_id in vip_role_ids):
                            await serverMember.remove_roles(role)

                    if len(role.members) == 0:
                        match = re.search(rf'{re.escape(DISCORD_VIP_CUSTOM_ROLE_PREFIX)} (.*)', role.name)
                        member = guild.get_member_named(match.group(1)) if match else None
                        if member and any(vip_id in [r.id for r in member.roles] for vip_id in vip_role_ids):
                            await member.add_roles(role)
                        else:
                            await role.delete()
                            continue
                    else:
                        member = role.members[0]
                        for extra in role.members[1:]:
                            await extra.remove_roles(role)

                    expected_name = f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {member.name}"
                    if role.name != expected_name:
                        await role.edit(name=expected_name)

                    hexColor = '#%02x%02x%02x' % (role.color.r, role.color.g, role.color.b)
                    saveCustomRole(guild.id, member, int(str(hexColor).replace('#','0x'),16))


async def setup(bot: commands.Bot):
    await bot.add_cog(VipCog(bot))