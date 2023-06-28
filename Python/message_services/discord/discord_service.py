from settings import DISCORD_TOKEN, DISCORD_INTENTS, COMMUNITY_LEARNING, DISCORD_IS_TESTING, DISCORD_TEST_CHANNEL, DISCORD_ADMINS, DISCORD_INPUT, DISCORD_BOT_PREFIX,BOT_NAME
from message_services.discord.message_moderation.moderation_functions import moderate
from learning.learning import discordDeepLearning, DMDiscordDeepLearning
from message_services.telegram.telegram_service import warn_admins
from commands.discordCommands import run_discord_commands
from commands.default_commands import calcular_idade
from chatterbot.conversation import Statement
from chatterbot.trainers import ListTrainer
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from dateutil import tz
import discord
import sqlite3

conn = sqlite3.connect('discord')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS bump (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT)')

intents = discord.Intents.default()
for DISCORD_INTENT in DISCORD_INTENTS:
    setattr(intents, DISCORD_INTENT, True)
bot = commands.Bot(command_prefix='>', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print('Logado como {0.user}'.format(bot))
    try:
        synced = await bot.tree.sync()
        print('Comandos sincronizados com sucesso!')
    except Exception as e:
        print(e)
    send_message.start()

@bot.event
async def on_message(message):
    inputChat = message.content
    if message.author.bot == True:
        return
    #testes de lógica e aprendizado
    if message.content.startswith(DISCORD_BOT_PREFIX):
        await run_discord_commands(bot, message)
        return
    await DMDiscordDeepLearning(bot, message)
    #proteções de teste
    moderated = await moderate(bot, message)
    if moderated: return
    if DISCORD_IS_TESTING and (message.channel.id != DISCORD_TEST_CHANNEL and not isinstance(message.channel, discord.channel.DMChannel)):
        return
    if isinstance(message.channel, discord.channel.DMChannel):
        async for msg in message.channel.history(limit=3):
            if msg.author.id == bot.user.id and msg.content.__contains__("Qual seria a resposta correta?"):
                return
    #checa se a mensagem é para ser moderada ou não
    #menciona o bot
    if not message.content.lower().__contains__(bot.chatBot.name.lower()) and not bot.user in message.mentions and not isinstance(message.channel, discord.channel.DMChannel):
        return
    #respondendo
    response = bot.chatBot.generate_response(Statement(inputChat))
    print(response)
    await message.channel.send(response)
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.author.id == bot.user.id: #se a mensagem for do bot
        if not COMMUNITY_LEARNING and DISCORD_ADMINS.__contains__(user.id): 
            await discordDeepLearning(bot, reaction, user, DISCORD_INPUT)
            return
        if COMMUNITY_LEARNING:
            await discordDeepLearning(bot, reaction, user, DISCORD_INPUT)
            return





@tasks.loop(hours=2) #0.16   10 minutos
async def send_message():
    now = datetime.now().strftime("%H:%M:%S")
    if int(now[:2])>=9 and int(now[:2])<=23:
        channel = bot.get_channel(853971735514316880)
        async for msg in channel.history(limit=5):
            if msg.author.id == 302050872383242240:
                lastMessage = msg
                break
        lastBump = lastMessage.created_at.astimezone(tz.gettz('America/Sao_Paulo'))
        timeSinceLastBump = datetime.now(tz.gettz('America/Sao_Paulo')) - lastBump
        if timeSinceLastBump.days >= 1 or timeSinceLastBump.total_seconds() >= 7200:
            from message_services.discord.routine_functions.messages import bump
            import random
            generalchannel = bot.get_channel(753348623844114452)
            await generalchannel.send(f"{bump[int(random.random() * len(bump))]} {lastMessage.jump_url}")






@bot.tree.command(name=f'say_as_{BOT_NAME.lower()}', description=f'Faz {BOT_NAME} falar em um canal de texto')
async def sayAsCoddy(ctx: discord.Interaction, channel: discord.TextChannel, message: str):
    channelId = discord.utils.get(ctx.guild.channels, name=channel.name)
    await channelId.send(message)

@bot.tree.command(name=f'call_titio', description=f'Faz {BOT_NAME} chamar o titio')
async def sayAsCoddy(ctx: discord.Interaction, message: str):
    await warn_admins(message)

@bot.tree.command(name='insert_training', description=f'Treina {BOT_NAME} para responder uma conversa')
async def insertTraining(ctx, prompt: str, answer1: str, answer2: str = None, answer3: str = None):
    trainer = ListTrainer(bot.chatBot)
    if not prompt or not answer1:
        await ctx.response.send_message(content='Você precisa informar uma conversa valida!', ephemeral=True)
        return
    else:
        conversation = [prompt] + [answer1] + [answer2] + [answer3]
        for i in range(len(conversation)):
            if conversation[i] != '' and i+1 < len(conversation):
                if conversation[i+1] != None:
                    trainer.train([conversation[i], conversation[i+1]])
        await ctx.response.send_message(content='Conversa treinada com sucesso!', ephemeral=True)

@bot.tree.command(name='insert_complex_training', description=f'Treina {BOT_NAME} para responder uma conversa com dados complexos')
async def insertComplexTraining(ctx, conversation: str):
    """ trainer = ListTrainer(bot.chatBot)
    conversation
    for i in range(len(conversation)):
        if conversation[i] != '' and i+1 < len(conversation):
            if conversation[i+1] != None:
                trainer.train([conversation[i], conversation[i+1]]) """
    await ctx.response.send_message(content='Conversa treinada com sucesso!', ephemeral=True)

@bot.tree.command(name='mod-calc_idade', description=f'Use esse recurso para calcular a idade de alguém de acordo com a data de nascimento')
async def calc_idade(ctx, message: str):
    try:
        idade = calcular_idade(message)
        if idade == 'Entrada inválida':
            raise Exception
        await ctx.response.send_message(content=f'{message}: {idade} anos', ephemeral=True)
    except Exception:
        await ctx.response.send_message(content='Data de nascimento inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>', ephemeral=True)

@bot.tree.command(name='mod-check_new_member', description=f'Use esse recurso para checar se um novo membro é elegivel a usar a carteirinha de cargos ou não')
async def check_new_member(ctx, member:discord.Member, age:int):
        account_age = datetime.utcnow().date() - member.created_at.date()
        if age<=13 or account_age.days <= 30:
            conditions = 'idade menor do que 13 anos e conta com menos de 30 dias de idade' if (age<=13 and account_age.days <= 30) else 'conta criada a menos de 30 dias' if account_age.days <= 30 else 'idade menor do que 13 anos'
            return await ctx.response.send_message(content=f'o membro {member.name} precisará usar carteirinha temporária, o membro possui {conditions}', ephemeral=True)
        return await ctx.response.send_message(content='O membro não precisará usar carteirinha temporária', ephemeral=True)

def run_discord_client(chatBot):
    bot.chatBot = chatBot
    bot.run(DISCORD_TOKEN)