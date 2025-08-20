from discord.ext import commands
import discord
from discord import app_commands
from typing import Literal
from datetime import datetime
from core.database import includeLocale, getAllLocals, getUsersByLocale
from core.database import includeBirthday, getAllBirthdays
from core.database import pooled_connection
from schemas.models.locals import StateAbbrev
from core.verifications import verifyDate



class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name='registrar_local', description='Registra o seu local')
    @app_commands.describe(local='Abreviação do estado')
    async def registerLocal(self, ctx: discord.Interaction, local: StateAbbrev):
        availableLocals = getAllLocals()
        await ctx.response.defer()
        result = includeLocale(ctx.guild.id, local, ctx.user, availableLocals)
        if result:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local:
                    return await ctx.followup.send(content=f'você foi registrado em {locale["locale_name"]}!', ephemeral=False)
        else:
            return await ctx.followup.send(content=f'Não foi possível registrar você! você já está registrado em algum local?', ephemeral=True)

    @app_commands.command(name='furros_na_area', description='Lista todos os furries registrados em um local')
    @app_commands.describe(local='Abreviação do estado')
    async def listFurries(self, ctx: discord.Interaction, local: StateAbbrev):
        availableLocals = getAllLocals()
        await ctx.response.defer()
        result = getUsersByLocale(local, availableLocals)
        if result:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local:
                    membersResponse = ',\n'.join(member for member in result)
                    return await ctx.followup.send(content=f'''Aqui estão os furros registrados em {locale["locale_name"]}:```{membersResponse}```''')
        else:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local:
                    return await ctx.followup.send(content=f'Não há furros registrados em {locale["locale_name"]}... que tal ser o primeiro? :3')

    @app_commands.command(name='registrar_aniversario', description='Registra seu aniversário')
    async def registerBirthday(self, ctx: discord.Interaction, data: str, mencionavel: Literal["sim", "não"]):
        birthdayAsDate = verifyDate(data)
        if not birthdayAsDate:
            return await ctx.response.send_message(content='''Data de nascimento inválida! Você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)

        mencionavel = True if mencionavel == "sim" else False
        await ctx.response.defer()
        try:
            registered = includeBirthday(ctx.guild.id, birthdayAsDate, ctx.user, mencionavel, None, True)
            if registered:
                return await ctx.followup.send(content=f'você foi registrado com o aniversário {birthdayAsDate.day:02}/{birthdayAsDate.month:02}!', ephemeral=False)
            else:
                return await ctx.followup.send(content=f'Algo deu errado... Avise o titio!', ephemeral=False)
        except ValueError as e:
            # invalid birthdate range or type
            return await ctx.followup.send(content=f'Data de nascimento inválida! {e}', ephemeral=True)
        except Exception as e:
            if str(e).__contains__('Duplicate entry'):
                return await ctx.followup.send(content=f'Você ja está registrado. Caso o seu aniversário não esteja aparecendo na lista, tente usar /{ctx.command.name} com mencionável = Sim', ephemeral=True)
            if str(e).__contains__('Changed Entry'):
                if mencionavel:
                    return await ctx.followup.send(content=f'Seu aniversário foi atualizado para ser mencionável!', ephemeral=False)
                else:
                    return await ctx.followup.send(content=f'Seu aniversário foi atualizado para não ser mencionável!', ephemeral=False)
            return await ctx.followup.send(content=f'Algo deu errado... Avise o titio!', ephemeral=False)

    @app_commands.command(name='aniversarios', description='Lista todos os aniversários registrados')
    async def listBirthdays(self, ctx: discord.Interaction):
        await ctx.response.defer()
        result = getAllBirthdays()
        if result:
            for birthday in result:
                birthday['user'] = ctx.guild.get_member(birthday['user_id'])
            birthdaysResponse = ',\n'.join(
                f"{birthday['birth_date'].strftime('%d/%m')} - {birthday['user'].display_name}"
                for birthday in sorted(result, key=lambda birthday: (birthday['birth_date'].month, birthday['birth_date'].day)) if birthday['user'] != None)
            return await ctx.followup.send(content=f'Aqui estão os aniversários registrados:```{birthdaysResponse}```')
        else:
            return await ctx.followup.send(content=f'Não há aniversários registrados... que tal ser o primeiro? :3')

async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))
