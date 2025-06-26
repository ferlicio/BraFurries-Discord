from core.database import connectToDatabase, assignTempRole, endConnectionWithCommit
from discord import Interaction, Member, Role, commands
from datetime import timedelta, datetime
from core.common.timeFunctions import now
import discord
import re

def setup(bot: commands.Bot):
    @bot.tree.command(name=f'relatorio-portaria', description=f'Gera um relatório de atividades na portaria')
    async def portariaReport(ctx: discord.Interaction, periodo:Literal['semana', 'mês']):
        if periodo == 'semana':
            InitialDate = now() - timedelta(days=7)
        elif periodo == 'mês':
            InitialDate = now() - timedelta(days=30)
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
            async for message in channel.history(limit=None, after=InitialDate, before=now()):
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
        memberProfile = getUserInfo(member, ctx.guild.id)
        profileDescription = generateUserDescription(memberProfile)
        embedUserProfile = discord.Embed(
            color=discord.Color.from_str('#febf10'),
            title='{0} - ID {1:64}'.format(member.name, str(member.id)), 
            description=profileDescription)
        embedUserProfile.set_thumbnail(url=member.avatar.url)
        embedUserProfile.set_author(
            name=(member.display_name)+f' (level {memberProfile.level})', 
            icon_url=member.guild_avatar.url if member.guild_avatar != None else member.avatar.url)
        embedUserProfile.set_footer(text=f'{memberProfile.warnings.__len__()} Warns{"  -  Ultimo warn em "+now().strftime("%d/%m/%Y") if memberProfile.warnings.__len__() > 0 else f""}{"  -  >> DE CASTIGO <<" if member.is_timed_out() else ""}')
        await ctx.followup.send(embed=embedUserProfile)


    @bot.tree.command(name=f'registrar_usuario', description=f'Registra um membro')
    async def registerUser(ctx: discord.Interaction, member: discord.Member, data_aprovacao:str, aniversario:str):
        data_aprovacao = verifyDate(data_aprovacao)
        aniversario = verifyDate(aniversario)
        await ctx.response.send_message(content='Registrando usuário...',ephemeral=True)
        if not data_aprovacao: return await ctx.edit_original_response(content='Data de aprovação no formato errado! use o formato dd/MM/YYYY')
        if not aniversario: return await ctx.edit_original_response(content='Data de aniversário no formato errado! use o formato dd/MM/YYYY')
        registered = registerUser(ctx.guild.id, member, aniversario, data_aprovacao)
        if registered:
            return await ctx.edit_original_response(content='Membro registrado com sucesso!')
        else: 
            return await ctx.edit_original_response(content='Não foi possível registrar o usuário')
        
        
    @bot.tree.command(name=f'liberar_acesso_nsfw', description=f'Libera o acesso NSFW para o membro')
    async def grantNSFWAccess(ctx: discord.Interaction, member: discord.Member, data_aniversario:str):
        data_aniversario = verifyDate(data_aniversario)
        if data_aniversario == False:
            return await ctx.response.send_message(content='Data de aniversário inválida! use o formato dd/MM/YYYY', ephemeral=True)
        if (now().date() - data_aniversario).days < 18*365:
            return await ctx.response.send_message(content='O membro não tem 18 anos ainda! não pode acessar conteúdo NSFW', ephemeral=True)
        await ctx.response.send_message(content='Processando...', ephemeral=True)
        approved = grantNSFWAccess(ctx.guild.id, member, data_aniversario)
        if (discord.utils.get(ctx.guild.roles, id=DISCORD_NSFW_ROLE) in member.roles):
            return await ctx.edit_original_response(content='O membro já tem acesso NSFW!')
        if approved == True:
            await member.add_roles(discord.utils.get(ctx.guild.roles, id=DISCORD_NSFW_ROLE))
            return await ctx.edit_original_response(content='Acesso liberado com sucesso!')
        elif approved == 'not_registered':
            return await ctx.edit_original_response(content=f'''O membro não está registrado no sistema! 
    Use o comando /registrar_usuario para registrar o membro e tente novamente''')
        elif approved == 'dont_match':
            return await ctx.edit_original_response(content=f'''A data de aniversário informada não corresponde ao registro!''')
        else:
            return await ctx.edit_original_response(content='Ocorreu um erro ao aprovar o membro')


    """@bot.tree.command(name=f'adm-banir', description=f'Bane um membro do servidor')"""



    @bot.tree.command(name=f'warn', description=f'Aplica um warn em um membro')
    async def warn(ctx: discord.Interaction, membro: discord.Member, motivo: str):
        mydb = connectToDatabase()
        #staffRoles = getStaffRoles(ctx.guild)
        await ctx.response.send_message("Registrando warn...")
        if True: #adicionar verificação de cargo de staff
            warnings = warnMember(mydb, ctx.guild.id, membro, motivo)
            endConnectionWithCommit(mydb)
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
        endConnection(mydb)
        return await ctx.response.send_message(content='Você não tem permissão para fazer isso', ephemeral=True)

    @bot.tree.command(name=f'warnings', description=f'Mostra os warnings de um membro')
    async def showWarnings(ctx: discord.Interaction, member: discord.Member):
        warnings = getMemberWarnings(ctx.guild.id, member)
        if warnings:
            warningsList = '\n'.join([f'**{warn.date.strftime("%d/%m/%Y")}** - {warn.reason}' for warn in warnings])
            return await ctx.response.send_message(content=f'Warnings do membro {member.mention}:\n{warningsList}')
        return await ctx.response.send_message(content=f'O membro {member.mention} não possui warnings')


    @bot.tree.command(name=f'portaria_cargos', description=f'Permite que um membro na portaria pegue seus cargos')
    async def portariaCargos(ctx: discord.Interaction, member: discord.Member):
        portariaCategory = discord.utils.get(ctx.guild.categories, id=753342674576211999)
        provisoriaCategory = discord.utils.get(ctx.guild.categories, id=1178531112042111016)
        carteirinhaDeCargos = ctx.guild.get_role(860492272054829077)
        for channel in portariaCategory.channels+provisoriaCategory.channels:
            if channel.permissions_for(member).send_messages:
                if (now().date() - member.created_at.date()).days < 30 and not channel.name.__contains__("provisória"):
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

        channels = portariaCategory.channels + provisoriaCategory.channels
        channel = next((c for c in channels if c.permissions_for(member).send_messages), None)
        if not channel:
            return await ctx.response.send_message(content=f'O membro <@{member.id}> não está na portaria', ephemeral=True)

        if (cargoVisitante in member.roles and carteirinhaProvisoria in member.roles) or (cargoVisitante not in member.roles):
            return await ctx.response.send_message(content=f'O membro <@{member.id}> ja foi aprovado!', ephemeral=True)

        if (now().date() - member.created_at.date()).days < 30:
            await ctx.response.send_message(content=f'Atribuindo carteirinha provisória...', ephemeral=True)
            await member.add_roles(carteirinhaProvisoria, cargoVisitante)
            await member.remove_roles(carteirinhaCargos)
            expiration_date = now() + timedelta(days=15)
            await ctx.edit_original_response(content=f'O membro <@{member.id}> entrará no servidor com **carteirinha provisória** e terá acesso restrito ao servidor por sua conta ter **menos de 30 dias**. \nLembre de avisar o membro sobre isso')
            with pooled_connection() as cursor:
                assignTempRole(cursor.connection, ctx.guild_id, member, carteirinhaProvisoria.id, expiration_date, 'Carteirinha provisória')
            await channel.edit(name=f'{channel.name}-provisória' if 'provisória' not in channel.name else channel.name, category=provisoriaCategory)
            return

        async for message in channel.history(limit=1, oldest_first=True):
            if data_nascimento:
                matchEmbedded = BIRTHDAY_REGEX.search(data_nascimento)
                if not matchEmbedded:
                    return await ctx.response.send_message(content=f'Você digitou uma data inválida: {data_nascimento}', ephemeral=True)
            else:
                matchEmbedded = None
                if len(message.embeds) > 1 and isinstance(message.embeds[1].description, str):
                    matchEmbedded = BIRTHDAY_REGEX.search(message.embeds[1].description)

            if matchEmbedded:
                await ctx.response.send_message(content='registrando usuario...', ephemeral=True)
                try:
                    day = int(matchEmbedded.group(1))
                    month = int(matchEmbedded.group(2) if matchEmbedded.group(2).isdigit() else MONTHS.index(matchEmbedded.group(2)))
                    year = int(matchEmbedded.group(3))
                    if len(str(year)) <= 2:
                        year += 2000 if year < (now().date().year - 2000) else 1900
                    birthday = datetime(year, month, day)
                    if birthday.year > 1975 and birthday.year < now().year:
                        age = (datetime.now().date() - birthday.date()).days
                        if not (cargoMaior18 in member.roles or cargoMenor18 in member.roles) and age >= 4745:
                            return await ctx.edit_original_response(content=f'O membro <@{member.id}> ainda não pegou seus cargos!' if carteirinhaCargos in member.roles else f'O membro <@{member.id}> ainda não tem a carteirinha de cargos, use o comando "/portaria_cargos" antes')
                        registerUser(ctx.guild.id, member, birthday.date(), now().date())
                        eighteen_years_in_days = 6570
                        thirteen_years_in_days = 4745
                        if age >= eighteen_years_in_days:  # 18+ anos
                            await member.add_roles(cargoMaior18)
                            await member.remove_roles(cargoMenor18, cargoMenor13)
                        elif age >= thirteen_years_in_days:  # 13+ anos
                            await member.add_roles(cargoMenor18)
                            await member.remove_roles(cargoMaior18, cargoMenor13)
                        else:
                            await member.remove_roles(cargoMaior18, cargoMenor18)
                            await member.add_roles(carteirinhaProvisoria, cargoVisitante, cargoMenor13)
                            await channel.edit(name=f'{channel.name}-provisória' if not channel.name.__contains__('provisória') else channel.name, category=provisoriaCategory)
                            return await ctx.edit_original_response(content=f'Por ser menor de 13 anos, o membro <@{member.id}> entrará no servidor com carteirinha provisória e terá acesso restrito ao servidor. Lembre de avisar o membro sobre isso.')
                        await member.remove_roles(carteirinhaCargos, cargoVisitante)
                        await channel.edit(name=f'{channel.name}-✅' if '-✅' not in channel.name else channel.name)
                        return await ctx.edit_original_response(content=f'O membro <@{member.id}> foi aprovado com sucesso!\nLembre de dar boas vindas a ele no <#753348623844114452> :3')
                    else:
                        return await ctx.edit_original_response(content=f'Data inválida encontrada: {matchEmbedded.group(0)}\nO membro tem {relativedelta(now().date(), birthday.date()).years} anos?')
                except ValueError:
                    return await ctx.edit_original_response(content=f'Data inválida encontrada: {matchEmbedded.group(0)}')
                except Exception as e:
                    return await ctx.edit_original_response(content=f'Erro ao registrar o membro: {e}')
        return await ctx.response.send_message(content=f'Não foi possível encontrar a data de nascimento do membro <@{member.id}> na portaria\nEm ultimo caso, digite a data de nascimento nos argumentos do comando.', ephemeral=True)