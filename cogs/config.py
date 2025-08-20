from discord import Interaction, app_commands
from discord.ext import commands
import discord
from schemas.types.server_messages import ServerMessages
from core.database import setServerMessage, getConfig, updateServerConfig
from core.discord_events import getStaffRoles

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

    @app_commands.command(
        name='configuracoes_servidor',
        description='Exibe ou altera as configurações do servidor',
    )
    @app_commands.describe(
        economia='Ativa ou desativa a economia',
        ia='Ativa ou desativa as respostas por IA',
    )
    async def serverConfig(
        self,
        ctx: Interaction,
        economia: bool | None = None,
        ia: bool | None = None,
    ):
        if economia is None and ia is None:
            config = getConfig(ctx.guild)
            embed = discord.Embed(
                title='Configurações do Servidor',
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name='Economia',
                value='Ativada' if config.get('hasEconomyEnabled') else 'Desativada',
                inline=False,
            )
            embed.add_field(
                name='Respostas por IA',
                value='Ativadas' if config.get('hasGptEnabled') else 'Desativadas',
                inline=False,
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        staff_roles = getStaffRoles(ctx.guild)
        if not any(role in ctx.user.roles for role in staff_roles):
            return await ctx.response.send_message(
                content='Você não tem permissão para alterar as configurações.',
                ephemeral=True,
            )

        updates = {}
        if economia is not None:
            updates['has_economy_enabled'] = economia
        if ia is not None:
            updates['has_gpt_enabled'] = ia

        updated = updateServerConfig(ctx.guild_id, **updates)
        if not updated:
            return await ctx.response.send_message(
                content='Não foi possível atualizar as configurações.',
                ephemeral=True,
            )

        config = getConfig(ctx.guild)
        embed = discord.Embed(
            title='Configurações do Servidor',
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name='Economia',
            value='Ativada' if config.get('hasEconomyEnabled') else 'Desativada',
            inline=False,
        )
        embed.add_field(
            name='Respostas por IA',
            value='Ativadas' if config.get('hasGptEnabled') else 'Desativadas',
            inline=False,
        )
        await ctx.response.send_message(
            content='Configurações atualizadas com sucesso!',
            embed=embed,
            ephemeral=True,
        )
    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCog(bot))
