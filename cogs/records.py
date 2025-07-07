from discord.ext import commands, tasks
import discord
from discord import app_commands
from datetime import datetime, timedelta
from core.time_functions import now
from core.database import (
    updateVoiceRecord,
    getAllVoiceRecords,
    updateGameRecord,
    getAllGameRecords,
    getBlacklistedGames,
    addGameToBlacklist,
)
from schemas.types.record_types import RecordTypes
from settings import DISCORD_GUILD_ID


class RecordsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_sessions: dict[int, datetime] = {}
        self.game_sessions: dict[int, tuple[datetime, str]] = {}
        self.blacklisted_games: set[str] = set(getBlacklistedGames(DISCORD_GUILD_ID))
        super().__init__()
        self.save_records.start()

    def cog_unload(self):
        self.save_records.cancel()

    @app_commands.command(name='recordes', description='Mostra os recordes do servidor')
    async def showRecords(self, ctx: discord.Interaction, tipo: RecordTypes = None):
        await ctx.response.defer()
        if tipo == "Tempo em call":
            records = getAllVoiceRecords(ctx.guild.id, limit=10)
            if not records:
                await ctx.followup.send(content='Nenhum recorde registrado.')
                return

            embed = discord.Embed(
                title='Recordes de tempo em call',
                color=discord.Color.blue(),
            )

            for index, record in enumerate(records, start=1):
                member = ctx.guild.get_member(record['user_id'])
                if member is None:
                    continue
                duration = str(timedelta(seconds=record['seconds']))
                embed.add_field(
                    name=f'{index}. {member.display_name}',
                    value=duration,
                    inline=False
                )

            await ctx.followup.send(embed=embed)
        elif tipo == "Tempo em jogo":
            records = getAllGameRecords(ctx.guild.id, limit=10, blacklist=list(self.blacklisted_games))
            if not records:
                await ctx.followup.send(content='Nenhum recorde registrado.')
                return

            embed = discord.Embed(
                title='Recordes de tempo em jogo',
                color=discord.Color.blue(),
            )

            for index, record in enumerate(records, start=1):
                member = ctx.guild.get_member(record['user_id'])
                if member is None:
                    continue
                duration = str(timedelta(seconds=record['seconds']))
                game_name = record.get('game', '')
                display = f'{member.display_name} - {game_name}' if game_name else member.display_name
                embed.add_field(
                    name=f'{index}. {display}',
                    value=duration,
                    inline=False
                )

            await ctx.followup.send(embed=embed)
        else:
            voice_records = getAllVoiceRecords(ctx.guild.id, limit=3)
            game_records = getAllGameRecords(ctx.guild.id, limit=3, blacklist=list(self.blacklisted_games))
            if not voice_records and not game_records:
                await ctx.followup.send(content='Nenhum recorde registrado.')
                return

            embed = discord.Embed(
                title='Recordes do servidor',
                color=discord.Color.blue(),
            )

            if voice_records:
                embed.add_field(name='Tempo em call', value='\u200b', inline=False)
                for index, record in enumerate(voice_records, start=1):
                    member = ctx.guild.get_member(record['user_id'])
                    if member is None:
                        continue
                    duration = str(timedelta(seconds=record['seconds']))
                    embed.add_field(
                        name=f'{index}. {member.display_name}',
                        value=duration,
                        inline=False
                    )

            if game_records:
                embed.add_field(name='Tempo em jogo', value='\u200b', inline=False)
                for index, record in enumerate(game_records, start=1):
                    member = ctx.guild.get_member(record['user_id'])
                    if member is None:
                        continue
                    duration = str(timedelta(seconds=record['seconds']))
                    game_name = record.get('game', '')
                    display = f'{member.display_name} - {game_name}' if game_name else member.display_name
                    embed.add_field(
                        name=f'{index}. {display}',
                        value=duration,
                        inline=False
                    )

            await ctx.followup.send(embed=embed)

    @app_commands.command(name='recorde_adicionar_blacklist', description='Adiciona um jogo à blacklist de recordes')
    async def addRecordBlacklist(self, ctx: discord.Interaction, *, jogo: str):
        await ctx.response.defer()
        if addGameToBlacklist(ctx.guild.id, jogo):
            self.blacklisted_games.add(jogo)
            # remove any ongoing sessions for this game
            for user_id, (start, game_name) in list(self.game_sessions.items()):
                if game_name == jogo:
                    self.game_sessions.pop(user_id, None)
            await ctx.followup.send(content=f'Jogo "{jogo}" adicionado à blacklist!')
        else:
            await ctx.followup.send(content='Não foi possível adicionar o jogo à blacklist.', ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Member joined a voice channel
        if before.channel is None and after.channel is not None:
            self.voice_sessions[member.id] = now()
        # Member left voice channel
        elif before.channel is not None and after.channel is None:
            start = self.voice_sessions.pop(member.id, None)
            if start:
                seconds = int((now() - start).total_seconds())
                updateVoiceRecord(member.guild.id, member, seconds)
        # Member switched channels
        elif before.channel != after.channel:
            start = self.voice_sessions.get(member.id)
            if start:
                seconds = int((now() - start).total_seconds())
                updateVoiceRecord(member.guild.id, member, seconds)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        before_game = next((a.name for a in before.activities if a.type == discord.ActivityType.playing), None)
        after_game = next((a.name for a in after.activities if a.type == discord.ActivityType.playing), None)
        if before_game in self.blacklisted_games:
            before_game = None
        if after_game in self.blacklisted_games:
            after_game = None
        if before_game is None and after_game is not None:
            self.game_sessions[after.id] = (now(), after_game)
        elif before_game is not None and after_game is None:
            session = self.game_sessions.pop(after.id, None)
            if session:
                start, game_name = session
                seconds = int((now() - start).total_seconds())
                updateGameRecord(after.guild.id, after, seconds, game_name)
        elif before_game != after_game:
            session = self.game_sessions.pop(after.id, None)
            if session:
                start, game_name = session
                seconds = int((now() - start).total_seconds())
                updateGameRecord(after.guild.id, after, seconds, game_name)
            if after_game is not None:
                self.game_sessions[after.id] = (now(), after_game)

    @tasks.loop(minutes=5)
    async def save_records(self):
        if not self.voice_sessions and not self.game_sessions:
            return
        guild = self.bot.get_guild(DISCORD_GUILD_ID)
        if guild is None:
            return
        for user_id, start in list(self.voice_sessions.items()):
            member = guild.get_member(user_id)
            if member is None:
                continue
            seconds = int((now() - start).total_seconds())
            if seconds > 0:
                updateVoiceRecord(guild.id, member, seconds)
        for user_id, (start, game_name) in list(self.game_sessions.items()):
            member = guild.get_member(user_id)
            if member is None:
                continue
            if game_name in self.blacklisted_games:
                continue
            seconds = int((now() - start).total_seconds())
            if seconds > 0:
                updateGameRecord(guild.id, member, seconds, game_name)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecordsCog(bot))

