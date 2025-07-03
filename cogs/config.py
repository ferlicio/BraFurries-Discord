from discord import Interaction, app_commands
from discord.ext import commands
from schemas.types.server_messages import ServerMessages
from core.database import setServerMessage

class ConfigCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name='mensagens_servidor', description='Configure as mensagens especificas do servidor')
    async def changeMessages(self, ctx: Interaction, tipo: ServerMessages, mensagem: str):
        if tipo == 'Aniversário':
            updated = setServerMessage(ctx.guild_id, 'birthday', mensagem)
        elif tipo == 'Bump':
            updated = setServerMessage(ctx.guild_id, 'bump', mensagem)
        if not updated:
            return await ctx.response.send_message(content=f'Não foi possível alterar a mensagem de {tipo}', ephemeral=True)
        return await ctx.response.send_message(content=f'Mensagem de {tipo} alterada com sucesso!', ephemeral=True)
    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCog(bot))