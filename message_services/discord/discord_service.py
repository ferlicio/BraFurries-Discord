from message_services.discord.routine_functions.routine_functions import *
from message_services.discord.discord_events import *
from commands.default_commands import calcular_idade
from IA_Functions.terceiras.openAI import *
from verification_functions.verification import *
from discord.ext import tasks
from models.bot import *
from models.locals import *
from database.database import *
from datetime import datetime, timedelta
from typing import Literal
from dateutil import tz
import requests
import discord
import re

intents = discord.Intents.default()
for DISCORD_INTENT in DISCORD_INTENTS:
    setattr(intents, DISCORD_INTENT, True)
bot = MyBot(config=None,command_prefix=DISCORD_BOT_PREFIX, intents=discord.Intents.all())
levelConfig = None


@bot.event
async def on_ready():
    print(f'Logado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)} Comandos sincronizados com sucesso!')
    except Exception as e:
        print(e)
    guild = bot.get_guild(DISCORD_GUILD_ID)
    bot.config = Config(getConfig(guild))
    print(bot.config)
    if DISCORD_BUMP_WARN: bumpWarning.start()
    if DISCORD_HAS_BUMP_REWARD: bumpReward.start()
    cronJobs12h.start()
    cronJobs2h.start()
    cronJobs30m.start()
    configForVips.start()

@bot.event
async def on_message(message: discord.Message):
    await warnMemberWithMissingQuestions(message)

    if message.author.bot:
        return
    
    await mentionArtRoles(bot, message)
    await secureArtPosts(message)
    await botAnswerOnMention(bot,message)

@bot.event
async def on_reaction_add(reaction, user):
    pass

@bot.event
async def on_member_update(before:discord.member.Member, after:discord.member.Member):
    checkRolesUpdate(before, after)



@tasks.loop(hours=12)
async def cronJobs12h():
    await removeTempRoles(bot)

@tasks.loop(hours=2)
async def cronJobs2h():
    await checkTicketsState(bot)

@tasks.loop(minutes=30)
async def cronJobs30m():
    getServerConfigurations(bot)
    if bot.config.hasLevels != False: 
        print('Configurações de níveis não encontradas')
        pass
    




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
        for role in guild.roles:
            if role.name.__contains__(DISCORD_VIP_CUSTOM_ROLE_PREFIX):
                if role.color == discord.Color.default() and role.display_icon == None:
                    await role.delete()
                else:
                    member = None
                    for serverMember in role.members:
                        if not VIPMembers.__contains__(serverMember):
                            member = serverMember
                            await serverMember.remove_roles(role)
                    if role.members.__len__() == 0:
                        regex = rf'(?:{DISCORD_VIP_CUSTOM_ROLE_PREFIX} )(.*)'
                        pattern = re.compile(regex)
                        MemberName = pattern.search(role.name).group(1)
                        member = guild.get_member_named(MemberName)
                        if member == None: 
                            await role.delete()
                            continue
                    hexColor = '#%02x%02x%02x' % (role.color.r, role.color.g, role.color.b)
                    mydbAndCursor = startConnection()
                    roleSaved = saveCustomRole(mydbAndCursor[0],guild.id, member, int(str(hexColor).replace('#','0x'),16))
                    endConnectionWithCommit(mydbAndCursor)
                    if roleSaved: await role.delete()
        VIPMembers = [obj.name for obj in VIPMembers] #transforma a lista de membros em uma lista de nomes
        print('Membros VIPs encontrados:')
        print(VIPMembers)
        
        mydbAndCursor = startConnection()
        getAllCustomRoles(mydbAndCursor[0], guild.id)
        endConnection(mydbAndCursor)
        return
                
    else:
        print(f'Não foi possível encontrar um cargo VIP no servidor {guild.name}')



####################################################################################################################
# COMANDOS VIP
####################################################################################################################


