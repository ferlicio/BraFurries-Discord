import discord

def checkRolesUpdate(before:discord.member.Member, after:discord.member.Member):
    if before.roles != after.roles:
        todosCargos = before.roles + after.roles
        #vamos remover os cargos repetidos e @everyone
        todosCargos = list(dict.fromkeys(todosCargos))
        todosCargos.remove(after.guild.default_role)
        cargosAlterados = {'adicionados': [], 'removidos': []}
        #agora vamos percorrer a lista de cargos e ver quais foram adicionados e quais foram removidos
        for cargo in todosCargos:
            if not before.roles.__contains__(cargo):
                cargosAlterados['adicionados'].append(cargo)
            if not after.roles.__contains__(cargo):
                cargosAlterados['removidos'].append(cargo)
        ##print(f'Os cargos alterados foram: {cargosAlterados}')
        return cargosAlterados
    else:
        return False


