from discord.ext import commands
import discord
from typing import Literal
from settings import BOT_NAME


def setup(bot: commands.Bot):
    @bot.tree.command(name=f'{BOT_NAME.lower()}_diz', description=f'Faz {BOT_NAME} falar em um canal de texto')
    async def sayAsCoddy(ctx: discord.Interaction, channel: discord.TextChannel, message: str):
        channelId = discord.utils.get(ctx.guild.channels, name=channel.name)
        await channelId.send(message)
        resp = await ctx.response.send_message(content='mensagem enviada!', ephemeral=True)
        return resp

    @bot.tree.command(name=f'{BOT_NAME.lower()}_status', description=f'Muda o status do {BOT_NAME}')
    async def changeMood(ctx: discord.Interaction, mood: Literal['jogando','ouvindo','assistindo','mensagem'], message: str):
        moodDiscord = 'playing' if mood == 'jogando' else 'listening' if mood == 'ouvindo' else 'watching'
        if mood == 'mensagem':
            await bot.change_presence(activity=discord.CustomActivity(name=message))
            resp = await ctx.response.send_message(content=f'{BOT_NAME} está com o status de "{message}"', ephemeral=True)
        else:
            await bot.change_presence(activity=discord.Activity(type=getattr(discord.ActivityType, moodDiscord), name=message))
            resp = await ctx.response.send_message(content=f'{BOT_NAME} está {mood}{message}!', ephemeral=True)
        return resp
