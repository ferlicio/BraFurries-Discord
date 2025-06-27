from discord.ext import commands
import discord


class XpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
        
    @commands.command(name='xp', description='Mostra a quantidade de xp de um membro')
    async def showXp(self, ctx: discord.Interaction, member: discord.Member):
        pass

    @commands.command(name='xp_ranking', description='Mostra o ranking de xp dos membros')
    async def showXpRanking(self, ctx: discord.Interaction):
        pass

    @commands.command(name='xp_resetar', description='Resetar a quantidade de xp de um membro')
    async def resetXp(self, ctx: discord.Interaction, member: discord.Member):
        pass

    @commands.command(name='xp_resetar_todos', description='Resetar a quantidade de xp de todos os membros')
    async def resetAllXp(self, ctx: discord.Interaction):
        pass

    @commands.command(name='xp_adicionar', description='Adiciona xp a um membro')
    async def addXp(self, ctx: discord.Interaction, member: discord.Member, xp: int):
        pass

    @commands.command(name='xp_remover', description='Remove xp de um membro')
    async def removeXp(self, ctx: discord.Interaction, member: discord.Member, xp: int):
        pass

    @commands.command(name='loja', description='Compre itens com seu dinheiro')
    async def shop(self, ctx: discord.Interaction):
        pass

    @commands.command(name='rp_inventario', description='Mostra os itens que você possui')
    async def inventory(self, ctx: discord.Interaction):
        pass

    @commands.command(name='rp_usar', description='Usa um item do seu inventário')
    async def useItem(self, ctx: discord.Interaction, item: str):
        pass

    @commands.command(name='rp_vender', description='Vende um item do seu inventário')
    async def sellItem(self, ctx: discord.Interaction, item: str):
        pass

    @commands.cooldown(1, 86400, key=lambda self, ctx: (self, ctx.guild_id, self, ctx.author.id))
    @commands.command(name='daily', description='Pega sua recompensa diária')
    async def daily(self, ctx: discord.Interaction):
        await ctx.response.send_message(content='Recompensa diária pega com sucesso!')
        pass

    @daily.error
    async def daily_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f'Você já pegou sua recompensa diária! Tente novamente em {error.retry_after:.0f} segundos', ephemeral=True)
        else:
            raise error

    @commands.command(name='rp_banho', description='Tomar banho dá xp sabia?')
    async def bath(self, ctx: discord.Interaction):
        pass

    @commands.command(name='rp_trabalhar', description='Trabalha em troca de xp e dinheiro')
    async def work(self, ctx: discord.Interaction):
        pass

    @commands.command(name='rp_duelo', description='Desafie alguém para um duelo')
    async def duel(self, ctx: discord.Interaction, member: discord.Member):
        pass

    @commands.command(name='rp_desenhar', description='Desenhe algo!')
    async def draw(self, ctx: discord.Interaction):
        pass

    @commands.command(name='rp_escrever', description='Escreva uma história')
    async def write(self, ctx: discord.Interaction):
        pass
    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(XpCog(bot))
