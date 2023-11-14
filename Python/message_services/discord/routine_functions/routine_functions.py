from settings import *
import discord

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