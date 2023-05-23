from settings import SOCIAL_MEDIAS, DISCORD_TOKEN, DISCORD_INTENTS, COMMUNITY_LEARNING, DISCORD_IS_TESTING, DISCORD_TEST_CHANNEL, DISCORD_ADMINS, DISCORD_INPUT, DISCORD_BOT_PREFIX,BOT_NAME
from learning.learning import discordDeepLearning, DMDiscordDeepLearning
from commands.discordCommands import run_discord_commands
from chatterbot.conversation import Statement
from chatterbot.trainers import ListTrainer
from discord.ext import commands
import discord


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
    if DISCORD_IS_TESTING and (message.channel.id != DISCORD_TEST_CHANNEL and not isinstance(message.channel, discord.channel.DMChannel)):
        return
    if isinstance(message.channel, discord.channel.DMChannel):
        async for msg in message.channel.history(limit=3):
            if msg.author.id == bot.user.id and msg.content.__contains__("Qual seria a resposta correta?"):
                return
    #menciona o bot
    if not message.content.lower().__contains__(bot.chatBot.name.lower()) and not bot.user in message.mentions and not isinstance(message.channel, discord.channel.DMChannel):
        return
    response = bot.chatBot.generate_response(Statement(text=inputChat))
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

def check_allowed_ids(ctx):
    user_id = ctx.author.id  # ID de quem usou o comando
    return user_id in DISCORD_ADMINS

@bot.tree.command(name=f'say_as_{BOT_NAME.lower()}', description=f'Faz {BOT_NAME} falar em um canal de texto')
@commands.check(check_allowed_ids)
async def sayAsCoddy(ctx: discord.Interaction, channel: discord.TextChannel, message: str):
    channelId = discord.utils.get(ctx.guild.channels, name=channel.name)
    await channelId.send(message)

@bot.tree.command(name='insert_training', description=f'Treina {BOT_NAME} para responder uma conversa')
@commands.check(check_allowed_ids)
async def insertTraining(ctx, prompt: str, answer1: str, answer2: str = None, answer3: str = None):
    trainer = ListTrainer(bot.chatBot)
    if not prompt or not answer1:
        await ctx.send('Você precisa informar uma conversa valida!')
        return
    else:
        conversation = [prompt] + [answer1] + [answer2] + [answer3]
        for i in range(len(conversation)):
            if conversation[i] != '' and i+1 < len(conversation):
                if conversation[i+1] != None:
                    trainer.train([conversation[i], conversation[i+1]])
        await ctx.send('Conversa treinada com sucesso!')

def run_discord_client(chatBot):
    if SOCIAL_MEDIAS.__contains__('Discord'):
        bot.chatBot = chatBot
        bot.run(DISCORD_TOKEN)