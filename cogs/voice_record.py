from discord.ext import commands, tasks
import discord
from datetime import datetime
from core.time_functions import now
from core.database import connectToDatabase, endConnectionWithCommit, addVoiceTime
from settings import DISCORD_GUILD_ID


class VoiceRecordCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_sessions: dict[int, datetime] = {}
        super().__init__()
        self.save_call_time.start()

    def cog_unload(self):
        self.save_call_time.cancel()

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
                addVoiceTime(mydb, member.guild.id, member, seconds)
                endConnectionWithCommit(mydb)
        # Member switched channels
        elif before.channel != after.channel:
            start = self.voice_sessions.get(member.id)
            if start:
                seconds = int((now() - start).total_seconds())
                mydb = connectToDatabase()
                addVoiceTime(mydb, member.guild.id, member, seconds)
                endConnectionWithCommit(mydb)
            self.voice_sessions[member.id] = now()

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
                addVoiceTime(mydb, guild.id, member, seconds)
                self.voice_sessions[user_id] = now()
        endConnectionWithCommit(mydb)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceRecordCog(bot))

