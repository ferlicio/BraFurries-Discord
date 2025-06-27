from discord import Interaction, Member
from discord.ext import commands
from core.database import admConnectTelegramAccount

class AccountCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
    
    @commands.command(name='adm-conectar_conta', description='Conecta sua conta do discord com a do telegram')
    async def connectAccount(ctx: Interaction, user: Member, telegram_username: str):
        await ctx.response.defer()
        result = admConnectTelegramAccount(ctx.guild.id, user, telegram_username)
        if result:
            return await ctx.followup.send(content='Sua conta foi conectada com sucesso! agora você pode usar os comandos do bot no discord e no telegram', ephemeral=False)
        else:
            return await ctx.followup.send(content='Não foi possível conectar sua conta! você já está conectado?', ephemeral=True)
        
        
async def setup(bot: commands.Bot):
    await bot.add_cog(AccountCog(bot))