@bot.tree.command(name=f'vip-mudar_cor', description=f'Muda a cor do cargo VIP do membro')
async def changeVipColor(ctx: discord.Interaction, cor: str):
    userVipRoles = [role.id for role in ctx.user.roles if DISCORD_VIP_ROLES_ID.__contains__(role.id)]
    if userVipRoles.__len__() != 0:
        if not re.match(r'^#(?:[a-fA-F0-9]{3}){1,2}$', cor):
            return await ctx.response.send_message(content='''# Cor invalida!\n 
Você precisa informar uma cor no formato Hex (#000000).
Você pode procurar por uma cor em https://htmlcolorcodes.com/color-picker/ e testa-la usando o comando "?color #000000"''', ephemeral=False)
        if not await colorIsAvailable(cor):
            return await ctx.response.send_message(content='''Cor inválida! você precisa informar uma cor que não seja muito parecida com a cor de algum cargo da staff''', ephemeral=True)
        corFormatada = int(cor.replace('#','0x'),16)
        customRole = await addVipRole(ctx)
        await customRole.edit(color=corFormatada)
        await ctx.response.send_message(content=f'Cor do cargo VIP alterada para {cor} com sucesso!', ephemeral=False)
        mydbAndCursor = startConnection()
        saveCustomRole(mydbAndCursor[0], ctx.guild_id, ctx.user, color=corFormatada)
        return endConnectionWithCommit(mydbAndCursor)
    return await ctx.response.send_message(content='Você não é vip! você não pode fazer isso', ephemeral=True)

@bot.tree.command(name=f'vip-mudar_icone', description=f'Muda o icone do cargo VIP do membro')
async def changeVipIcon(ctx: discord.Interaction, icon: str):
    userVipRoles = [role.id for role in ctx.user.roles if DISCORD_VIP_ROLES_ID.__contains__(role.id)]
    if userVipRoles.__len__() != 0:
        try:
            customRole = await addVipRole(ctx)
            if icon.__contains__('<') or icon.__contains__('>') or icon.__contains__(':'):
                try:
                    emoji = ctx.guild.get_emoji(int(icon.replace('<','').replace('>','').split(':')[2]))
                except:
                    return await ctx.response.send_message(content='''Ícone inválido! apenas emojis do servidor são permitidos''', ephemeral=True)
                icon = await emoji.read()
            await customRole.edit(display_icon=icon)
            await ctx.response.send_message(content='Ícone do cargo VIP alterado com sucesso!', ephemeral=False)
            mydbAndCursor = startConnection()
            saveCustomRole(mydbAndCursor[0], ctx.guild_id, ctx.user, iconId=emoji.id)
            return endConnectionWithCommit(mydbAndCursor)
        except Exception as e:
            print(e)
            return await ctx.response.send_message(content='''Algo deu errado, avise o titio sobre!''', ephemeral=True)
    return await ctx.response.send_message(content='Você não é vip! você não pode fazer isso', ephemeral=True)




####################################################################################################################
# COMANDOS DE INFORMAÇÕES DE MEMBROS
####################################################################################################################


@bot.tree.command(name=f'registrar_local', description=f'Registra o seu local')
async def registerLocal(ctx: discord.Interaction, local: str):
    mydbAndCursor = startConnection()
    availableLocals = getAllLocals(mydbAndCursor[0])
    if stateLetterCodes[local]:
        await ctx.response.defer()
        result = includeLocale(mydbAndCursor[0], ctx.guild.id, local.upper(), ctx.user, availableLocals)
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
    if stateLetterCodes[local]:
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
    else:
        return await ctx.response.send_message(content='''Local inválido! Você deve informar uma sigla de Estado válido''', ephemeral=True)
    

