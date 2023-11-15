from IA_Functions.propria.learning.learning import discordDeepLearning, DMDiscordDeepLearning, simpleLearning
from message_services.discord.message_moderation.moderation_functions import moderate
from message_services.discord.routine_functions.routine_functions import *
from message_services.telegram.telegram_service import warn_admins
from commands.discordCommands import run_discord_commands
from message_services.discord.discord_events import *
from commands.default_commands import calcular_idade
from chatterbot.conversation import Statement
from chatterbot.trainers import ListTrainer
from IA_Functions.terceiras.openAI import *
from database.database import *
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from dateutil import tz
from settings import *
import discord
import sqlite3
import re
import asyncio

conn = sqlite3.connect('discord')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS bump (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT)')

intents = discord.Intents.default()
for DISCORD_INTENT in DISCORD_INTENTS:
    setattr(intents, DISCORD_INTENT, True)
bot = commands.Bot(command_prefix=DISCORD_BOT_PREFIX, intents=discord.Intents.all())

@bot.event
async def on_ready():
    print('Logado como {0.user}'.format(bot))
    try:
        await bot.tree.sync()
        print('Comandos sincronizados com sucesso!')
    except Exception as e:
        print(e)
    guild = bot.get_guild(DISCORD_GUILD_ID)
    bot.config = getConfig(guild)
    if DISCORD_BUMP_WARN: bumpWarning.start()
    if DISCORD_HAS_BUMP_REWARD: bumpReward.start()
    configForVips.start()

@bot.event
async def on_message(message: discord.Message):
    inputChat = message.content
    if message.author.bot == True:
        return
    #testes de lógica e aprendizado
    if message.content.startswith(DISCORD_BOT_PREFIX):
        await run_discord_commands(bot, message)
        return
    #proteções de teste
    ##função de moderação
    moderated = await moderate(bot, message)
    if moderated: return
    ##checagem se esta em fase de testes
    if DISCORD_IS_TESTING and (message.channel.id != DISCORD_TEST_CHANNEL and not isinstance(message.channel, discord.channel.DMChannel)):
        return
    #checa se menciona o bot ou se é uma DM
    if not message.content.lower().__contains__(bot.chatBot.name.lower()) and not bot.user in message.mentions and not isinstance(message.channel, discord.channel.DMChannel):
        return
    #respondendo
    #response = bot.chatBot.generate_response(Statement(inputChat))
    response = await retornaRespostaGPT(inputChat, message.author.name, bot, message.channel.id, 'Discord')
    #await simpleLearning(bot, inputChat, response)
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

@bot.event
async def on_member_update(before:discord.member.Member, after:discord.member.Member):
    checkRolesUpdate(before, after)




@tasks.loop(hours=2) #0.16   10 minutos
async def bumpWarning():
    now = datetime.now().strftime("%H:%M:%S")
    if int(now[:2])>=DISCORD_BUMP_WARNING_TIME[0] and int(now[:2])<=DISCORD_BUMP_WARNING_TIME[1]:
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
            generalChannel = bot.get_channel(753348623844114452)
            await generalChannel.send(f"{bump[int(random.random() * len(bump))]} {lastMessage.jump_url}")

@tasks.loop(hours=24) #0.16   10 minutos
async def bumpReward():
    # se for dia de recompensa(entre 1 e 5 do mês), dará o cargo para os tres primeiro que deram mais bump no mês(exceto os que já tem o cargo VIP)
    if datetime.now().day >= 1 and datetime.now().day <= 25:
        #pegas as mensagens do ultimo mês no canal de bump
        channel = bot.get_channel(853971735514316880)
        bumpers = {}
        async for msg in channel.history(limit=300):
            # se a mensagem for do bot e for do mês passado, conta como bump
            if msg.author.id == 302050872383242240 and msg.created_at.month == datetime.now().month - 1:
                # agora vamos criar uma key para cada membro que deu bump
                if not bumpers.__contains__(msg.interaction.user.name):
                    bumpers[msg.interaction.user.name] = 0
                bumpers[msg.interaction.user.name] += 1
        # agora vamos pegar os 3 primeiros
        bumpers = dict(sorted(bumpers.items(), key=lambda item: item[1], reverse=True))
        print("Os membros que deram bump no mês passado foram: ")
        for member in bumpers:
            print(f"{member}: {bumpers[member]}")

