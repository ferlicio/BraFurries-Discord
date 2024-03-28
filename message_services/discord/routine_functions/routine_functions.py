from database.database import *
from settings import *
import discord, asyncio
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import _get_lab_color1_vector, _get_lab_color2_matrix
from colormath import color_diff_matrix

def getVIPConfigurations(guild):
    VIPStatus = {'VIPRoles': [], 'hasVIPCustomization': DISCORD_HAS_VIP_CUSTOM_ROLES, 'hasRoleDivision': DISCORD_HAS_ROLE_DIVISION,
                    'VIPRoleDivisionStartID': DISCORD_VIP_ROLE_DIVISION_START_ID, 'VIPRoleDivisionEndID': DISCORD_VIP_ROLE_DIVISION_END_ID}
    VIPRoles = []
    for role in DISCORD_VIP_ROLES_ID:
        VIPRoles.append(discord.utils.get(guild.roles, id=role))
    VIPStatus['VIPRoles'] = VIPRoles
    return VIPStatus

def getVIPMembers(guild):
    VIPConfig = getVIPConfigurations(guild)
    VIPMembers = []
    for VIPRole in VIPConfig['VIPRoles']:
        for member in VIPRole.members:
            VIPMembers.append(member)
    return VIPMembers

def getMemberInRole(guild, roleID):
    role = discord.utils.get(guild.roles, id=roleID)
    members = []
    for member in role.members:
        members.append(member)
    return members

async def rearrangeRoleInsideInterval(guild, roleID, start, end):
    role = discord.utils.get(guild.roles, id=roleID)
    if not(role.position > end.position and role.position < start.position):
        newRolePosition = start.position-1
        await guild.edit_role_positions(positions={role: newRolePosition})

async def localeIsAvailable(ctx, mydbAndCursor, locale):
    availableLocals = getAllLocals(mydbAndCursor[0])
    if locale.upper() in [local_dict['locale_abbrev'] for local_dict in availableLocals]:
        #pegaremos o id do local
        locale_id = [local_dict['id'] for local_dict in availableLocals if local_dict['locale_abbrev'] == locale.upper()][0]
        return locale_id
    else:
        endConnection(mydbAndCursor)
        availableLocalsResponse = ',\n'.join(f'{local["locale_abbrev"]} = {local["locale_name"]}' for local in availableLocals)
        await ctx.response.send_message(content=f'''você precisa fornecer um local existente!
Você deve usar apenas a sigla do local, sem acentos ou espaços.\n
Os locais disponiveis são:\n ```{availableLocalsResponse}```''', ephemeral=True)
        return False
    
def hex_to_rgb(hex_color):
    return sRGBColor.new_from_rgb_hex(hex_color)
    
async def colorIsAvailable(color:str):
    for staff_color in DISCORD_STAFF_COLORS:
        color1_rgb = hex_to_rgb(color)
        color2_rgb = hex_to_rgb(staff_color)

        color1_lab = convert_color(color1_rgb, LabColor)
        color2_lab = convert_color(color2_rgb, LabColor)
        color1_vector = _get_lab_color1_vector(color1_lab)
        color2_matrix = _get_lab_color2_matrix(color2_lab)
        delta_e = color_diff_matrix.delta_e_cie2000(
            color1_vector, color2_matrix, Kl=1, Kc=1, Kh=1)[0]
        
        color_distance = delta_e.item()

        if color_distance < 11.0:
            return False
    return True


async def addVipRole(ctx) -> discord.Role:
    customRole = discord.utils.get(ctx.guild.roles, name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}")
    if customRole == None:
        print(f'Não foi possível encontrar um cargo VIP para {ctx.user.name}')
        customRole = await ctx.guild.create_role(name=f"{DISCORD_VIP_CUSTOM_ROLE_PREFIX} {ctx.user.name}", mentionable=False, reason="Cargo criado para membros VIPs")
        if DISCORD_HAS_ROLE_DIVISION:
            divisionStart = discord.utils.get(ctx.guild.roles, id=DISCORD_VIP_ROLE_DIVISION_START_ID) 
            divisionEnd = discord.utils.get(ctx.guild.roles, id=DISCORD_VIP_ROLE_DIVISION_END_ID)
            await rearrangeRoleInsideInterval(ctx, customRole.id, divisionStart, divisionEnd)
        await ctx.user.add_roles(customRole)
    elif not ctx.user.roles.__contains__(customRole):
        await ctx.user.add_roles(customRole)
    return customRole
    
