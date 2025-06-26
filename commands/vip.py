from discord.ext import commands
import discord
import re
from core.verifications import colorIsAvailable, addVipRole
from core.database import saveCustomRole
from settings import DISCORD_VIP_ROLES_ID


def setup(bot: commands.Bot):
    @bot.tree.command(name='vip-mudar_cor', description='Muda a cor do cargo VIP do membro')
    async def changeVipColor(ctx: discord.Interaction, cor: str):
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

    @bot.tree.command(name='vip-mudar_icone', description='Muda o icone do cargo VIP do membro')
    async def changeVipIcon(ctx: discord.Interaction, icon: str):
        userVipRoles = [role.id for role in ctx.user.roles if DISCORD_VIP_ROLES_ID.__contains__(role.id)]
        if userVipRoles.__len__() != 0:
            try:
                customRole = await addVipRole(ctx)
                if icon.__contains__('<') or icon.__contains__('>') or icon.__contains__(':'):
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
