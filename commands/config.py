from discord import Interaction, commands
from schemas.types.server_messages import ServerMessages
from core.database import setServerMessage


def setup(bot: commands.Bot):
    @bot.tree.command(name='mensagens_servidor', description='Configure as mensagens especificas do servidor')
    async def changeMessages(ctx: Interaction, tipo: ServerMessages, mensagem: str):
        if tipo == 'Aniversário':
            updated = setServerMessage(ctx.guild_id, 'birthday', mensagem)
        elif tipo == 'Bump':
            updated = setServerMessage(ctx.guild_id, 'bump', mensagem)
        if not updated:
            return await ctx.response.send_message(content=f'Não foi possível alterar a mensagem de {tipo}', ephemeral=True)
        return await ctx.response.send_message(content=f'Mensagem de {tipo} alterada com sucesso!', ephemeral=True)