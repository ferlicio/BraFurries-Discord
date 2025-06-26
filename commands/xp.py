from discord.ext import commands
import discord


def setup(bot: commands.Bot):
    @bot.tree.command(name='xp', description='Mostra a quantidade de xp de um membro')
    async def showXp(ctx: discord.Interaction, member: discord.Member):
        pass

    @bot.tree.command(name='xp_ranking', description='Mostra o ranking de xp dos membros')
    async def showXpRanking(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='xp_resetar', description='Resetar a quantidade de xp de um membro')
    async def resetXp(ctx: discord.Interaction, member: discord.Member):
        pass

    @bot.tree.command(name='xp_resetar_todos', description='Resetar a quantidade de xp de todos os membros')
    async def resetAllXp(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='xp_adicionar', description='Adiciona xp a um membro')
    async def addXp(ctx: discord.Interaction, member: discord.Member, xp: int):
        pass

    @bot.tree.command(name='xp_remover', description='Remove xp de um membro')
    async def removeXp(ctx: discord.Interaction, member: discord.Member, xp: int):
        pass

    @bot.tree.command(name='loja', description='Compre itens com seu dinheiro')
    async def shop(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='rp_inventario', description='Mostra os itens que você possui')
    async def inventory(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='rp_usar', description='Usa um item do seu inventário')
    async def useItem(ctx: discord.Interaction, item: str):
        pass

    @bot.tree.command(name='rp_vender', description='Vende um item do seu inventário')
    async def sellItem(ctx: discord.Interaction, item: str):
        pass

    @commands.cooldown(1, 86400, key=lambda ctx: (ctx.guild_id, ctx.author.id))
    @bot.tree.command(name='daily', description='Pega sua recompensa diária')
    async def daily(ctx: discord.Interaction):
        await ctx.response.send_message(content='Recompensa diária pega com sucesso!')
        pass

    @daily.error
    async def daily_error(ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f'Você já pegou sua recompensa diária! Tente novamente em {error.retry_after:.0f} segundos', ephemeral=True)
        else:
            raise error

    @bot.tree.command(name='rp_banho', description='Tomar banho dá xp sabia?')
    async def bath(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='rp_trabalhar', description='Trabalha em troca de xp e dinheiro')
    async def work(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='rp_duelo', description='Desafie alguém para um duelo')
    async def duel(ctx: discord.Interaction, member: discord.Member):
        pass

    @bot.tree.command(name='rp_desenhar', description='Desenhe algo!')
    async def draw(ctx: discord.Interaction):
        pass

    @bot.tree.command(name='rp_escrever', description='Escreva uma história')
    async def write(ctx: discord.Interaction):
        pass
