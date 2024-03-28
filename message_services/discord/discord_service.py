import asyncio
import random
from message_services.discord.message_moderation.moderation_functions import moderate
from message_services.discord.routine_functions.routine_functions import *
from message_services.discord.discord_events import *
from commands.default_commands import calcular_idade
from IA_Functions.terceiras.openAI import *
from discord.ext import commands, tasks
from database.database import *
from datetime import datetime, timedelta, timezone
from typing import Literal
from dateutil import tz
import requests
import discord
import sqlite3
import re, pytz

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
    bot.config = Config(getConfig(guild))
    if DISCORD_BUMP_WARN: bumpWarning.start()
    if DISCORD_HAS_BUMP_REWARD: bumpReward.start()
    cronJobs.start()
    configForVips.start()

@bot.event
async def on_message(message: discord.Message):
    inputChat = message.content
    response = None
    if message.author.bot == True:
        return
    
    await mentionArtRoles(bot, message)
    await secureArtPosts(message)

    #se for uma DM e não for o criador, não responde
    if isinstance(message.channel, discord.channel.DMChannel) and not message.author.id == os.getenv('CREATOR_ID'):
        return
    
    #se não menciona o bot ou se é uma DM, ou se é uma mensagem aleatória, não responde
    if (not message.content.lower().__contains__(bot.chatBot['name'].lower()) and  
        not bot.user in message.mentions and 
        not isinstance(message.channel, discord.channel.DMChannel)) or (
        random.random() > 0.7 and datetime.now(pytz.timezone('America/Sao_Paulo')).hour < 8):
            return 

    #se for os canais não permitidos, não responde
    allowedChannels = [753348623844114452]
    if not message.channel.id in allowedChannels:
        return
    
    #se for horario de dormir, responde que está dormindo
    if datetime.now(pytz.timezone('America/Sao_Paulo')).hour < 8:
            response = '''coddy está a mimir, às 8 horas eu volto😴'''
    
    if not response:
        #respondendo
        await asyncio.sleep(2)
        async with message.channel.typing():
            gpt_properties = hasGPTEnabled(message.guild)
            if gpt_properties['enabled']:
                memberRoles = [role.name for role in message.author.roles]
                memberGenre = memberRoles[(next(i for i, item in enumerate(memberRoles) if 'Gênero' in item))-1]
                memberGenre = "ele" if "Membro" in memberGenre else "ela" if "Membra" in memberGenre else "ele/ela"
                memberSpecies = memberRoles[(next(i for i, item in enumerate(memberRoles) if 'Espécies' in item))-1]
                response = await retornaRespostaGPT(inputChat, message.author.display_name if message.author.display_name
                                                    else message.author.name, memberGenre, memberSpecies, bot, message.channel.id, 'Discord', gpt_properties['model'])
            else:
                response = '''Eu to desativado por enquanto, mas logo logo eu volto! \nFale com o titio derg se você quiser saber mais sobre como ajudar a me manter ativo ;3'''
            await asyncio.sleep(2)
    await message.channel.send(response)
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    pass

@bot.event
async def on_member_update(before:discord.member.Member, after:discord.member.Member):
    checkRolesUpdate(before, after)



@tasks.loop(hours=12)
async def cronJobs():
    await removeTempRoles(bot)




@tasks.loop(hours=2) #0.16   10 minutos
async def bumpWarning():
    now = datetime.now().strftime("%H:%M:%S")
    if int(now[:2])>=DISCORD_BUMP_WARNING_TIME[0] and int(now[:2])<=DISCORD_BUMP_WARNING_TIME[1]:
        bumpChannel = bot.get_channel(853971735514316880)
        generalChannel = bot.get_channel(753348623844114452)
        async for msg in bumpChannel.history(limit=5):
            if msg.author.id == 302050872383242240:
                lastMessage = msg
                break
        lastBump = lastMessage.created_at.astimezone(tz.gettz('America/Sao_Paulo'))
        timeSinceLastBump = datetime.now(tz.gettz('America/Sao_Paulo')) - lastBump
        needToWarn = True
        async for msg in generalChannel.history(limit=200):
            if msg.author.id == 1106756281420759051 and msg.content.__contains__('bump'):
                if datetime.now(tz.gettz('America/Sao_Paulo')) - msg.created_at.astimezone(tz.gettz('America/Sao_Paulo')) < timedelta(hours=2):
                    needToWarn = False
                break
        if (timeSinceLastBump.days >= 1 or timeSinceLastBump.total_seconds() >= 7200) and needToWarn:
            from message_services.discord.routine_functions.messages import bump
            import random
            await generalChannel.send(f"{bump[int(random.random() * len(bump))]} {lastMessage.jump_url}")