@tasks.loop(hours=24) #0.16   10 minutos
async def configForVips(color=discord.Color.default()):
    guild = bot.get_guild(DISCORD_GUILD_ID)  # Substitua ID_DO_SERVIDOR pelo ID do seu servidor
    VIPRoles = getVIPConfigurations(guild)['VIPRoles']
    VIPMembers = getVIPMembers(guild)
    if VIPRoles:
        for member in VIPMembers:
            if DISCORD_HAS_VIP_CUSTOM_ROLES:
                customRole = discord.utils.get(guild.roles, name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {member.name}")
                if customRole == None:
                    print(f'Não foi possível encontrar um cargo VIP para {member.name}')
                    customRole = await guild.create_role(name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {member.name}", color=color, mentionable=False, reason="Cargo criado para membros VIPs")
                if DISCORD_HAS_ROLE_DIVISION:
                    divisionStart = guild.get_role(DISCORD_VIP_ROLE_DIVISION_START_ID)
                    divisionEnd = guild.get_role(DISCORD_VIP_ROLE_DIVISION_END_ID)
                    await rearrangeRoleInsideInterval(guild, customRole.id, divisionStart, divisionEnd)
                await member.add_roles(customRole)
        for role in guild.roles:
            if role.name.__contains__(DISCORD_VIP_CUSTOM_ROLE_PREFIX):
                for member in role.members:
                    if not VIPMembers.__contains__(member):
                        await member.remove_roles(role)
                        if role.color == discord.Color.default() and role.display_icon == None:
                            await role.delete()
        VIPMembers = [obj.name for obj in VIPMembers] #transforma a lista de membros em uma lista de nomes
        print('Membros VIPs encontrados:')
        print(VIPMembers)
                
    else:
        print(f'Não foi possível encontrar um cargo VIP no servidor {guild.name}')





@bot.tree.command(name=f'vip-mudar_cor', description=f'Muda a cor do cargo VIP do membro')
async def changeVipColor(ctx: discord.Interaction, cor: str):
    for role in ctx.user.roles: #percorre os cargos do membro
        if DISCORD_VIP_ROLES_ID.__contains__(role.id): #se o membro tiver um cargo VIP
            if not re.match(r'^#(?:[a-fA-F0-9]{3}){1,2}$', cor):
                await ctx.response.send_message(content='''# Cor invalida!\n 
Você precisa informar uma cor no formato Hex (#000000).
Você pode procurar por uma cor em https://htmlcolorcodes.com/color-picker/ e testa-la usando o comando "?color #000000"''', ephemeral=False)
                return
            corFormatada = int(cor.replace('#','0x'),16)
            customRole = discord.utils.get(ctx.guild.roles, name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}")
            if customRole == None:
                print(f'Não foi possível encontrar um cargo VIP para {ctx.user.name}')
                customRole = await ctx.guild.create_role(name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}", color=corFormatada, mentionable=False, reason="Cargo criado para membros VIPs")
                if DISCORD_HAS_ROLE_DIVISION:
                    divisionStart = ctx.get_role(DISCORD_VIP_ROLE_DIVISION_START_ID)
                    divisionEnd = ctx.get_role(DISCORD_VIP_ROLE_DIVISION_END_ID)
                    await rearrangeRoleInsideInterval(ctx, customRole.id, divisionStart, divisionEnd)
                await ctx.user.add_roles(customRole)
            else:
                await customRole.edit(color=corFormatada)
            return await ctx.response.send_message(content=f'Cor do cargo VIP alterada para {cor} com sucesso!', ephemeral=False)
    return await ctx.response.send_message(content='Você não é vip! você não pode fazer isso', ephemeral=True)

@bot.tree.command(name=f'vip-mudar_icone', description=f'Muda o icone do cargo VIP do membro')
async def changeVipIcon(ctx: discord.Interaction, icon: str):
    for role in ctx.user.roles:
        if DISCORD_VIP_ROLES_ID.__contains__(role.id):
            try:
                customRole = discord.utils.get(ctx.guild.roles, name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}")
                if customRole == None:
                    print(f'Não foi possível encontrar um cargo VIP para {ctx.user.name}')
                    customRole = await ctx.guild.create_role(name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}", color=discord.Color.default(), mentionable=False, reason="Cargo criado para membros VIPs")
                    if DISCORD_HAS_ROLE_DIVISION:
                        divisionStart = ctx.get_role(DISCORD_VIP_ROLE_DIVISION_START_ID)
                        divisionEnd = ctx.get_role(DISCORD_VIP_ROLE_DIVISION_END_ID)
                        rearrangeRoleInsideInterval(ctx, customRole.id, divisionStart, divisionEnd)
                    await ctx.user.add_roles(customRole)
                await customRole.edit(display_icon=icon)
                await ctx.response.send_message(content='Ícone do cargo VIP alterado com sucesso!', ephemeral=False)
            except Exception as e:
                await ctx.response.send_message(content='''Ícone inválido! você precisa informar um emoji válido. Se você quiser usar um emoji 
customizado como os do servidor, você ira precisar pedir a algum staff''', ephemeral=True)


@bot.tree.command(name=f'say_as_{BOT_NAME.lower()}', description=f'Faz {BOT_NAME} falar em um canal de texto')
async def sayAsCoddy(ctx: discord.Interaction, channel: discord.TextChannel, message: str):
    channelId = discord.utils.get(ctx.guild.channels, name=channel.name)
    await channelId.send(message)

@bot.tree.command(name=f'call_titio', description=f'Faz {BOT_NAME} chamar o titio')
async def callAdmin(ctx: discord.Interaction, message: str):
    warn_admins(ctx.user.name, message)
    try:
        resp = await ctx.response.send_message(content='O titio foi avisado! agora é só esperar :3', ephemeral=True)
        return resp
    except Exception as e:
        if resp:
            channel = await ctx.user.create_dm()
            await channel.send(content='O titio foi avisado! agora é só esperar :3')
        pass

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