@bot.tree.command(name=f'registrar_aniversario', description=f'Registra seu aniversário')
async def registerBirthday(ctx: discord.Interaction, data: str, mencionavel: Literal["sim", "não"]):
    try:
        datetime.strptime(data, "%d/%m/%Y")
    except ValueError:
        return await ctx.response.send_message(content='''Data de nascimento inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
    birthdayAsDate = datetime.strptime(data, '%d/%m/%Y').date()
    mencionavel = True if mencionavel == "sim" else False
    await ctx.response.defer()
    mydbAndCursor = startConnection()
    result = includeBirthday(mydbAndCursor[0], ctx.guild.id, birthdayAsDate, ctx.user, mencionavel)
    endConnectionWithCommit(mydbAndCursor)
    if result:
        return await ctx.followup.send(content=f'você foi registrado com o aniversário {data}!', ephemeral=False)
    else:
        return await ctx.followup.send(content=f'Você ja está registrado', ephemeral=True)
    

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
    result = admConnectTelegramAccount(mydbAndCursor[0], ctx.guild.id, user, telegram_username)
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
# COMANDOS DE PERFIL
####################################################################################################################




####################################################################################################################
# COMANDOS DE MODERAÇÃO
####################################################################################################################


@bot.tree.command(name=f'relatorio-portaria', description=f'Gera um relatório de atividades na portaria')
async def test(ctx: discord.Interaction, periodo:Literal['semana', 'mês']):
    if periodo == 'semana':
        InitialDate = datetime.now() - timedelta(days=7)
    elif periodo == 'mês':
        InitialDate = datetime.now() - timedelta(days=30)
    await ctx.response.send_message(content='Gerando relatório...')
    try:
        channel = discord.utils.get(ctx.guild.channels, id=1140486877951033375)
        staffRoles = [discord.utils.get(ctx.guild.roles, id=829140185777307658),
        discord.utils.get(ctx.guild.roles, id=775483946501799947),
        discord.utils.get(ctx.guild.roles, id=1100331034542886933)]
        staffMembers = []
        for role in staffRoles:
            for member in role.members:
                staffMembers.append(member)
        membersStats = []
        for staff in staffMembers:
            membersStats.append({
                'id': staff.id,
                'name': staff.display_name,
                'ticketsAttended': 0
            })
        totalTickets = 0
        async for message in channel.history(limit=None, after=InitialDate, before=datetime.now()):
            if message.author.id == 557628352828014614:
                if message.embeds.__len__() >= 1:
                    for field in message.embeds[0].fields:
                        if field.name == 'Users in transcript':
                            totalTickets +=1
                            regex = r'<@(\d+)>'
                            pattern = re.compile(regex)
                            matchEmbeded = pattern.findall(field.value)
                            if matchEmbeded:
                                for user in matchEmbeded:
                                    for staff in membersStats:
                                        if int(user) == staff['id']:
                                            staff['ticketsAttended'] += 1
                                            continue
            pass
        response = 'Relatório de atividades na portaria:\n'
        membersStats = sorted(membersStats, key= lambda m: m["ticketsAttended"], reverse=True)
        for staff in membersStats:
            response += '**{0:32}**  {1:10} tickets atendidos\n'.format(staff["name"],staff["ticketsAttended"])
        response += f'\n**Periodo: {periodo}**'
        response += f'\n**Total de tickets: {totalTickets}**'
        await ctx.edit_original_response(content=response)
    except:
        await ctx.edit_original_response(content='Erro ao gerar o relatório!')
    pass


@bot.tree.command(name=f'perfil', description=f'Mostra o perfil de um membro')
async def profile(ctx: discord.Interaction, member: discord.Member):
    await ctx.response.defer()
    mydbAndCursor = startConnection()
    memberProfile = getUserInfo(mydbAndCursor[0], member, ctx.guild.id)
    endConnectionWithCommit(mydbAndCursor)
    profileDescription = generateUserDescription(memberProfile)
    embedUserProfile = discord.Embed(
        color=discord.Color.from_str('#febf10'),
        title='{0} - ID {1:64}'.format(member.name,str(member.id)), 
        description=profileDescription)
    embedUserProfile.set_thumbnail(url=member.avatar.url)
    embedUserProfile.set_author(
        name=(member.display_name)+f' (level {memberProfile.level})', 
        icon_url=member.guild_avatar.url if member.guild_avatar != None else member.avatar.url)
    embedUserProfile.set_footer(text=f'{memberProfile.warnings.__len__()} Warns{"  -  Ultimo warn em "+datetime.now().strftime("%d/%m/%Y") if memberProfile.warnings.__len__() > 0 else f""}{"  -  >> DE CASTIGO <<" if member.is_timed_out() else ""}')
    await ctx.followup.send(embed=embedUserProfile)


@bot.tree.command(name=f'registrar_usuario', description=f'Registra um membro')
async def profile(ctx: discord.Interaction, member: discord.Member, data_aprovacao:str, aniversario:str):
    mydbAndCursor = startConnection()
    data_aprovacao = verifyDate(data_aprovacao)
    aniversario = verifyDate(aniversario)
    await ctx.response.send_message(content='Registrando usuário...')
    if not data_aprovacao: return await ctx.response.send_message(content='Data de aprovação no formato errado! use o formato dd/MM/YYYY')
    if not aniversario: return await ctx.response.send_message(content='Data de aniversário no formato errado! use o formato dd/MM/YYYY')
    registered = registerUser(mydbAndCursor[0], ctx.guild.id, member, aniversario, data_aprovacao)
    endConnectionWithCommit(mydbAndCursor)
    if registered:
        return await ctx.edit_original_response(content='Membro registrado com sucesso!')
    else: 
        return await ctx.edit_original_response(content='Não foi possível registrar o usuário')


"""@bot.tree.command(name=f'adm-banir', description=f'Bane um membro do servidor')"""



@bot.tree.command(name=f'warn', description=f'Aplica um warn em um membro')
async def warn(ctx: discord.Interaction, membro: discord.Member, motivo: str):
    mydbAndCursor = startConnection()
    #staffRoles = getStaffRoles(ctx.guild)
    await ctx.response.send_message("Registrando warn...")
    if True: #adicionar verificação de cargo de staff
        warnings = warnMember(mydbAndCursor[0], ctx.guild.id, membro, motivo)
        endConnectionWithCommit(mydbAndCursor)
        if warnings:
            if warnings['warningsCount'] < (int(warnings['warningsLimit']) - 1):
                await membro.send(f'Você recebeu um warn por "{motivo}", totalizando {warnings["warningsCount"]}! Cuidado com suas ações no servidor!')
                return await ctx.edit_original_response(content=f'Warn registrado com sucesso! total de {warnings["warningsCount"]} warns no membro {membro.mention}') 
            elif warnings['warningsCount'] < (int(warnings['warningsLimit'])):
                await membro.send(f'Você recebeu um warn por "{motivo}", totalizando {warnings["warningsCount"]}! Cuidado, caso receba mais um warn, você será banido do servidor')
                return await ctx.edit_original_response(content=f'Warn registrado com sucesso! total de {warnings["warningsCount"]} warns no membro {membro.mention} \nAvise ao membro sobre o risco de banimento!')
            else:
                await membro.send(f'Você recebeu um warn por "{motivo}" e atingiu o limite de {warnings["warningsCount"]} warnings do servidor!')
                return await ctx.edit_original_response(content=f'Warn registrado com sucesso! \nCom esse warn, o membro {membro.mention} atingiu o limite de warns do servidor e deverá ser **Banido**')
        return await ctx.edit_original_response(content=f'Não foi possível aplicar o warn no membro {membro.mention}')
    return await ctx.response.send_message(content='Você não tem permissão para fazer isso', ephemeral=True)


@bot.tree.command(name=f'portaria_cargos', description=f'Permite que um membro na portaria pegue seus cargos')
async def portariaCargos(ctx: discord.Interaction, member: discord.Member):
    portariaCategory = discord.utils.get(ctx.guild.categories, id=753342674576211999)
    provisoriaCategory = discord.utils.get(ctx.guild.categories, id=1178531112042111016)
    carteirinhaDeCargos = ctx.guild.get_role(860492272054829077)
    for channel in portariaCategory.channels+provisoriaCategory.channels:
        if channel.permissions_for(member).send_messages:
            if (datetime.now().date() - member.created_at.date()).days < 30 and not channel.name.__contains__("provisória"):
                return await ctx.response.send_message(content=f'''<@{member.id}> não pode pegar seus cargos agora! A conta foi criada a menos de 30 dias
        Use o comando "/portaria_aprovar" e apos 15 dias, quando vencer a carteirinha provisória, ele poderá pegar seus cargos''', ephemeral=True)
            if carteirinhaDeCargos in member.roles:
                return await ctx.response.send_message(content=f'O membro <@{member.id}> ja está com a carteirinha de cargos!', ephemeral=True)
            await member.add_roles(carteirinhaDeCargos)
            await channel.edit(name=f'{channel.name}-🆔' if not channel.name.__contains__('-🆔') else channel.name)
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
    cargoMenor13 = ctx.guild.get_role(938399264231534632)
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
            regex = r'(\d{1,2})(?:\s*(?:d[eo]|\/|\\|\.)\s*|\s*)(\d{1,2}|(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))(?:\s*(?:d[eo]|\/|\\|\.)\s*|\s*)(\d{2,4})'
            pattern = re.compile(regex)
            months = ['00','janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            async for message in channel.history(limit=1, oldest_first=True):
                if data_nascimento:
                    matchEmbeded = pattern.search(data_nascimento)
                    if not matchEmbeded:
                        return await ctx.response.send_message(content=f'Você digitou uma data inválida: {data_nascimento}', ephemeral=True)
                else:
                    matchEmbeded = pattern.search(message.embeds[1].description) if isinstance(message.embeds[1].description, str) else None
                if matchEmbeded:
                    await ctx.response.send_message(content=f'registrando usuario...', ephemeral=True)
                    try:
                        day = int(matchEmbeded.group(1))
                        month = int(matchEmbeded.group(2) if matchEmbeded.group(2).isdigit() else months.index(matchEmbeded.group(2)))
                        year = int(matchEmbeded.group(3))
                        if str(year).__len__()<=2 :year+=2000 if year < (datetime.now().date().year - 2000) else 1900
                        birthday = datetime(year, month, day)
                        if birthday.year > 1975 and birthday.year < datetime.now().year:
                            age = (datetime.now().date() - birthday.date()).days
                            if not (cargoMaior18 in member.roles or cargoMenor18 in member.roles) and age >= 4745:
                                return await ctx.edit_original_response(content=f'O membro <@{member.id}> ainda não pegou seus cargos!' if carteirinhaCargos in member.roles 
                                                                        else f'O membro <@{member.id}> ainda não tem a carteirinha de cargos, use o comando "/portaria_cargos" antes')
                            mydbAndCursor = startConnection()
                            registerUser(mydbAndCursor[0], ctx.guild.id, member, birthday.date())
                            endConnectionWithCommit(mydbAndCursor)
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
                            await channel.edit(name=f'{channel.name}-✅' if not channel.name.__contains__('-✅') else channel.name)
                            return await ctx.edit_original_response(content=f'O membro <@{member.id}> foi aprovado com sucesso!\nLembre de dar boas vindas a ele no <#753348623844114452> :3')
                        else:
                            return await ctx.edit_original_response(content=f'Data inválida encontrada: {matchEmbeded.group(0)}\nO membro tem {(datetime.now().date() - birthday.date()).year} anos?')
                    except ValueError:
                        return await ctx.edit_original_response(content=f'Data inválida encontrada: {matchEmbeded.group(0)}')
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
    ####### adicionar para aceitar data especifica também
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

@bot.tree.command(name=f'testes', description=f'teste')
async def test(ctx: discord.Interaction):
    guild = bot.get_guild(DISCORD_GUILD_ID)  # Substitua ID_DO_SERVIDOR pelo ID do seu servidor
    VIPRoles = getVIPConfigurations(guild)['VIPRoles']
    VIPMembers = getVIPMembers(guild)
    await ctx.response.send_message(content=f'Carregando...', ephemeral=True)
    if VIPRoles:
        #deletar os que não tem config
        #salvar e deletar os que não tem mais vip/não tem membros com cargo
        for role in guild.roles:
            if role.name.__contains__(DISCORD_VIP_CUSTOM_ROLE_PREFIX):
                if role.color == discord.Color.default() and role.display_icon == None:
                    await role.delete()
                else:
                    member = None
                    for serverMember in role.members:
                        if not VIPMembers.__contains__(serverMember):
                            member = serverMember
                            await serverMember.remove_roles(role)
                    if role.members.__len__() == 0:
                        regex = rf'(?:{DISCORD_VIP_CUSTOM_ROLE_PREFIX} )(.*)'
                        pattern = re.compile(regex)
                        MemberName = pattern.search(role.name).group(1)
                        member = guild.get_member_named(MemberName)
                        if member == None: 
                            await role.delete()
                            continue
                    hexColor = '#%02x%02x%02x' % (role.color.r, role.color.g, role.color.b)
                    mydbAndCursor = startConnection()
                    roleSaved = saveCustomRole(mydbAndCursor[0],guild.id, member, int(str(hexColor).replace('#','0x'),16))
                    endConnectionWithCommit(mydbAndCursor)
                    if roleSaved: await role.delete()
        return
    mydbAndCursor = startConnection()
    getAllCustomRoles(mydbAndCursor[0], ctx.guild_id)
    endConnection(mydbAndCursor)


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