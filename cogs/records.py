from discord.ext import commands, tasks
import discord
from discord import app_commands
from datetime import datetime, timedelta
from core.time_functions import now
from core.database import (
    updateVoiceRecord,
    getAllVoiceRecords,
)
from schemas.types.record_types import RecordTypes
from settings import DISCORD_GUILD_ID


class RecordsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_sessions: dict[int, datetime] = {}
        super().__init__()
        self.save_call_time.start()

    def cog_unload(self):
        self.save_call_time.cancel()

    @app_commands.command(name='recordes', description='Mostra os recordes do servidor')
    async def showRecords(self, ctx: discord.Interaction, tipo: RecordTypes = None):
        await ctx.response.defer()
        if tipo is None or tipo == "Tempo em call":
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
        else:
            await ctx.followup.send(content='Tipo de recorde desconhecido.', ephemeral=True)

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

    @tasks.loop(minutes=5)
    async def save_call_time(self):
        if not self.voice_sessions:
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


async def setup(bot: commands.Bot):
    await bot.add_cog(RecordsCog(bot))

