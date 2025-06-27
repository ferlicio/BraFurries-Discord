from discord.ext import commands
import discord
from typing import Literal
from settings import BOT_NAME


class InteractionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @commands.command(name=f'{BOT_NAME.lower()}_diz', description=f'Faz {BOT_NAME} falar em um canal de texto')
    async def sayAsCoddy(self, ctx: discord.Interaction, channel: discord.TextChannel, message: str):
        channelId = discord.utils.get(ctx.guild.channels, name=channel.name)
        await channelId.send(message)
        resp = await ctx.response.send_message(content='mensagem enviada!', ephemeral=True)
        return resp

    @commands.command(name=f'{BOT_NAME.lower()}_status', description=f'Muda o status do {BOT_NAME}')
    async def changeMood(self, ctx: discord.Interaction, mood: Literal['jogando','ouvindo','assistindo','mensagem'], message: str):
        moodDiscord = 'playing' if mood == 'jogando' else 'listening' if mood == 'ouvindo' else 'watching'
        if mood == 'mensagem':
            await self.bot.change_presence(activity=discord.CustomActivity(name=message))
            resp = await ctx.response.send_message(content=f'{BOT_NAME} está com o status de "{message}"', ephemeral=True)
        else:
            await self.bot.change_presence(activity=discord.Activity(type=getattr(discord.ActivityType, moodDiscord), name=message))
            resp = await ctx.response.send_message(content=f'{BOT_NAME} está {mood} {message}!', ephemeral=True)
        return resp
    
async def setup(bot: commands.Bot):
    await bot.add_cog(InteractionsCog(bot))
