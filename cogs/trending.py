from discord.ext import commands, tasks
import discord
from discord import app_commands
from datetime import datetime, timedelta
from typing import Literal

from core.time_functions import now
from core.monthly_activity import (
    add_time,
    get_trending_games,
    get_total_games,
    get_games_for_months,
    previous_months,
    current_month,
    cleanup_old_weekly_entries,
)
from settings import DISCORD_GUILD_ID

class TrendingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Store active game sessions by guild and member
        # Key is a tuple (guild_id, user_id) so presence updates from
        # different servers do not overwrite each other.
        self.sessions: dict[tuple[int, int], tuple[datetime, str]] = {}
        super().__init__()
        self.save_activity.start()
        self.cleanup_weekly.start()

    def cog_unload(self):
        self.save_activity.cancel()
        self.cleanup_weekly.cancel()

    @app_commands.command(name='atividades_em_alta', description='Mostra os jogos mais jogados do mês')
    async def showTrending(self, ctx: discord.Interaction):
        await ctx.response.defer()
        games = get_trending_games(ctx.guild.id)
        if not games:
            await ctx.followup.send(content='Nenhuma atividade registrada neste mês.')
            return
        sorted_games = sorted(games.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title='Jogos em alta', color=discord.Color.green())
        for index, (name, seconds) in enumerate(sorted_games, start=1):
            duration = str(timedelta(seconds=seconds))
            embed.add_field(name=f'{index}. {name}', value=duration, inline=False)
        await ctx.followup.send(embed=embed)

    @app_commands.command(name='relatorio_atividades', description='Mostra um relatório de jogos registrados')
    async def activityReport(
        self,
        ctx: discord.Interaction,
        periodo: Literal[
            'mes_atual',
            'ultimo_mes',
            'ultimos_3_meses',
            'ultimos_6_meses',
            'ultimo_ano',
        ] = 'mes_atual',
    ):
        await ctx.response.defer()
        if periodo == 'mes_atual':
            months = [current_month()]
            title = f'Atividades de {months[0]}'
        elif periodo == 'ultimo_mes':
            months = previous_months(2)[1:]
            title = f'Atividades de {months[0]}'
        elif periodo == 'ultimos_3_meses':
            months = previous_months(3)
            title = 'Atividades dos últimos 3 meses'
        elif periodo == 'ultimos_6_meses':
            months = previous_months(6)
            title = 'Atividades dos últimos 6 meses'
        else:  # ultimo_ano
            months = previous_months(12)
            title = 'Atividades do último ano'

        games = get_games_for_months(ctx.guild.id, months)

        if not games:
            await ctx.followup.send(content='Nenhuma atividade registrada.')
            return

        sorted_games = sorted(games.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title=title, color=discord.Color.green())
        for index, (name, seconds) in enumerate(sorted_games, start=1):
            duration = str(timedelta(seconds=seconds))
            embed.add_field(name=f'{index}. {name}', value=duration, inline=False)
        await ctx.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        before_game = next((a.name for a in before.activities if a.type == discord.ActivityType.playing), None)
        after_game = next((a.name for a in after.activities if a.type == discord.ActivityType.playing), None)

        # Ignore updates outside the configured guild
        if after.guild is None or after.guild.id != DISCORD_GUILD_ID:
            return

        key = (after.guild.id, after.id)

        if before_game is None and after_game is not None:
            self.sessions[key] = (now(), after_game)
        elif before_game is not None and after_game is None:
            session = self.sessions.pop(key, None)
            if session:
                start, game_name = session
                seconds = int((now() - start).total_seconds())
                add_time(game_name, seconds, after.guild.id)
        elif before_game != after_game:
            session = self.sessions.pop(key, None)
            if session:
                start, game_name = session
                seconds = int((now() - start).total_seconds())
                add_time(game_name, seconds, after.guild.id)
            if after_game is not None:
                self.sessions[key] = (now(), after_game)

    @tasks.loop(minutes=1)
    async def save_activity(self):
        if not self.sessions:
            return
        for (guild_id, user_id), (start, game_name) in list(self.sessions.items()):
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue
            member = guild.get_member(user_id)
            if member is None:
                continue
            seconds = int((now() - start).total_seconds())
            if seconds > 0:
                add_time(game_name, seconds, guild.id)
                self.sessions[(guild_id, user_id)] = (now(), game_name)

    @tasks.loop(hours=24)
    async def cleanup_weekly(self):
        if now().weekday() != 0:
            return
        cleanup_old_weekly_entries()

async def setup(bot: commands.Bot):
    await bot.add_cog(TrendingCog(bot))
