from discord.ext import commands, tasks
import discord
from discord import app_commands
from datetime import datetime, timedelta
from core.time_functions import now
from core.database import (
    connectToDatabase,
    endConnectionWithCommit,
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
    async def showRecords(self, ctx: discord.Interaction, tipo: RecordTypes | None = None):
        await ctx.response.defer()
        if tipo is None or tipo == "Tempo em call":
            records = getAllVoiceRecords(ctx.guild.id)
            if not records:
                await ctx.followup.send(content='Nenhum recorde registrado.')
                return
            lines = []
            for record in records:
                member = ctx.guild.get_member(record['user_id'])
                if member is None:
                    continue
                duration = str(timedelta(seconds=record['seconds']))
                lines.append(f'{member.display_name} - {duration}')
            await ctx.followup.send(content='Recordes de tempo em call:\n' + '\n'.join(lines))
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
                mydb = connectToDatabase()
                updateVoiceRecord(mydb, member.guild.id, member, seconds)
                endConnectionWithCommit(mydb)
        # Member switched channels
        elif before.channel != after.channel:
            start = self.voice_sessions.get(member.id)
            if start:
                seconds = int((now() - start).total_seconds())
                mydb = connectToDatabase()
                updateVoiceRecord(mydb, member.guild.id, member, seconds)
                endConnectionWithCommit(mydb)

    @tasks.loop(minutes=5)
    async def save_call_time(self):
        if not self.voice_sessions:
            return
        guild = self.bot.get_guild(DISCORD_GUILD_ID)
        if guild is None:
            return
        mydb = connectToDatabase()
        for user_id, start in list(self.voice_sessions.items()):
            member = guild.get_member(user_id)
            if member is None:
                continue
            seconds = int((now() - start).total_seconds())
            if seconds > 0:
                updateVoiceRecord(mydb, guild.id, member, seconds)
        endConnectionWithCommit(mydb)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecordsCog(bot))

