from database.database import *
from settings import *
import discord
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

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

        color_distance = delta_e_cie2000(color1_lab, color2_lab)  # Aqui está a mudança

        if color_distance < 11.0:
            return False
    return True
    