def formatEventList(eventList):
    sortedEventList = sorted(eventList, key=lambda event: event["starting_datetime"])
    messages = []
    
    for event in sortedEventList:
        formattedEvent = (f'''> # {event["event_name"].title()}
>    **Data**: {event["starting_datetime"].strftime("%d/%m/%Y") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") else f"{event['starting_datetime'].strftime('%d')} a {event['ending_datetime'].strftime('%d/%m/%Y')}"}{" - das "+event["starting_datetime"].strftime("%H:%M")+" às "+event["ending_datetime"].strftime("%H:%M") if event["starting_datetime"] == event["ending_datetime"] else ''}
>    **Local**: {event["city"]}, {event["state_abbrev"]}
>    **Endereço**: {event["address"]} ''' + '\n'+
        '\n'.join(filter(None, [
            f">    **Chat do evento**: <{event['group_chat_link']}>" if event['group_chat_link']!=None else '',
            f">    **Site**: <{event['website']}>" if event['website']!=None else '',
            f'''>    **Preço**: {"Ingressos esgotados" if event['out_of_tickets']
        else "Vendas encerradas" if event['sales_ended']
        else "A partir de R$"+str(f"{event['price']:.2f}").replace('.',',') if event['price']!=0 else 'Gratuito'}'''
            ])))
        if messages != []:
            if messages[-1].__len__() + '\n\n'.__len__() + formattedEvent.__len__() < 1500:
                messages[-1] += '\n\n' + formattedEvent
            else:
                messages.append(formattedEvent)
        else:
            messages.append(formattedEvent)
    return messages

def formatSingleEvent(event):
    embeded_description = f'''**Data**: {event["starting_datetime"].strftime("%d/%m/%Y") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") 
                                            else f"{event['starting_datetime'].strftime('%d')} a {event['ending_datetime'].strftime('%d/%m/%Y')}"}{" - das "+event["starting_datetime"].strftime("%H:%M")+" às "+event["ending_datetime"].strftime("%H:%M") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") else ''}
**Local**: {event["city"]}, {event["state_abbrev"]}
**Endereço**: {event["address"]}'''
    if event['group_chat_link']!=None: embeded_description += f"""
**Chat do evento**: <{event['group_chat_link']}>"""
    if event['website']!=None: embeded_description += f"""
**Site**: <{event['website']}>""" 
    embeded_description += f"""
**Preço**: {"Ingressos esgotados" if event['out_of_tickets']
else "Vendas encerradas" if event['sales_ended']
else "De R$"+str(f"{event['price']:.0f}").replace('.',',')+" a "+"R${:,.0f}".format(event['max_price']).replace(",", "x").replace(".", ",").replace("x", ".") if (event['price']!=0 and event['max_price']!=0) 
else f'R$'+str(f"{event['price']:.0f}").replace('.',',') if (event['max_price']==0 or event['max_price']==event['price']) and event['price']!=0 else 'Gratuito'}"""
    if event['description']!=None: embeded_description += f"""

{event['description']}
"""
    eventEmbeded = discord.Embed(
        color=discord.Color.blue(),
        title=event["event_name"].title(),
        description=embeded_description
    )
    if event["logo_url"]!=None:
        eventEmbeded.set_thumbnail(url=event["logo_url"])
    else: eventEmbeded.set_author(name='')
    return eventEmbeded

async def removeTempRoles(bot):
    mydbAndCursor = startConnection()
    expiringTempRoles = getExpiringTempRoles(mydbAndCursor[0], DISCORD_GUILD_ID)
    for TempRole in expiringTempRoles:
        guild = bot.get_guild(DISCORD_GUILD_ID)
        member = guild.get_member(TempRole['user_id'])
        role = guild.get_role(TempRole['role_id'])
        print(f'{member.name} perdeu o cargo {role.name}')
        pass
        if member != None and role != None:
            await member.remove_roles(role)
            deleteTempRole(mydbAndCursor[1], TempRole['id'])
    endConnectionWithCommit(mydbAndCursor)
    return

async def mentionArtRoles(bot, message:discord.Message):
    guild = bot.get_guild(DISCORD_GUILD_ID)
    if (message.author.roles.__contains__(guild.get_role(835120204270534707))
        and message.channel.type == discord.ChannelType.public_thread
        and message.channel.parent.id == 1210574829107945513
        and message.channel.owner == message.author
        ):
        availableMentions = ['#YCH', '#Rifa', '#Sorteio', '#Adopt']
        mentionableRoles = [1217107416701997147,1217109127482834965,1217109253647503411,1217112597565014128]
        rolesDict = dict(zip(availableMentions, mentionableRoles))
        answer = ''
        for mention in availableMentions:
            if message.content.lower().__contains__(mention.lower()):
                role = guild.get_role(rolesDict[mention])
                answer += f'{role.mention} '
        if answer != '':
            await asyncio.sleep(2)
            return await message.channel.send(answer, delete_after=5)
        

async def secureArtPosts(message:discord.Message):
    if (message.channel.type == discord.ChannelType.public_thread
        and message.channel.parent.id == 1210574829107945513
        and message.channel.owner != message.author
        ):
        await message.delete()
        await message.author.send('Você não tem permissão para enviar mensagens no post de outro artista!')
    return