from discord.ext import commands, tasks
from discord import app_commands
import discord
import re
from core.routine_functions import colorIsAvailable, addVipRole, getVIPConfigurations
from core.database import saveCustomRole
from schemas.models.bot import MyBot
from settings import *


class VipCog(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot
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
        
    
    @tasks.loop(hours=24)
    async def configForVips(self):
        guild = self.bot.get_guild(self.bot.config[0].guildId)
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