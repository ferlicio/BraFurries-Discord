from discord import Interaction, Member, app_commands
from discord.ext import commands
from core.database import admConnectTelegramAccount, mergeDiscordAccounts

class AccountCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
    
    @app_commands.command(name='adm-conectar_conta', description='Conecta sua conta do discord com a do telegram')
    async def connectAccount(self, ctx: Interaction, user: Member, telegram_username: str):
        await ctx.response.defer()
        result = admConnectTelegramAccount(ctx.guild.id, user, telegram_username)
        if result:
            return await ctx.followup.send(content='Sua conta foi conectada com sucesso! agora você pode usar os comandos do bot no discord e no telegram', ephemeral=False)
        else:
            return await ctx.followup.send(content='Não foi possível conectar sua conta! você já está conectado?', ephemeral=True)

    @app_commands.command(name='adm-associar_membro', description='Associa dois perfis do discord ao mesmo usuário do banco')
    async def linkDiscordUsers(self, ctx: Interaction, membro: Member, usuario_existente: Member):
        await ctx.response.defer()
        result = mergeDiscordAccounts(ctx.guild.id, membro, usuario_existente)
        if result:
            return await ctx.followup.send(content=f'O membro {membro.mention} foi associado ao usuário de {usuario_existente.mention}!', ephemeral=False)
        else:
            return await ctx.followup.send(content='Não foi possível associar os membros.', ephemeral=True)
        
        
async def setup(bot: commands.Bot):    await bot.add_cog(AccountCog(bot))