@tasks.loop(hours=24) #0.16   10 minutos
async def bumpReward():
    # se for dia de recompensa(dia 1 do mês), dará o cargo para os tres primeiro que deram mais bump no mês(exceto os que já tem o cargo VIP)
    if datetime.now().day == 1:
        #pegas as mensagens do ultimo mês no canal de bump
        channel = bot.get_channel(853971735514316880)
        bumpers = {}
        async for msg in channel.history(limit=300):
            # se a mensagem for do bot e for do mês passado, conta como bump
            if msg.author.id == 302050872383242240 and (msg.created_at.month == datetime.now().month - 1 or (msg.created_at.month == 12 and datetime.now().month == 1)):
                # agora vamos criar uma key para cada membro que deu bump
                if not bumpers.__contains__(msg.interaction.user.name):
                    bumpers[msg.interaction.user.name] = 0
                bumpers[msg.interaction.user.name] += 1
        bumpers = dict(sorted(bumpers.items(), key=lambda item: item[1], reverse=True))
        # agora vamos mandar uma mensagem privada para o titio derg com os membros que deram mais bump
        guild = bot.get_guild(DISCORD_GUILD_ID)
        titio = guild.get_member(167436511787220992)
        message = f"Os membros que deram bump no mês passado foram: \n"
        for member in bumpers:
            # se for o ultimo membro adiciona \n no final
            message += f"{member}: {bumpers[member]}"+ ("" if list(bumpers.keys())[-1] == member else "\n")
        await titio.send(message)
        



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
                    for role in member.roles:
                        if role.name.__contains__(DISCORD_VIP_CUSTOM_ROLE_PREFIX):
                            await role.edit(name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {member.name}")
                            customRole = role
                            break
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



####################################################################################################################
# COMANDOS VIP
####################################################################################################################


@bot.tree.command(name=f'vip-mudar_cor', description=f'Muda a cor do cargo VIP do membro')
async def changeVipColor(ctx: discord.Interaction, cor: str):
    for role in ctx.user.roles: #percorre os cargos do membro
        if DISCORD_VIP_ROLES_ID.__contains__(role.id): #se o membro tiver um cargo VIP
            if not re.match(r'^#(?:[a-fA-F0-9]{3}){1,2}$', cor):
                return await ctx.response.send_message(content='''# Cor invalida!\n 
Você precisa informar uma cor no formato Hex (#000000).
Você pode procurar por uma cor em https://htmlcolorcodes.com/color-picker/ e testa-la usando o comando "?color #000000"''', ephemeral=False)
            if not await colorIsAvailable(cor):
                return await ctx.response.send_message(content='''Cor inválida! você precisa informar uma cor que não seja muito parecida com a cor de algum cargo da staff''', ephemeral=True)
            corFormatada = int(cor.replace('#','0x'),16)
            customRole = discord.utils.get(ctx.guild.roles, name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}")
            if customRole == None:
                print(f'Não foi possível encontrar um cargo VIP para {ctx.user.name}')
                customRole = await ctx.guild.create_role(name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}", color=corFormatada, mentionable=False, reason="Cargo criado para membros VIPs")
                if DISCORD_HAS_ROLE_DIVISION:
                    divisionStart = discord.utils.get(ctx.guild.roles, id=DISCORD_VIP_ROLE_DIVISION_START_ID) 
                    divisionEnd = discord.utils.get(ctx.guild.roles, id=DISCORD_VIP_ROLE_DIVISION_END_ID)
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

@bot.tree.command(name=f'testes', description=f'teste')
async def test(ctx: discord.Interaction, message: str):
    print(message)
    await ctx.response.send_message(content=f'{message}', ephemeral=False)


####################################################################################################################
# COMANDOS DE INFORMAÇÕES DE MEMBROS
####################################################################################################################


@bot.tree.command(name=f'registrar_local', description=f'Registra o local do membro')
async def registerLocal(ctx: discord.Interaction, local: str):
    mydbAndCursor = startConnection()
    availableLocals = getAllLocals(mydbAndCursor[0])
    if await localeIsAvailable(ctx, mydbAndCursor, local):
        await ctx.response.defer()
        result = includeLocale(mydbAndCursor[0],local.upper(), ctx.user, availableLocals)
        endConnectionWithCommit(mydbAndCursor)
        if result:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local.upper():
                    return await ctx.followup.send(content=f'você foi registrado em {locale["locale_name"]}!', ephemeral=False)
        else:
            return await ctx.followup.send(content=f'Não foi possível registrar você! você já está registrado em algum local?', ephemeral=True)
    return
    
    
@bot.tree.command(name=f'furros_na_area', description=f'Lista todos os furries registrados em um local')
async def listFurries(ctx: discord.Interaction, local: str):
    mydbAndCursor = startConnection()
    availableLocals = getAllLocals(mydbAndCursor[0])
    if await localeIsAvailable(ctx, mydbAndCursor, local):
        await ctx.response.defer()
        result = getByLocale(mydbAndCursor[0],local.upper(), availableLocals)
        endConnection(mydbAndCursor)
        if result:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local.upper():
                    membersResponse = ',\n'.join(member for member in result)
                    return await ctx.followup.send(content=f'''Aqui estão os furros registrados em {locale["locale_name"]}:```{membersResponse}```''')
        else:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local.upper():
                    return await ctx.followup.send(content=f'Não há furros registrados em {locale["locale_name"]}... que tal ser o primeiro? :3')
    return
    

@bot.tree.command(name=f'registrar_aniversario', description=f'Registra o aniversário do membro')
async def registerBirthday(ctx: discord.Interaction, birthday: str):
    try:
        datetime.strptime(birthday, "%d/%m/%Y")
    except ValueError:
        return await ctx.response.send_message(content='''Data de nascimento inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
    birthdayAsDate = datetime.strptime(birthday, '%d/%m/%Y').date()
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = includeBirthday(mydbAndCursor[0],birthdayAsDate, ctx.user)
    endConnectionWithCommit(mydbAndCursor)
    if result:
        return await ctx.followup.send(content=f'você foi registrado com o aniversário {birthday}!', ephemeral=False)
    else:
        return await ctx.followup.send(content=f'Não foi possível registrar você! você já está registrado?', ephemeral=True)
    

@bot.tree.command(name=f'aniversarios', description=f'Lista todos os aniversários registrados')
async def listBirthdays(ctx: discord.Interaction):
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = getAllBirthdays(mydbAndCursor[0])
    endConnection(mydbAndCursor)
    if result:
        birthdaysResponse = ',\n'.join(
    f'{birthday["username"]} - {birthday["birth_date"].strftime("%d/%m")}'
    for birthday in sorted(result, key=lambda birthday: birthday["birth_date"]))
        return await ctx.followup.send(content=f'Aqui estão os aniversários registrados:```{birthdaysResponse}```')
    else:
        return await ctx.followup.send(content=f'Não há aniversários registrados... que tal ser o primeiro? :3')


####################################################################################################################
# COMANDOS DE EVENTOS
####################################################################################################################


async def addEvent(ctx: discord.Interaction, user: any, state:str, city:str, event_name:str, address:str, price:float, starting_date: str, starting_time: str, ending_date: str, ending_time: str, description: str = None, group_link:str = None, site:str = None, max_price:float = None, event_logo_url:str = None):
    try:
        datetime.strptime(starting_date, "%d/%m/%Y")
        if ending_date == None:
            ending_date = starting_date
        else:
            datetime.strptime(ending_date, "%d/%m/%Y")
    except ValueError:
        return await ctx.response.send_message(content='''Data inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
    try:
        datetime.strptime(starting_time, "%H:%M")
        datetime.strptime(ending_time, "%H:%M")
    except ValueError:
        return await ctx.response.send_message(content='''Horário inválido! você informou um horário no formato "hh:mm"? <:catsip:851024825333186560>''', ephemeral=True)
    starting_datetime = datetime.strptime(f'{starting_date} {starting_time}', '%d/%m/%Y %H:%M')

    ending_datetime = datetime.strptime(f'{ending_date} {ending_time}', '%d/%m/%Y %H:%M')
    if starting_datetime > ending_datetime:
        #teste se a data e hora de inicio é maior que a data e hora de encerramento
        return await ctx.response.send_message(content='''A data e hora de início do evento não pode ser maior que a data e hora de encerramento!''', ephemeral=True)
    mydbAndCursor = startConnection()
    locale_id = await localeIsAvailable(ctx, mydbAndCursor, state)
    if locale_id:
        await ctx.response.defer()
        result = includeEvent(mydbAndCursor[0],user, locale_id, city, event_name, address, price, starting_datetime, ending_datetime, description, group_link, site, max_price, event_logo_url)
        endConnectionWithCommit(mydbAndCursor)
        if result:
            return await ctx.followup.send(content=f'O evento **{event_name}** foi registrado com sucesso!', ephemeral=False)
        
@bot.tree.command(name=f'novo_evento', description=f'Adiciona um evento ao calendário')
async def addEventWithDiscordUser(ctx: discord.Interaction, user: discord.Member, estado:str, cidade:str, event_name:str, address:str, price:float, starting_date: str, starting_time: str, ending_date: str, ending_time: str, description: str = None, group_link:str = None, site:str = None, max_price:float = None, event_logo_url:str = None):
    await addEvent(ctx, user, estado, cidade, event_name, address, price, starting_date, starting_time, ending_date, ending_time, description, group_link, site, max_price, event_logo_url)
    pass
@bot.tree.command(name=f'novo_evento_por_usuario', description=f'Adiciona um evento ao calendário usando um usuário do telegram')
async def addEventWithTelegramUser(ctx: discord.Interaction, telegram_username: str, estado:str, cidade:str, event_name:str, address:str, price:float, starting_date: str, starting_time: str, ending_time: str, ending_date: str = None, description: str = None, group_link:str = None, site:str = None, max_price:float = None, event_logo_url:str = None):
    await addEvent(ctx, telegram_username, estado, cidade, event_name, address, price, starting_date, starting_time, ending_date, ending_time, description, group_link, site, max_price, event_logo_url)
    pass


@bot.tree.command(name=f'eventos', description=f'Lista todos os eventos registrados')
async def listEvents(ctx: discord.Interaction):
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = getAllEvents(mydbAndCursor[0])
    endConnection(mydbAndCursor)
    if result:
        formattedEvents = formatEventList(result)
        eventsResponse = []
        for event in formattedEvents:
            if eventsResponse == []:
                eventsResponse.append(f'''Aqui estão os próximos eventos registrados:\n'''+event+'\n‎')
            else:
                eventsResponse.append('\n\n'+ event)
                if event != formattedEvents[-1]:
                    eventsResponse[-1] += '\n‎'
        eventsResponse[-1] += f'''\n\n```Se você quiser ver mais detalhes sobre um evento, use o comando "/evento <nome do evento>"```
Adicione tambem a nossa agenda de eventos ao seu google agenda e tenha todos os eventos na palma da sua mão! {os.getenv('GOOGLE_CALENDAR_LINK')}'''
        for message in eventsResponse:
            await ctx.followup.send(content=message) if message != eventsResponse[-1] else await ctx.channel.send(content=message)
    else:
        return await ctx.followup.send(content=f'Não há eventos registrados... que tal ser o primeiro? :3')
    
    
@bot.tree.command(name=f'eventos_por_estado', description=f'Lista todos os eventos registrados em um estado')
async def listEventsByState(ctx: discord.Interaction, state: str):
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    locale_id = await localeIsAvailable(ctx, mydbAndCursor, state)
    result = getEventsByState(mydbAndCursor[0], locale_id)
    endConnection(mydbAndCursor)
    if result:
        formattedEvents = formatEventList(result)
        eventsResponse = []
        for event in formattedEvents:
            if eventsResponse == []:
                eventsResponse.append(f'''Aqui estão os próximos eventos registrados:\n'''+event+'\n‎')
            else:
                eventsResponse.append('\n\n'+ event)
                if event != formattedEvents[-1]:
                    eventsResponse[-1] += '\n‎'
        eventsResponse[-1] += f'''\n\n```Se você quiser ver mais detalhes sobre um evento, use o comando "/evento <nome do evento>"```
Adicione tambem a nossa agenda de eventos ao seu google agenda e tenha todos os eventos na palma da sua mão! {os.getenv('GOOGLE_CALENDAR_LINK')}'''
        for message in eventsResponse:
            await ctx.followup.send(content=message) if message != eventsResponse[-1] else await ctx.channel.send(content=message)
    else:
        return await ctx.followup.send(content=f'Não há eventos registrados em {state}... que tal ser o primeiro? :3')
    
    
@bot.tree.command(name=f'evento', description=f'Mostra os detalhes de um evento')
async def showEvent(ctx: discord.Interaction, event_name: str):
    mydbAndCursor = startConnection()
    if event_name.__len__() < 4:
        return await ctx.response.send_message(content='''Nome do evento inválido! você informou um nome com menos de 4 caracteres? <:catsip:851024825333186560>''', ephemeral=True)
    await ctx.response.defer()
    event = getEventByName(mydbAndCursor[0], event_name)
    endConnection(mydbAndCursor)
    if event:
        eventEmbeded = formatSingleEvent(event)
        return await ctx.followup.send(embed=eventEmbeded)
    else:
        return await ctx.followup.send(content=f'Não há eventos registrados com esse nome. Tem certeza que digitou o nome certo?')
    

@bot.tree.command(name=f'evento_reagendar', description=f'Reagenda um evento pendente')
async def rescheduleEvent(ctx: discord.Interaction, event_name: str, new_date: str):
    try: new_date = datetime.strptime(new_date, "%d/%m/%Y")
    except ValueError:
        return await ctx.response.send_message(content='''Data inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = rescheduleEventDate(mydbAndCursor[0], event_name, new_date, ctx.user.name)
    endConnectionWithCommit(mydbAndCursor)
    if result == True:
        return await ctx.followup.send(content=f'O evento **{event_name}** foi reagendado com sucesso!')
    elif result == "não encontrado":
        return await ctx.followup.send(content=f'Não foi possível encontrar um evento com esse nome! tem certeza que digitou o nome certo?')
    elif result == "não é o dono":
        return await ctx.followup.send(content=f'Você não é o dono desse evento! apenas o dono pode reagendar o evento')
    elif result == "em andamento":
        return await ctx.followup.send(content=f'Não é possível reagendar um evento que já está em andamento')
    elif result == "encerrado":
        return await ctx.followup.send(content=f'Não é possível reagendar um evento que já foi realizado')


@bot.tree.command(name=f'evento_agendar_prox', description=f'Agenda no calendario a próxima data do evento')
async def scheduleNextEvent(ctx: discord.Interaction, nome_do_evento: str, data: str):
    try: data = datetime.strptime(data, "%d/%m/%Y")
    except ValueError:
        return await ctx.response.send_message(content='''Data inválida! Você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = scheduleNextEventDate(mydbAndCursor[0], nome_do_evento, data, ctx.user.name)
    endConnectionWithCommit(mydbAndCursor)
    if result == True:
        return await ctx.followup.send(content=f'O evento **{nome_do_evento}** foi agendado com sucesso!')
    elif result == "não encontrado":
        return await ctx.followup.send(content=f'Não foi possível encontrar um evento com esse nome! tem certeza que digitou o nome certo?')
    elif result == "não encerrado":
        return await ctx.followup.send(content=f'Não é possível agendar um evento que ainda não foi encerrado')
    elif result == "não é o dono":
        return await ctx.followup.send(content=f'Você não é o dono desse evento! apenas o dono pode agendar o evento')
    

@bot.tree.command(name=f'eventos_pendentes', description=f'Mostra os eventos esperando aprovação')
async def showPendingEvents(ctx: discord.Interaction):
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = getAllPendingApprovalEvents(mydbAndCursor[0])
    endConnection(mydbAndCursor)
    if result:
        eventsResponse = '\n\n'.join(
    f'''> # {event["event_name"].title()} (id - {event["id"]})
>    **Data**: {event["starting_datetime"].strftime("%d/%m/%Y") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") else f"{event['starting_datetime'].strftime('%d')} a {event['ending_datetime'].strftime('%d/%m/%Y')}"}{" - das "+event["starting_datetime"].strftime("%H:%M")+" às "+event["ending_datetime"].strftime("%H:%M") if event["starting_datetime"] == event["ending_datetime"] else ''}
>    **Local**: {event["city"]}, {event["state_abbrev"]}
>    **Endereço**: {event["address"]} ''' + '\n'+
    '\n'.join(filter(None, [
        f">    **Chat do evento**: <{event['group_chat_link']}>" if event['group_chat_link']!=None else '',
        f">    **Site**: <{event['website']}>" if event['website']!=None else '',
        f'''>    **Preço**: {"A partir de R$"+str(f"{event['price']:.2f}").replace('.',',') if event['price']!=0 else 'Gratuito'}'''
        ]))
        for event in sorted(result, key=lambda event: event["starting_datetime"]))
        await ctx.followup.send(content=f'''Aqui estão os eventos registrados esperando aprovação:\n{eventsResponse}\n
```Se você quiser aprovar um evento, use o comando "/evento_aprovar <id do evento>"```''')
    else:
        return await ctx.followup.send(content=f'Não há eventos a serem aprovados... talvez seja a hora de buscar novos eventos!')


@bot.tree.command(name=f'evento_aprovar', description=f'Aprova um evento pendente')
async def approveEvent(ctx: discord.Interaction, event_id: int):
    if ctx.user.id != 167436511787220992:
        return await ctx.response.send_message(content='Você não tem permissão para fazer isso', ephemeral=True)
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = approveEventById(mydbAndCursor[0], event_id)
    endConnectionWithCommit(mydbAndCursor)
    if result == True:
        return await ctx.followup.send(content=f'O evento foi aprovado com sucesso!')
    elif result == "não encontrado":
        return await ctx.followup.send(content=f'Não foi possível encontrar um evento pendente com esse id! tem certeza que digitou o id certo?')
    elif result == False:
        return await ctx.followup.send(content=f'Não foi possível aprovar o evento')


@bot.tree.command(name=f'evento_add_staff', description=f'Adiciona um membro da staff como organizador de um evento')
async def addStaffToEvent(ctx: discord.Interaction, event_id: int, staff: discord.Member):
    pass


####################################################################################################################
# COMANDO DE CONEXÃO DE CONTAS
####################################################################################################################


@bot.tree.command(name=f'adm-conectar_conta', description=f'Conecta sua conta do discord com a do telegram')
async def connectAccount(ctx: discord.Interaction,user: discord.Member, telegram_username: str):
    mydbAndCursor = startConnection()
    await ctx.response.defer()
    result = admConnectTelegramAccount(mydbAndCursor[0], user, telegram_username)
    endConnectionWithCommit(mydbAndCursor)
    if result:
        return await ctx.followup.send(content=f'Sua conta foi conectada com sucesso! agora você pode usar os comandos do bot no discord e no telegram', ephemeral=False)
    else:
        return await ctx.followup.send(content=f'Não foi possível conectar sua conta! você já está conectado?', ephemeral=True)


####################################################################################################################
# COMANDOS DE INTERAÇÕES DO CODDY
####################################################################################################################


@bot.tree.command(name=f'{BOT_NAME.lower()}_diz', description=f'Faz {BOT_NAME} falar em um canal de texto')
async def sayAsCoddy(ctx: discord.Interaction, channel: discord.TextChannel, message: str):
    channelId = discord.utils.get(ctx.guild.channels, name=channel.name)
    await channelId.send(message)
    resp = await ctx.response.send_message(content='mensagem enviada!', ephemeral=True)
    return resp

@bot.tree.command(name=f'{BOT_NAME.lower()}_status', description=f'Muda o status do {BOT_NAME}')
async def changeMood(ctx: discord.Interaction, mood: Literal['jogando','ouvindo','assistindo','mensagem'], message: str):
    moodDiscord = 'playing' if mood == 'jogando' else 'listening' if mood == 'ouvindo' else 'watching'
    if mood == 'mensagem':
        await bot.change_presence(activity=discord.CustomActivity(name=message))
        resp = await ctx.response.send_message(content=f'{BOT_NAME} está com o status de "{message}"', ephemeral=True)
    else:
        await bot.change_presence(activity=discord.Activity(type=getattr(discord.ActivityType, moodDiscord), name=message))
        resp = await ctx.response.send_message(content=f'{BOT_NAME} está {mood} {message}!', ephemeral=True)
    return resp


####################################################################################################################
# COMANDOS DE XP
####################################################################################################################


@bot.tree.command(name=f'xp', description=f'Mostra a quantidade de xp de um membro')
async def showXp(ctx: discord.Interaction, member: discord.Member):
    pass

@bot.tree.command(name=f'xp_ranking', description=f'Mostra o ranking de xp dos membros')
async def showXpRanking(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'xp_resetar', description=f'Resetar a quantidade de xp de um membro')
async def resetXp(ctx: discord.Interaction, member: discord.Member):
    pass

@bot.tree.command(name=f'xp_resetar_todos', description=f'Resetar a quantidade de xp de todos os membros')
async def resetAllXp(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'xp_adicionar', description=f'Adiciona xp a um membro')
async def addXp(ctx: discord.Interaction, member: discord.Member, xp: int):
    pass

@bot.tree.command(name=f'xp_remover', description=f'Remove xp de um membro')
async def removeXp(ctx: discord.Interaction, member: discord.Member, xp: int):
    pass

###############################################################

@bot.tree.command(name=f'loja', description=f'Compre itens com seu dinheiro')
async def shop(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'rp_inventario', description=f'Mostra os itens que você possui')
async def inventory(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'rp_usar', description=f'Usa um item do seu inventário')
async def useItem(ctx: discord.Interaction, item: str):
    pass

@bot.tree.command(name=f'rp_vender', description=f'Vende um item do seu inventário')
async def sellItem(ctx: discord.Interaction, item: str):
    pass

################################################################

@bot.tree.command(name=f'daily', description=f'Pega sua recompensa diária')
async def daily(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'rp_banho', description=f'Tomar banho dá xp sabia?')
async def bath(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'rp_trabalhar', description=f'Trabalha em troca de xp e dinheiro')
async def work(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'rp_duelo', description=f'Desafie alguém para um duelo')
async def duel(ctx: discord.Interaction, member: discord.Member):
    pass

@bot.tree.command(name=f'rp_desenhar', description=f'Desenhe algo!')
async def draw(ctx: discord.Interaction):
    pass

@bot.tree.command(name=f'rp_escrever', description=f'Escreva uma história')
async def write(ctx: discord.Interaction):
    pass

""" @bot.tree.command(name=f'rp_missao', description=f'Complete missões para ganhar xp e dinheiro')
async def mission(ctx: discord.Interaction):
    pass """




####################################################################################################################
# COMANDOS DE MODERAÇÃO
####################################################################################################################


""" @bot.tree.command(name=f'adm-banir', description=f'Bane um membro do servidor')


@bot.tree.command(name=f'warn', description=f'Aplica um warn em um membro') """


@bot.tree.command(name=f'portaria_cargos', description=f'Permite que um membro na portaria pegue seus cargos')
async def portariaCargos(ctx: discord.Interaction, member: discord.Member):
    portariaCategory = discord.utils.get(ctx.guild.categories, id=753342674576211999)
    provisoriaCategory = discord.utils.get(ctx.guild.categories, id=1178531112042111016)
    carteirinhaDeCargos = ctx.guild.get_role(860492272054829077)
    for channel in portariaCategory.channels+provisoriaCategory.channels:
        if channel.permissions_for(member).send_messages:
            if carteirinhaDeCargos in member.roles:
                return await ctx.response.send_message(content=f'O membro <@{member.id}> ja está com a carteirinha de cargos!', ephemeral=True)
            if (datetime.now().date() - member.created_at.date()).days < 30:
                return await ctx.response.send_message(content=f'''<@{member.id}> não pode pegar seus cargos agora! A conta foi criada a menos de 30 dias
        Use o comando "/portaria_aprovar" e apos 15 dias, quando vencer a carteirinha provisória, ele poderá pegar seus cargos''', ephemeral=True)
            await member.add_roles(carteirinhaDeCargos)
            return await ctx.response.send_message(content=f'<@{member.id}> agora pode pegar seus cargos!', ephemeral=True)
    return await ctx.response.send_message(content=f'O membro <@{member.id}> não está na portaria', ephemeral=True)


@bot.tree.command(name=f'portaria_aprovar', description=f'Aprova um membro que está esperando aprovação na portaria')
async def approvePortaria(ctx: discord.Interaction, member: discord.Member, data_nascimento: str=None):
    provisoriaCategory = discord.utils.get(ctx.guild.categories, id=1178531112042111016)
    portariaCategory = discord.utils.get(ctx.guild.categories, id=753342674576211999)
    carteirinhaProvisoria = ctx.guild.get_role(923523251852955668)
    cargoVisitante = ctx.guild.get_role(860453882323927060)
    cargoMaior18 = ctx.guild.get_role(753711082656497875)
    cargoMenor18 = ctx.guild.get_role(753711433224814662)
    carteirinhaCargos = ctx.guild.get_role(860492272054829077)
    for channel in (portariaCategory.channels+provisoriaCategory.channels):
        if channel.permissions_for(member).send_messages:
            if (cargoVisitante in member.roles and carteirinhaProvisoria in member.roles) or (cargoVisitante not in member.roles):
                return await ctx.response.send_message(content=f'O membro <@{member.id}> ja foi aprovado!', ephemeral=True)
            if (datetime.now().date() - member.created_at.date()).days < 30:
                await ctx.response.send_message(content=f'Atribuindo carteirinha provisória...', ephemeral=True)
                await member.add_roles(carteirinhaProvisoria, cargoVisitante)
                await member.remove_roles(carteirinhaCargos)
                mydbAndCursor = startConnection()
                duration = timedelta(days=15)
                expiration_date = datetime.utcnow() + duration
                await ctx.edit_original_response(content=f'O membro <@{member.id}> entrará no servidor com **carteirinha provisória** e terá acesso restrito ao servidor por sua conta ter **menos de 30 dias**. \nLembre de avisar o membro sobre isso')
                assignTempRole(mydbAndCursor[0], ctx.guild_id, member, carteirinhaProvisoria.id, expiration_date, 'Carteirinha provisória')
                endConnectionWithCommit(mydbAndCursor)
                await channel.edit(name=f'{channel.name}-provisória' if not channel.name.__contains__('provisória') else channel.name, category=provisoriaCategory)
                return 
            regex = r'(\d{1,2})(\s*\/\s*|\sd[eo]\s)(\d{1,2}|(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))(\s*\/\s*|\sd[eo]\s)(\d{2,4})'
            pattern = re.compile(regex)
            months = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            async for message in channel.history(limit=100):
                if message.author.id != member.id: pass
                matchMessage = pattern.search(message.content)
                if message.embeds and message.embeds.__len__() > 1:
                    matchEmbeded = pattern.search(message.embeds[1].description) if isinstance(message.embeds[1].description, str) else None  
                else: matchEmbeded = None
                if matchMessage or matchEmbeded or data_nascimento:
                    if data_nascimento: 
                        date_str = data_nascimento
                    else: 
                        date_str = matchMessage.group() if matchMessage else matchEmbeded.group()
                    await ctx.response.send_message(content=f'verificando idade...', ephemeral=True)
                    try:
                        if '/' in date_str:
                            if [i for i in months if i in date_str]:
                                day, month_str, year = date_str.split('/').strip()
                                month = months.index(month_str) + 1
                                if str(year).__len__()<=2 :year+=2000 if year < (datetime.now().date().year - 2000) else 1900
                                day, year = int(day), int(year)
                            else:
                                day, month, year = map(int, date_str.replace(' ','').split('/'))
                                if str(year).__len__()<=2 :year+=2000 if year < (datetime.now().date().year - 2000) else 1900
                        else:
                            date_str = [x for x in date_str.split(' ') if x != None and (x.isdigit() or x in months) ]
                            day, month_str, year = date_str
                            month = months.index(month_str) + 1
                            if str(year).__len__()<=2 :year+=2000 if year < (datetime.now().date().year - 2000) else 1900
                            day, year = int(day), int(year)
                        date = datetime(year, month, day)
                        if date.year > 1975 and date.year < datetime.now().year:
                            age = (datetime.now().date() - date.date()).days
                            cargoMenor13 = ctx.guild.get_role(938399264231534632)
                            if not (cargoMaior18 in member.roles or cargoMenor18 in member.roles) and age >= 4745:
                                return await ctx.edit_original_response(content=f'O membro <@{member.id}> ainda não pegou seus cargos!' if carteirinhaCargos in member.roles 
                                                                        else f'O membro <@{member.id}> ainda não tem a carteirinha de cargos, use o comando "/portaria_cargos" antes')
                            if age >= 6570: #18+ anos
                                await member.add_roles(cargoMaior18)
                                await member.remove_roles(cargoMenor18, cargoMenor13)
                            elif age >= 4745: #13+ anos
                                await member.add_roles(cargoMenor18)
                                await member.remove_roles(cargoMaior18, cargoMenor13)
                            else:
                                await member.remove_roles(cargoMaior18, cargoMenor18)
                                await member.add_roles(carteirinhaProvisoria, cargoVisitante, cargoMenor13)
                                await channel.edit(name=f'{channel.name}-provisória' if not channel.name.__contains__('provisória') else channel.name,category=provisoriaCategory)
                                return await ctx.edit_original_response(content=f'Por ser menor de 13 anos, o membro <@{member.id}> entrará no servidor com carteirinha provisória e terá acesso restrito ao servidor. Lembre de avisar o membro sobre isso.')
                            await member.remove_roles(carteirinhaCargos, cargoVisitante)
                            return await ctx.edit_original_response(content=f'O membro <@{member.id}> foi aprovado com sucesso!\nLembre de dar boas vindas a ele no <#753348623844114452> :3')
                        else:
                            return await ctx.edit_original_response(content=f'Data inválida encontrada: {date_str}\nO membro tem {(datetime.now().date() - date.date()).year} anos?')
                    except ValueError:
                        return await ctx.edit_original_response(content=f'Data inválida encontrada: {date_str}')
            return await ctx.response.send_message(content=f'Não foi possível encontrar a data de nascimento do membro <@{member.id}> na portaria\nEm ultimo caso, digite a data de nascimento nos argumentos do comando.', ephemeral=True)
    return await ctx.response.send_message(content=f'O membro <@{member.id}> não está na portaria', ephemeral=True)
    




####################################################################################################################
# COMANDOS UTILITARIOS
####################################################################################################################


@bot.tree.command(name=f'call_titio', description=f'Faz {BOT_NAME} chamar o titio')
async def callAdmin(ctx: discord.Interaction, message: str):
    requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage?chat_id={os.getenv('TELEGRAM_ADMIN')}&text={ctx.user.name}: {message}")
    try:
        resp = await ctx.response.send_message(content='O titio foi avisado! agora é só esperar :3', ephemeral=True)
        return resp
    except Exception as e:
        if resp:
            channel = await ctx.user.create_dm()
            await channel.send(content='O titio foi avisado! agora é só esperar :3')
        pass


@bot.tree.command(name=f'temp_role', description=f'Adiciona um cargo temporário a um membro')
async def addTempRole(ctx: discord.Interaction, member: discord.Member, role: discord.Role, duration: str):
    mydbAndCursor = startConnection()
    #duration pode ser dias(d), semanas(s), meses(m). exemplo: 1d, 2s, 3m
    duration = duration.lower()
    if duration[-1] not in ['d', 's', 'm'] or not duration[:-1].isdigit() or duration.__len__() < 2:
        return await ctx.response.send_message(content='''Duração inválida! Você informou uma duração no formato "1d", "2s" ou "3m"?\nSiglas: d=dias, s=semanas, m=meses''', ephemeral=True)
    if int(duration[:-1]) == 0:
        return await ctx.response.send_message(content='''Duração inválida! Você informou uma duração maior que 0?''', ephemeral=True)
    if role in member.roles:
        return await ctx.response.send_message(content=f'O membro <@{member.id}> já tem o cargo {role.name}!', ephemeral=True)
    #calcula qual vai ser a data de expiração do cargo
    if duration[-1] == 'd':
        duration = timedelta(days=int(duration[:-1]))
    elif duration[-1] == 's':
        duration = timedelta(weeks=int(duration[:-1]))
    else:
        duration = timedelta(months=int(duration[:-1]))
    expiration_date = datetime.utcnow() + duration
    await ctx.response.send_message(content=f'Adicionando o cargo...', ephemeral=True)
    roleAssignment = assignTempRole(mydbAndCursor[0], ctx.guild_id, member, role.id, expiration_date, 'porque sim')
    endConnectionWithCommit(mydbAndCursor)
    if roleAssignment:
        await member.add_roles(role)
        return await ctx.edit_original_response(content=f'O membro <@{member.id}> agora tem o cargo {role.name} por {duration}!')


#@bot.tree.command(name='mod-calc_idade', description=f'Use esse recurso para calcular a idade de alguém de acordo com a data de nascimento')
async def calc_idade(ctx, message: str):
    try:
        idade = calcular_idade(message)
        if idade == 'Entrada inválida':
            raise Exception
        await ctx.response.send_message(content=f'{message}: {idade} anos', ephemeral=True)
    except Exception:
        await ctx.response.send_message(content='Data de nascimento inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>', ephemeral=True)

#@bot.tree.command(name='mod-check_new_member', description=f'Use esse recurso para checar se um novo membro é elegivel a usar a carteirinha de cargos ou não')
async def check_new_member(ctx, member:discord.Member, age:int):
        account_age = datetime.utcnow().date() - member.created_at.date()
        if age<=13 or account_age.days <= 30:
            conditions = 'idade menor do que 13 anos e conta com menos de 30 dias de idade' if (age<=13 and account_age.days <= 30) else 'conta criada a menos de 30 dias' if account_age.days <= 30 else 'idade menor do que 13 anos'
            return await ctx.response.send_message(content=f'o membro {member.name} precisará usar carteirinha temporária, o membro possui {conditions}', ephemeral=True)
        return await ctx.response.send_message(content='O membro não precisará usar carteirinha temporária', ephemeral=True)

def run_discord_client(chatBot):
    bot.chatBot = chatBot
    bot.run(os.getenv('DISCORD_TOKEN'))