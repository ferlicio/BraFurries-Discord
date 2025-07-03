from discord.ext import commands
import discord
import os
from discord import app_commands
from datetime import datetime
from core.database import connectToDatabase, endConnectionWithCommit, endConnection
from core.database import includeEvent, getAllEvents, getEventsByState, getAllPendingApprovalEvents, approveEventById
from core.database import admConnectTelegramAccount, getEventByName, scheduleNextEventDate, rescheduleEventDate
from core.routine_functions import formatSingleEvent, formatEventList
from core.verifications import localeIsAvailable


class EventCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    async def addEvent(self, ctx: discord.Interaction, user, state: str, city: str, event_name: str, address: str, price: float, starting_date: str, starting_time: str, ending_date: str, ending_time: str, description: str = None, group_link: str = None, site: str = None, max_price: float = None, event_logo_url: str = None):
        try:
            datetime.strptime(starting_date, "%d/%m/%Y")
            if ending_date is None:
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
            return await ctx.response.send_message(content='''A data e hora de início do evento não pode ser maior que a data e hora de encerramento!''', ephemeral=True)
        mydb = connectToDatabase()
        locale_id = await localeIsAvailable(ctx, mydb, state)
        if locale_id:
            await ctx.response.defer()
            result = includeEvent(mydb, user, locale_id, city, event_name, address, price, starting_datetime, ending_datetime, description, group_link, site, max_price, event_logo_url)
            endConnectionWithCommit(mydb)
            if result:
                return await ctx.followup.send(content=f'O evento **{event_name}** foi registrado com sucesso!', ephemeral=False)

    @app_commands.command(name='novo_evento', description='Adiciona um evento ao calendário')
    async def addEventWithDiscordUser(self, ctx: discord.Interaction, user: discord.Member, estado: str, cidade: str, event_name: str, address: str, price: float, starting_date: str, starting_time: str, ending_date: str, ending_time: str, description: str = None, group_link: str = None, site: str = None, max_price: float = None, event_logo_url: str = None):
        await EventCog.addEvent(self, ctx, user, estado, cidade, event_name, address, price, starting_date, starting_time, ending_date, ending_time, description, group_link, site, max_price, event_logo_url)

    @app_commands.command(name='novo_evento_por_usuario', description='Adiciona um evento ao calendário usando um usuário do telegram')
    async def addEventWithTelegramUser(self, ctx: discord.Interaction, telegram_username: str, estado: str, cidade: str, event_name: str, address: str, price: float, starting_date: str, starting_time: str, ending_date: str, ending_time: str, description: str = None, group_link: str = None, site: str = None, max_price: float = None, event_logo_url: str = None):
        await EventCog.addEvent(self, ctx, telegram_username, estado, cidade, event_name, address, price, starting_date, starting_time, ending_date, ending_time, description, group_link, site, max_price, event_logo_url)

    @app_commands.command(name='eventos', description='Lista todos os eventos registrados')
    async def listEvents(self, ctx: discord.Interaction):
        await ctx.response.defer()
        result = getAllEvents()
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
            eventsResponse[-1] += f'''\n\n```Se você quiser ver mais detalhes sobre um evento, use o comando "/evento <nome do evento>"```\nAdicione tambem a nossa agenda de eventos ao seu google agenda e tenha todos os eventos na palma da sua mão! {os.getenv('GOOGLE_CALENDAR_LINK')}'''
            for message in eventsResponse:
                await ctx.followup.send(content=message) if message != eventsResponse[-1] else await ctx.channel.send(content=message)
        else:
            return await ctx.followup.send(content=f'Não há eventos registrados... que tal ser o primeiro? :3')

    @app_commands.command(name='eventos_por_estado', description='Lista todos os eventos registrados em um estado')
    async def listEventsByState(self, ctx: discord.Interaction, state: str):
        mydb = connectToDatabase()
        await ctx.response.defer()
        locale_id = await localeIsAvailable(ctx, mydb, state)
        result = getEventsByState(locale_id)
        endConnection(mydb)
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
            eventsResponse[-1] += f'''\n\n```Se você quiser ver mais detalhes sobre um evento, use o comando "/evento <nome do evento>"```\nAdicione tambem a nossa agenda de eventos ao seu google agenda e tenha todos os eventos na palma da sua mão! {os.getenv('GOOGLE_CALENDAR_LINK')}'''
            for message in eventsResponse:
                await ctx.followup.send(content=message) if message != eventsResponse[-1] else await ctx.channel.send(content=message)
        else:
            return await ctx.followup.send(content=f'Não há eventos registrados em {state}... que tal ser o primeiro? :3')

    @app_commands.command(name=f'evento', description=f'Mostra os detalhes de um evento')
    async def showEvent(self, ctx: discord.Interaction, event_name: str):
        if event_name.__len__() < 4:
            return await ctx.response.send_message(content='''Nome do evento inválido! você informou um nome com menos de 4 caracteres? <:catsip:851024825333186560>''', ephemeral=True)
        await ctx.response.defer()
        event = getEventByName(event_name)
        if event:
            eventEmbeded = formatSingleEvent(event)
            return await ctx.followup.send(embed=eventEmbeded)
        else:
            return await ctx.followup.send(content=f'Não há eventos registrados com esse nome. Tem certeza que digitou o nome certo?')

    @app_commands.command(name=f'evento_reagendar', description=f'Reagenda um evento pendente')
    async def rescheduleEvent(self, ctx: discord.Interaction, event_name: str, new_date: str):
        try: new_date = datetime.strptime(new_date, "%d/%m/%Y")
        except ValueError:
            return await ctx.response.send_message(content='''Data inválida! você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
        await ctx.response.defer()
        result = rescheduleEventDate(event_name, new_date, ctx.user.name)
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


    @app_commands.command(name='evento_agendar_prox', description='Agenda no calendario a próxima data do evento')
    async def scheduleNextEvent(self, ctx: discord.Interaction, nome_do_evento: str, data: str):
        try:
            data = datetime.strptime(data, "%d/%m/%Y")
        except ValueError:
            return await ctx.response.send_message(content='''Data inválida! Você informou uma data no formato "dd/mm/aaaa"? <:catsip:851024825333186560>''', ephemeral=True)
        await ctx.response.defer()
        result = scheduleNextEventDate(nome_do_evento, data, ctx.user.name)
        if result == True:
            return await ctx.followup.send(content=f'O evento **{nome_do_evento}** foi agendado com sucesso!')
        elif result == "não encontrado":
            return await ctx.followup.send(content=f'Não foi possível encontrar um evento com esse nome! tem certeza que digitou o nome certo?')
        elif result == "não encerrado":
            return await ctx.followup.send(content=f'Não é possível agendar um evento que ainda não foi encerrado')
        elif result == "não é o dono":
            return await ctx.followup.send(content=f'Você não é o dono desse evento! apenas o dono pode agendar o evento')

    @app_commands.command(name='eventos_pendentes', description='Mostra os eventos esperando aprovação')
    async def showPendingEvents(self, ctx: discord.Interaction):
        await ctx.response.defer()
        result = getAllPendingApprovalEvents()
        if result:
            eventsResponse = '\n\n'.join(
                f'''> # {event["event_name"].title()} (id - {event["id"]})\n    **Data**: {event["starting_datetime"].strftime("%d/%m/%Y") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") else f"{event['starting_datetime'].strftime('%d')} a {event['ending_datetime'].strftime('%d/%m/%Y')}"}{" - das "+event["starting_datetime"].strftime("%H:%M")+" às "+event["ending_datetime"].strftime("%H:%M") if event["starting_datetime"] == event["ending_datetime"] else ''}\n    **Local**: {event["city"]}, {event["state_abbrev"]}\n    **Endereço**: {event["address"]} ''' + '\n'+\
                '\n'.join(filter(None, [
                    f">    **Chat do evento**: <{event['group_chat_link']}>" if event['group_chat_link']!=None else '',
                    f">    **Site**: <{event['website']}>" if event['website']!=None else '',
                    f'''>    **Preço**: {"A partir de R$"+str(f"{event['price']:.2f}").replace('.',',') if event['price']!=0 else 'Gratuito'}'''
                ]))
                for event in sorted(result, key=lambda event: event["starting_datetime"])
            )
            await ctx.followup.send(content=f'''Aqui estão os eventos registrados esperando aprovação:\n{eventsResponse}\n```Se você quiser aprovar um evento, use o comando "/evento_aprovar <id do evento>"```''')
        else:
            return await ctx.followup.send(content=f'Não há eventos a serem aprovados... talvez seja a hora de buscar novos eventos!')

    @app_commands.command(name='evento_aprovar', description='Aprova um evento pendente')
    async def approveEvent(self, ctx: discord.Interaction, event_id: int):
        if ctx.user.id != 167436511787220992:
            return await ctx.response.send_message(content='Você não tem permissão para fazer isso', ephemeral=True)
        await ctx.response.defer()
        result = approveEventById(event_id)
        if result == True:
            return await ctx.followup.send(content=f'O evento foi aprovado com sucesso!')
        elif result == "não encontrado":
            return await ctx.followup.send(content=f'Não foi possível encontrar um evento pendente com esse id! tem certeza que digitou o id certo?')
        elif result == False:
            return await ctx.followup.send(content=f'Não foi possível aprovar o evento')

    @app_commands.command(name='evento_add_staff', description='Adiciona um membro da staff como organizador de um evento')
    async def addStaffToEvent(self, ctx: discord.Interaction, event_id: int, staff: discord.Member):
        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(EventCog(bot))