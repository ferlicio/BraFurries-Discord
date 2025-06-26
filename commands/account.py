from discord import Interaction, Member, commands
from core.database import admConnectTelegramAccount


def setup(bot: commands.Bot):
    @bot.tree.command(name='adm-conectar_conta', description='Conecta sua conta do discord com a do telegram')
    async def connectAccount(ctx: Interaction, user: Member, telegram_username: str):
        await ctx.response.defer()
        result = admConnectTelegramAccount(ctx.guild.id, user, telegram_username)
        if result:
            return await ctx.followup.send(content='Sua conta foi conectada com sucesso! agora você pode usar os comandos do bot no discord e no telegram', ephemeral=False)
        else:
            return await ctx.followup.send(content='Não foi possível conectar sua conta! você já está conectado?', ephemeral=True)