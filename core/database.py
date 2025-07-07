from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schemas.models.user import User, CustomRole, Warning
from schemas.enums.server_messages import ServerMessagesEnum
from schemas.models.user import SimpleUserBirthday
from mysql.connector.cursor import MySQLCursorAbstract
from mysql.connector import pooling
import mysql.connector
from datetime import date, datetime
from typing import Union
import discord
import os.path
import dotenv
from contextlib import contextmanager

dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

SCOPES = ['https://www.googleapis.com/auth/calendar']

db_config = {
    "host": os.getenv("BOT_DATABASE_HOST"),
    "user": os.getenv("BOT_DATABASE_USER"),
    "password": os.getenv("BOT_DATABASE_PASSWORD"),
    "database": "coddy",
}

def getCredentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds
    
connection_pool = pooling.MySQLConnectionPool(
    pool_name="Discord", pool_size=5, **db_config
)

@contextmanager
def pooled_connection(buffered: bool = False):
    connection = connection_pool.get_connection()
    cursor: MySQLCursorAbstract = connection.cursor(dictionary=True, buffered=buffered)
    try:
        yield cursor
    except Exception as e:
        connection.rollback()
        raise e
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def getConfig(guild:discord.Guild):
    with pooled_connection() as cursor:
        #verifica se a comunidade já está no banco de dados
        query = f"""SELECT * FROM communities"""
        cursor.execute(query)
        communities = cursor.fetchall()
        if communities == []:
            botOriginalGuildName = discord.utils.get(guild.client.guilds, id=int(os.getenv('BOT_GUILD_ID'))).name
            query = f"""INSERT IGNORE INTO communities (name)
    VALUES ('{botOriginalGuildName}');"""
            cursor.execute(query)
            query = f"""INSERT IGNORE INTO discord_servers (community_id, name, guild_id)
    VALUES ('{cursor.lastrowid}', '{guild.name}', '{guild.id}');"""
            cursor.execute(query)
        else:
            existInCommunities = False
            for community in communities:
                if community["name"] in guild.name:
                    existInCommunities = True
                    query = f"""INSERT IGNORE INTO discord_servers (community_id, name, guild_id) 
                VALUES ('{community['id']}', '{guild.name}', '{guild.id}');"""
                cursor.execute(query)
                continue
            if not existInCommunities:
                query = f"""INSERT IGNORE INTO communities (name)
    VALUES ('{guild.name}');""" 
                cursor.execute(query)
                query = f"""SELECT * FROM communities"""
                cursor.execute(query)
                community = cursor.fetchall()
                query = f"""INSERT IGNORE INTO discord_servers (community_id, name, guild_id)
    VALUES ('{community[-1]["id"]}', '{guild.name}', '{guild.id}');"""
                cursor.execute(query)
        query = f"""INSERT IGNORE INTO server_settings (server_guild_id) 
    VALUES ('{guild.id}');"""
        cursor.execute(query)
        
        # Recupera as configurações do servidor
        query = f"""SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'server_settings';"""
        cursor.execute(query)
        todas_colunas = cursor.fetchall()

        dynamic_query = f"""SELECT discord_servers.name, discord_servers.guild_id AS guildId"""
        for column in todas_colunas:
            if column != 'server_guild_id' and column != 'id':
                dynamic_query += f", server_settings.{column}"

        dynamic_query += f"""
    FROM discord_servers
    LEFT JOIN server_settings ON discord_servers.guild_id = server_settings.server_guild_id
    WHERE discord_servers.guild_id = '{guild.id}'"""

        cursor.execute(dynamic_query)
        config = cursor.fetchone()

        return config

def getLevelConfig():
    with pooled_connection() as cursor:
        query = f"""SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'level_config';"""
    

def hasGPTEnabled(guild:discord.Guild):
    with pooled_connection() as cursor:
        query = f"""
        SELECT  has_gpt_enabled AS enabled, 
                gpt_model AS model
        FROM server_settings
        WHERE server_guild_id = '{guild.id}';"""
        cursor.execute(query)
        return cursor.fetchone()

def CreateGCalendarDescription(price:float, max_price:float, group_link:str, website:str):
    CalendarDescription = None
    formatted_price = "{:,.2f}".format(price).replace(",", "x").replace(".", ",").replace("x", ".")
    if max_price != None and max_price != 'None' and max_price != 0:
        formatted_max_price = "{:,.2f}".format(max_price).replace(",", "x").replace(".", ",").replace("x", ".")
    if price > 0:
        CalendarDescription = f"""<strong>>> Evento Pago <<</strong>"""
    else:
        CalendarDescription = f"""<strong>>> Evento Gratuito <<</strong>"""
    if max_price != None and max_price != 'None' and max_price != 0:
        CalendarDescription += f"""

<strong>Preço:</strong>
R${formatted_price} a R${formatted_max_price}"""
    elif price > 0:
        CalendarDescription += f"""

<strong>Preço:</strong>
R${formatted_price}"""+(" a R$"+formatted_max_price if max_price != None else '')
    if group_link != None and group_link != 'None':
        CalendarDescription += f"""

<strong>Chat do Evento:</strong>
<a href="{group_link}">{group_link}</a>"""
    if website != None and website != 'None':
        CalendarDescription += f"""

<strong>Site:</strong>
<a href="{website}">{website}</a>"""
    return CalendarDescription



def getAllLocals():
    with pooled_connection() as cursor:
        query = f"""SELECT * FROM locale"""
        cursor.execute(query)
        return cursor.fetchall()


def getUserId(discord_user_id: int):
    """Fetch the internal user id for a Discord member."""
    with pooled_connection() as cursor:
        cursor.execute(
            "SELECT user_id FROM discord_user WHERE discord_user_id = %s",
            (discord_user_id,)
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None




def includeUser(user: Union[discord.Member, str], guildId: int = os.getenv("DISCORD_GUILD_ID"), approvedAt: datetime = None) -> int:
    """Ensure a user exists in the database and return the internal id."""
    with pooled_connection(True) as cursor:
        if isinstance(user, discord.Member):
            username = user.name
            display_name = user.display_name
            member_since = user.joined_at.strftime("%Y-%m-%d %H:%M:%S")
            approved = 0 if discord.utils.get(user.guild.roles, id=860453882323927060) in user.roles else 1
            cursor.execute(
                "SELECT user_id, display_name FROM discord_user WHERE discord_user_id = %s",
                (user.id,),
            )
            result = cursor.fetchone()
        else:
            username = user
            display_name = user
            member_since = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            approved = 0
            cursor.execute(
                "SELECT user_id, display_name FROM telegram_user WHERE username = %s",
                (user,),
            )
            result = cursor.fetchone()

        approved_at_str = approvedAt.strftime("%Y-%m-%d %H:%M:%S") if approvedAt else None

        if result:
            user_id = result["user_id"]

            if result["display_name"] != display_name:
                table = "discord_user" if isinstance(user, discord.Member) else "telegram_user"
                cursor.execute(
                    f"UPDATE {table} SET display_name = %s WHERE user_id = %s",
                    (display_name, user_id),
                )
            cursor.execute("SELECT display_name FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row and row["display_name"] != display_name:
                cursor.execute("UPDATE users SET display_name = %s WHERE id = %s", (display_name, user_id))

            cursor.execute(
                "SELECT approved_at FROM user_community_status WHERE user_id = %s",
                (user_id,),
            )
            status = cursor.fetchone()
            if status:
                if status["approved_at"] is None and approved_at_str:
                    cursor.execute(
                        "UPDATE user_community_status SET approved_at = %s, approved = 1 WHERE user_id = %s",
                        (approved_at_str, user_id),
                    )
            else:
                cursor.execute(
                    "SELECT community_id FROM discord_servers WHERE guild_id = %s",
                    (guildId,),
                )
                community_id = cursor.fetchone()["community_id"]
                cursor.execute(
                    "INSERT INTO user_community_status (user_id, community_id, member_since, approved, approved_at, is_vip, banned)"
                    " VALUES (%s, %s, %s, %s, %s, 0, 0)",
                    (user_id, community_id, member_since, approved, approved_at_str),
                )

            return user_id

        # User not found: create
        try:
            cursor.execute(
                "INSERT INTO users (display_name, username) VALUES (%s, %s)",
                (display_name, username),
            )
        except Exception as e:
            raise Exception(
                "Nome de usuário inválido. Não é possivel aprovar membros com caracteres especiais."
            ) from e

        user_id = cursor.lastrowid
        if not user_id:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()["id"]

        cursor.execute(
            "SELECT community_id FROM discord_servers WHERE guild_id = %s",
            (guildId,),
        )
        community_id = cursor.fetchone()["community_id"]
        cursor.execute(
            "INSERT INTO user_community_status (user_id, community_id, member_since, approved, approved_at, is_vip, banned)"
            " VALUES (%s, %s, %s, %s, %s, false, false)",
            (user_id, community_id, member_since, approved, approved_at_str),
        )

        try:
            if isinstance(user, discord.Member):
                cursor.execute(
                    "INSERT INTO discord_user (user_id, discord_user_id, username, display_name) VALUES (%s, %s, %s, %s)",
                    (user_id, user.id, username, user.nick),
                )
            else:
                cursor.execute(
                    "INSERT IGNORE INTO telegram_user (user_id, username, display_name) VALUES (%s, %s, %s)",
                    (user_id, user, username),
                )
        except Exception as e:
            raise Exception(
                "Nome de usuário inválido. Não é possivel aprovar membros com caracteres especiais."
            ) from e

        return user_id

def includeLocale(guildId: int, abbrev:str, user:discord.User, availableLocals:list):
    user_id = includeUser(user, guildId)
    with pooled_connection() as cursor:
        for local in availableLocals:
            if local['locale_abbrev'] == abbrev:
                try:
                    query = f"""INSERT INTO user_locale (user_id, locale_id) VALUES ('{user_id}','{local['id']}');"""
                    cursor.execute(query)
                    return True
                except:
                    return False

def getUsersByLocale(abbrev:str, availableLocals:list):
    with pooled_connection() as cursor:
        for local in availableLocals:
            if local['locale_abbrev'] == abbrev:
                query = f"""
                SELECT users.username
                FROM users
                JOIN user_locale ON users.id = user_locale.user_id
                JOIN locale ON user_locale.locale_id = locale.id
                WHERE locale.locale_abbrev = '{abbrev}';"""
                cursor.execute(query)
                return cursor.fetchall()
        
def includeBirthday(guildId: int, date:date, user:discord.User, mentionable:bool, userId:int=None, registered:bool=False):
    if userId != None:
        user_id = userId
    else:
        user_id = includeUser(user, guildId)
    with pooled_connection() as cursor:
        query = f"""SELECT birth_date, mentionable, registered FROM user_birthday WHERE user_id = '{user_id}'"""
        cursor.execute(query)
        birthday = cursor.fetchone()
        birthday = {'date': birthday[0], 'mentionable': birthday[1], 'registered': birthday[2]} if birthday != None else None
        if birthday:
            if birthday['registered'] == 0 or birthday['mentionable'] != mentionable:
                query = f"""SELECT approved_at FROM user_community_status WHERE user_id = '{user_id}';"""
                cursor.execute(query)
                approved_at = cursor.fetchone()
                approved_at = datetime.strptime(f"{approved_at[0]}", '%Y-%m-%d %H:%M:%S')
                query = f"""UPDATE user_birthday
    SET mentionable = {mentionable}, registered = 1{f", verified = 1" if (datetime.now() - approved_at).days > 40 and date == birthday['date'] else ''}
    WHERE user_id = '{user_id}';"""
                cursor.execute(query)
                if birthday['registered'] == 1:
                    raise Exception('Changed Entry')
                return True
            else:
                if birthday['registered'] == 1:
                    raise Exception('Duplicate entry')
        else:
            try:
                query = f"""INSERT INTO user_birthday (user_id, birth_date, verified, mentionable, registered) VALUES ('{user_id}','{date}',FALSE,{mentionable},{registered});"""
                cursor.execute(query)
                return True
            except:
                return False

def getAllBirthdays():
    with pooled_connection() as cursor:
        query = f"""SELECT discord_user.discord_user_id, user_birthday.birth_date
    FROM discord_user
    JOIN user_birthday ON discord_user.user_id = user_birthday.user_id
    WHERE user_birthday.mentionable = 1;"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        #convertendo para uma lista de dicionários
        myresult = [{'user_id': i["discord_user_id"], 'birth_date': i["birth_date"]} for i in myresult]
        return myresult

def getUserInfo(user: discord.Member, guildId: int, userId: int = None, create_if_missing: bool = True) -> User :
    """Retrieve a user from the database. Optionally registers the user if missing."""
    user_id = includeUser(user, guildId)

    with pooled_connection() as cursor:
        query = (
            "SELECT discord_user.discord_user_id, discord_user.display_name, "
            "user_community_status.member_since, user_community_status.approved, "
            "user_community_status.approved_at, user_community_status.is_vip, "
            "user_community_status.is_partner, user_level.current_level, "
            "user_birthday.birth_date, user_birthday.verified, locale.locale_name, "
            "user_economy.bank_balance "
            "FROM users "
            "LEFT JOIN discord_user ON users.id = discord_user.user_id "
            "LEFT JOIN user_community_status ON users.id = user_community_status.user_id "
            "LEFT JOIN user_birthday ON user_birthday.user_id = users.id "
            "LEFT JOIN user_level ON user_level.user_id = users.id AND user_level.server_guild_id = %s "
            "LEFT JOIN user_locale ON user_locale.user_id = users.id "
            "LEFT JOIN locale ON locale.id = user_locale.locale_id "
            "LEFT JOIN warnings ON warnings.user_id = users.id "
            "LEFT JOIN user_economy ON user_economy.user_id = users.id AND user_economy.server_guild_id = %s "
            "WHERE discord_user.user_id = %s"
        )
        cursor.execute(query, (guildId, guildId, user_id))
        dbUser = cursor.fetchone()
        if not dbUser:
            return None

        userToReturn = User(
            id=user_id,
            discordId=dbUser["discord_user_id"],
            username=user.name,
            displayName=user.display_name,
            memberSince=dbUser["member_since"],
            approved=dbUser["approved"],
            approvedAt=dbUser["approved_at"],
            isVip=dbUser["is_vip"],
            isPartner=dbUser["is_partner"],
            level=dbUser["current_level"],
            birthday=dbUser["birth_date"],
            birthdayVerified=dbUser["verified"],
            locale=dbUser["locale_name"],
            coins=dbUser["bank_balance"],
            warnings=[],
            inventory=[],
            staffOf=[],
        )

        cursor.execute(
            "SELECT warnings.date, warnings.reason, warnings.expired "
            "FROM warnings JOIN users ON warnings.user_id = users.id "
            "WHERE users.id = %s",
            (user_id,),
        )
        warnings = cursor.fetchall() or []
        userToReturn.warnings = [Warning(i["date"], i["reason"], i["expired"]) for i in warnings]

        return userToReturn
    

def includeEvent(user: Union[discord.Member,str], locale_id:int, city:str, event_name:str, address:str, price:float, starting_datetime: datetime, ending_datetime: datetime, description: str, group_link:str, website:str, max_price:float, event_logo_url:str):
    user_id = includeUser(user)
    with pooled_connection() as cursor:
        creds = getCredentials()
        try:
            CalendarDescription = CreateGCalendarDescription(price, max_price, group_link, website)
            
            eventToGCalendar = {
                "summary": event_name,
                "location": address,
                "description": CalendarDescription,
                "colorId": '7' if price == 0 else '3',
                #7: azul    
                #3: roxo
                "start": {
                    "dateTime": starting_datetime.isoformat(),
                    "timeZone": "America/Sao_Paulo",
                },
                "end": {
                    "dateTime": ending_datetime.isoformat(),
                    "timeZone": "America/Sao_Paulo",
                },
            }
            service = build('calendar', 'v3', credentials=creds)
            response = service.events().insert(calendarId=os.getenv('GOOGLE_CALENDAR_EVENTS_ID'), body=eventToGCalendar).execute()
            query = f"""INSERT IGNORE INTO events (host_user_id, locale_id, event_name, description, city, address, price, max_price, starting_datetime, ending_datetime, group_chat_link, website, event_logo_url, gcal_event_id)
        VALUES ({user_id}, {locale_id}, '{event_name}', '{description}', '{city}', '{address}', '{price}', '{max_price if max_price!=None else 0}', '{starting_datetime}', '{ending_datetime}', '{group_link}', '{website}', '{event_logo_url}', '{response['id']}');"""
            query = query.replace("'None'", 'NULL')
            cursor.execute(query)
            return True
        except HttpError as error:
            print('An error occurred: %s' % error)

def getAllEvents():
    with pooled_connection() as cursor:
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.address, 
                events.point_name, 
                events.price, 
                events.max_price, 
                events.starting_datetime, 
                events.ending_datetime, 
                events.description, 
                events.group_chat_link, 
                users.username, 
                locale.locale_name AS state, 
                locale.locale_abbrev AS state_abbrev, 
                events.city, 
                events.website, 
                events.out_of_tickets, 
                events.sales_ended
        FROM events
        JOIN users ON events.host_user_id = users.id
        JOIN locale ON events.locale_id = locale.id
        WHERE events.approved = 1"""
        cursor.execute(query)
        events = cursor.fetchall()
        for e in events:
            e['starting_datetime'] = datetime.strptime(f"{e['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
            e['ending_datetime'] = datetime.strptime(f"{e['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
            if e['website'] != None and not e['website'].__contains__('http'):
                e['website'] = f'https://{e["website"]}'
            if e['group_chat_link'] != None and not e['group_chat_link'].__contains__('http'):
                e['group_chat_link'] = f'https://{e["group_chat_link"]}'
        events = [e for e in events if e['ending_datetime'] >= datetime.now()]
        return events

def getAllPendingApprovalEvents():
    with pooled_connection() as cursor:
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.address, 
                events.point_name, 
                events.price, 
                events.max_price, 
                events.starting_datetime, 
                events.ending_datetime, 
                events.description, 
                events.group_chat_link, 
                users.username, 
                locale.locale_name AS state, 
                locale.locale_abbrev AS state_abbrev, 
                events.city, 
                events.website, 
                events.out_of_tickets, 
                events.sales_ended
        FROM events
        JOIN users ON events.host_user_id = users.id
        JOIN locale ON events.locale_id = locale.id
        WHERE events.approved = 0"""
        cursor.execute(query)
        events = cursor.fetchall()
        for e in events:
            e['starting_datetime'] = datetime.strptime(f"{e['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
            e['ending_datetime'] = datetime.strptime(f"{e['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
            if e['website'] != None and not e['website'].__contains__('http'):
                e['website'] = f'https://{e["website"]}'
            if e['group_chat_link'] != None and not e['group_chat_link'].__contains__('http'):
                e['group_chat_link'] = f'https://{e["group_chat_link"]}'
        return events

def getEventsByState(locale_id:int):
    with pooled_connection() as cursor:
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.address, 
                events.point_name, 
                events.price, 
                events.max_price, 
                events.starting_datetime, 
                events.ending_datetime, 
                events.description, 
                events.group_chat_link, 
                users.username, 
                locale.locale_name AS state, 
                locale.locale_abbrev AS state_abbrev, 
                events.city, 
                events.website, 
                events.out_of_tickets, 
                events.sales_ended
        FROM events
        JOIN users ON events.host_user_id = users.id
        JOIN locale ON events.locale_id = locale.id
        WHERE events.locale_id = '{locale_id}'
        AND events.approved = 1;"""
        cursor.execute(query)
        events = cursor.fetchall()
        for e in events:
            e['starting_datetime'] = datetime.strptime(f"{e['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
            e['ending_datetime'] = datetime.strptime(f"{e['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
            if e['website'] != None and not e['website'].__contains__('http'):
                e['website'] = f'https://{e["website"]}'
            if e['group_chat_link'] != None and not e['group_chat_link'].__contains__('http'):
                e['group_chat_link'] = f'https://{e["group_chat_link"]}'
        events = [e for e in events if e['ending_datetime'] >= datetime.now()]
        return events

def getEventByName(event_name:str):
    with pooled_connection() as cursor:
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.address, 
                events.point_name, 
                events.price, 
                events.max_price, 
                events.starting_datetime, 
                events.ending_datetime, 
                events.description, 
                events.group_chat_link, 
                users.username, 
                locale.locale_name AS state, 
                locale.locale_abbrev AS state_abbrev, 
                events.city, 
                events.website, 
                events.event_logo_url, 
                events.max_price, 
                events.out_of_tickets, 
                events.sales_ended
        FROM events
        JOIN users ON events.host_user_id = users.id
        JOIN locale ON events.locale_id = locale.id"""
        cursor.execute(query + f""" WHERE events.event_name = '{event_name}' AND events.approved = 1;""")
        events = cursor.fetchall()
        if event == []:
            cursor.execute(query + f""" WHERE events.event_name LIKE '%{event_name}%' AND events.approved = 1;""")
            events = cursor.fetchall()
        for e in events:
            e['starting_datetime'] = datetime.strptime(f"{e['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
            e['ending_datetime'] = datetime.strptime(f"{e['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
            if e['website'] != None and not e['website'].__contains__('http'):
                e['website'] = f'https://{e["website"]}'
            if e['group_chat_link'] != None and not e['group_chat_link'].__contains__('http'):
                e['group_chat_link'] = f'https://{e["group_chat_link"]}'
        return events[0] if events != [] else None 
    
def getEventsByOwner(owner_name:str):
    with pooled_connection() as cursor:
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.address, 
                events.point_name, 
                events.price, 
                events.max_price, 
                events.starting_datetime, 
                events.ending_datetime, 
                events.description, 
                events.group_chat_link, 
                users.username, 
                locale.locale_name AS state, 
                locale.locale_abbrev AS state_abbrev, 
                events.city, 
                events.website, 
                events.out_of_tickets, 
                events.sales_ended
        FROM events
        JOIN users ON events.host_user_id = users.id
        JOIN locale ON events.locale_id = locale.id
        WHERE users.username = '{owner_name}';"""
        cursor.execute(query)
        eventos = cursor.fetchall()
        for e in eventos:
            e['starting_datetime'] = datetime.strptime(f"{e['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
            e['ending_datetime'] = datetime.strptime(f"{e['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
            if e['website'] != None and not e['website'].__contains__('http'):
                e['website'] = f'https://{e["website"]}'
            if e['group_chat_link'] != None and not e['group_chat_link'].__contains__('http'):
                e['group_chat_link'] = f'https://{e["group_chat_link"]}'
        return eventos

def approveEventById(event_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT id FROM events WHERE id = {event_id} AND approved = 0;"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        if myresult == []:
            return "não encontrado"
        try:
            query = f"""UPDATE events
        SET approved = 1
        WHERE id = {event_id};"""
            cursor.execute(query)
            return True
        except:
            return False


def scheduleNextEventDate(event_name:str, new_starting_datetime:datetime, user):
    with pooled_connection() as cursor:
        #verifica se o evento já está agendado
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.starting_datetime, 
                events.ending_datetime, 
                users.username AS host_user, 
                events.price, 
                events.max_price, 
                events.group_chat_link, 
                events.website, 
                events.address, 
                events.gcal_event_id
        FROM events
        JOIN users ON events.host_user_id = users.id
        WHERE event_name = '{event_name}';"""
        cursor.execute(query)
        event = cursor.fetchone()
        if event is None:
            return "não encontrado"
        else:
            event["starting_datetime"] = datetime.strptime(f'{event["starting_datetime"]}', '%Y-%m-%d %H:%M:%S')
            event["ending_datetime"] = datetime.strptime(f'{event["ending_datetime"]}', '%Y-%m-%d %H:%M:%S')
            """ if event['ending_datetime'] > datetime.now():
                return "não encerrado" """
            updated = updateDateEvent(event, new_starting_datetime, user, True)
            return updated


def rescheduleEventDate(event_name:str, new_starting_datetime:datetime, user):
    with pooled_connection() as cursor:
        #verifica se o evento já está agendado
        query = f"""
        SELECT  events.id, 
                events.event_name, 
                events.starting_datetime, 
                events.ending_datetime, 
                users.username AS host_user, 
                events.gcal_event_id, 
                events.price, 
                events.max_price, 
                events.group_chat_link, 
                events.website, 
                events.address
        FROM events
        JOIN users ON events.host_user_id = users.id
        WHERE event_name = '{event_name}';"""
        cursor.execute(query)
        event = cursor.fetchone()
        if event is None:
            return "não encontrado"
        else:
            event["starting_datetime"] = datetime.strptime(f'{event["starting_datetime"]}', '%Y-%m-%d %H:%M:%S')
            event["ending_datetime"] = datetime.strptime(f'{event["ending_datetime"]}', '%Y-%m-%d %H:%M:%S')
            if event['ending_datetime'] > datetime.now() and event['starting_datetime'] < datetime.now():
                return "em andamento"
            if event['ending_datetime'] < datetime.now():
                return "encerrado"
            updated = updateDateEvent(event, new_starting_datetime, user, False)
            return updated


def updateDateEvent(event, new_starting_datetime:datetime, user:str, isNextEvent:bool):
    with pooled_connection() as cursor:
        if event['host_user'].lower() != user.lower() and user.lower() != 'titioderg':
            return "não é o dono"
        #calculando a diferença entre a data inicial e a data final do evento
        event_duration = event['ending_datetime'] - event['starting_datetime']
        #setando o horario antigo para o event_date
        new_starting_datetime = new_starting_datetime.replace(hour=event['starting_datetime'].hour, minute=event['starting_datetime'].minute, second=event['starting_datetime'].second)
        #somando a diferença com a data do evento
        new_ending_datetime = new_starting_datetime + event_duration
        creds = getCredentials()
        try:
            CalendarDescription = CreateGCalendarDescription(event['price'], event['max_price'], event['group_chat_link'], event['website'])
            eventToGCalendar = {
                "summary": event['event_name'],
                "location": event['address'],
                "description": CalendarDescription,
                "colorId": '7' if event['price'] == 0 else '3',
                #7: azul    
                #3: roxo
                "start": {
                    "dateTime": event['starting_datetime'].isoformat(),
                    "timeZone": "America/Sao_Paulo",
                },
                "end": {
                    "dateTime": event['ending_datetime'].isoformat(),
                    "timeZone": "America/Sao_Paulo",
                },
            }
            if isNextEvent: #
                service = build('calendar', 'v3', credentials=creds)
                service.events().insert(calendarId=os.getenv('GOOGLE_CALENDAR_EVENTS_ID'), body=eventToGCalendar).execute()
            service = build('calendar', 'v3', credentials=creds)
            eventToGCalendar['start']['dateTime'] = new_starting_datetime.isoformat()
            eventToGCalendar['end']['dateTime'] = new_ending_datetime.isoformat()
            service.events().update(
                calendarId=os.getenv('GOOGLE_CALENDAR_EVENTS_ID'),
                eventId=event['gcal_event_id'],
                body=eventToGCalendar).execute()
            #altera a data do evento
            query = f"""UPDATE events SET starting_datetime = '{new_starting_datetime}', ending_datetime = '{new_ending_datetime}' WHERE id = {event['id']};"""
            cursor.execute(query)
            return True
        except HttpError as error:
            print('An error occurred: %s' % error)

def admConnectTelegramAccount(discord_user:discord.Member, telegram_user:str):
    with pooled_connection() as cursor:
        #checa se o usuário já está cadastrado no banco de dados
        user_id = includeUser(discord_user)
        #checa se o telegram_user já está cadastrado no banco de dados
        query = f"""SELECT * FROM telegram_user WHERE user_id = '{user_id}';"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        if myresult == []:
            try:
                query = f"""INSERT INTO telegram_user (user_id, username, display_name, banned)
            VALUES ('{user_id}', '{telegram_user}', '{discord_user.nick}', 'FALSE');"""
                cursor.execute(query)
                return True
            except:
                return False
        else:
            return True
    

def assignTempRole(guild_id:int, discord_user:discord.Member, role_id:str, expiring_date:datetime, reason:str):
    with pooled_connection() as cursor:
        query = f"""SELECT id FROM discord_servers WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        discord_community_id = cursor.fetchone()["id"]
        user_id = includeUser(discord_user, guild_id)
        query = f"""SELECT id FROM discord_user WHERE user_id = '{user_id}';"""
        cursor.execute(query)
        discord_user_id = cursor.fetchone()["id"]
        try:
            query = f"""INSERT INTO temp_roles (disc_community_id, disc_user_id, role_id, expiring_date, reason)
            VALUES ('{discord_community_id}', '{discord_user_id}', '{role_id}', '{expiring_date}', '{reason}');"""
            cursor.execute(query)
            return True
        except Exception as e:
            print(e)
            return False
    
def getExpiringTempRoles(guild_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT id FROM discord_servers WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        discord_community_id = cursor.fetchone()["id"]
        query = f"""SELECT temp_roles.id, temp_roles.role_id, discord_user.discord_user_id AS user_id FROM temp_roles
    JOIN discord_user ON temp_roles.disc_user_id = discord_user.id
    WHERE temp_roles.disc_community_id = '{discord_community_id}'
    AND temp_roles.expiring_date <= NOW();
        """
        cursor.execute(query)
        expiredTempRoles = cursor.fetchall()
        return expiredTempRoles

def deleteTempRole(tempRoleDBId:int):
    with pooled_connection() as cursor:
        try:
            query = f"""DELETE FROM temp_roles
        WHERE id = {tempRoleDBId}"""
            cursor.execute(query)
            return True
        except Exception as e:
            print(e)
            return False

def warnMember(guild_id:int, discord_user:discord.Member, reason:str):
    with pooled_connection() as cursor:
        user_id = includeUser(discord_user, guild_id)
        query = f"""SELECT community_id FROM discord_servers WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        community_id = cursor.fetchone()["community_id"]
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            query = f"""INSERT INTO warnings (user_id, community_id, date, reason, expired)
            VALUES ('{user_id}', '{community_id}', '{date}', '{reason}', FALSE);"""
            cursor.execute(query)
            query = f"""SELECT COUNT(*) FROM warnings
    WHERE user_id = '{user_id}'
    AND community_id = '{community_id}';"""
            cursor.execute(query)
            warningsCount = cursor.fetchone()[0]
            #pegar o número de warnings necessários para banir o usuário
            query = f"""SELECT warnings_limit FROM warnings_settings
    WHERE community_id = '{community_id}';"""
            cursor.execute(query)
            warningsLimit = cursor.fetchone()["warnings_limit"]
            return {'warningsCount': warningsCount, 'warningsLimit': warningsLimit}
        except Exception as e:
            print(e)
            return False
    
def getMemberWarnings(guild_id:int, discord_user:discord.Member) -> list[Warning]:
    with pooled_connection() as cursor:
        user_id = includeUser(discord_user, guild_id)
        query = f"""SELECT community_id FROM discord_servers WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        community_id = cursor.fetchone()["community_id"]
        query = f"""SELECT date, reason, expired FROM warnings
    WHERE user_id = '{user_id}'
    AND community_id = '{community_id}';"""
        cursor.execute(query)
        results:list[Warning] = cursor.fetchall()
        warnings = [Warning(warning[0], warning[1], warning[2]) for warning in results]
        return warnings

def getStaffRoles(guild_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT staff_roles FROM server_settings WHERE server_guild_id = '{guild_id}';"""
        cursor.execute(query)
        return cursor.fetchall()

def registerUser(guild_id: int, discord_user: discord.Member, birthday: date, approved_date: date = None) -> bool:
    """Register a member in the database and saves the birthday."""
    user_id = includeUser(discord_user, guild_id, datetime.now() if approved_date is None else approved_date)
    birthdayRegistered = False
    try:
        birthdayRegistered = includeBirthday(guild_id, birthday, discord_user, False, user_id)
    except Exception as e:
        if not e.args[0].__contains__('Duplicate entry'):
            print(e)
        else:
            birthdayRegistered = True
    return user_id is not None and birthdayRegistered

def saveCustomRole(guild_id:int, discord_user:discord.Member, color:str=None, iconId:int=None):
    if color == None and iconId == None: return False
    try:
        user_id = includeUser(discord_user, guild_id)
        with pooled_connection(True) as cursor:
            query = f"""SELECT user_id FROM user_custom_roles
        WHERE user_id = '{user_id}'
        AND server_guild_id = '{guild_id}';"""
            cursor.execute(query)
            myresult = cursor.fetchone()
            if myresult != None:
                query = f"""UPDATE user_custom_roles
                SET {f"color = '{color}', icon_id = {iconId}" if color and iconId
                    else f"color = '{color}'" if color!= None 
                    else f"icon_id = {iconId}"}
                WHERE user_id = '{user_id}'
                AND server_guild_id = '{guild_id}';"""
                cursor.execute(query)
                return True
            else:
                query = f"""INSERT INTO user_custom_roles (server_guild_id, user_id, color, icon_id)
        VALUES ({guild_id}, {user_id}, {f"'{color}'" if color else 'NULL'},{f"{iconId}" if iconId else 'NULL'});"""
                cursor.execute(query)
                return True
    except:
        return False
    

def getAllCustomRoles(guild_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT discord_user.discord_user_id, user_custom_roles.color, user_custom_roles.icon_id FROM user_custom_roles
    JOIN discord_user ON user_custom_roles.user_id = discord_user.user_id
    WHERE user_custom_roles.server_guild_id = '{guild_id}'
        """
        cursor.execute(query)
        customRoles: list[CustomRole] = cursor.fetchall()
        return [CustomRole(role["discord_user_id"], role["color"], role["icon_id"]) for role in customRoles] if customRoles != [] else None


def grantNSFWAccess(guild_id:int, discord_user:discord.Member, birthday:date):
    approved = False
    try:
        user_id = includeUser(discord_user, guild_id)
        with pooled_connection() as cursor:
            query = f"""SELECT user_id, birth_date FROM user_birthday
    WHERE user_id = {user_id}"""
            cursor.execute(query)
            myresult = cursor.fetchone()
            if myresult != None:
                databaseBirthday = datetime.strptime(f"{myresult[1]}", '%Y-%m-%d').date()
                if databaseBirthday == birthday:
                    query = f"""UPDATE user_birthday
    SET verified = 1
    WHERE user_id = {user_id}"""
                    cursor.execute(query)
                    approved = True
                else:
                    approved = 'dont_match'
            else:
                approved = 'not_registered'
            return approved
    except Exception as e: 
        return approved
            
def getServerMessage(messageType:ServerMessagesEnum, guild_id:int):
    with pooled_connection(True) as cursor:
        query = f"""SELECT {messageType} 
        FROM discord_server_messages
        WHERE server_guild_id = {guild_id}"""
        cursor.execute(query)
        message = cursor.fetchone()
        return message if message != None else None

def setServerMessage(guild_id:int, messageType:ServerMessagesEnum, message:str):
    with pooled_connection(True) as cursor:
        query = f"""SELECT * 
    FROM discord_server_messages
    WHERE server_guild_id = {guild_id}"""
        cursor.execute(query)
        myresult = cursor.fetchone()
        try:
            if myresult == None:
                query = f"""INSERT INTO discord_server_messages (server_guild_id, {messageType})
        VALUES ({guild_id}, '{message}')"""
                cursor.execute(query)
                return True
            else:
                query = f"""UPDATE discord_server_messages
        SET {messageType} = '{message}'
        WHERE server_guild_id = {guild_id}"""
                cursor.execute(query)
                return True
        except Exception as e:
            return False


def getTodayBirthdays(guild_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT discord_user.discord_user_id, user_birthday.birth_date FROM user_birthday
    JOIN discord_user ON user_birthday.user_id = discord_user.user_id
    WHERE MONTH(birth_date) = MONTH(NOW())
    AND DAY(birth_date) = DAY(NOW())
    AND mentionable = 1;"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        users:list[SimpleUserBirthday] = []
        for ub in myresult:
            users.append(SimpleUserBirthday(ub["discord_user_id"],ub["birth_date"]))
        return users


def updateVoiceRecord(guild_id:int, discord_user:discord.Member, seconds:int):
    """Update the longest continuous voice call time for a member"""
    user_id = includeUser(discord_user, guild_id)
    with pooled_connection() as cursor:
        try:
            query = f"""INSERT INTO user_records (user_id, server_guild_id, voice_time)
    VALUES ({user_id}, {guild_id}, {seconds})
    ON DUPLICATE KEY UPDATE voice_time = IF({seconds} > voice_time, {seconds}, voice_time);"""
            cursor.execute(query)
            return True
        except mysql.connector.Error as err:
            logging.error(f"Database error occurred: {err}")
            return False


def getVoiceTime(guild_id:int, discord_user:discord.Member) -> int:
    """Retrieve the total recorded voice time in seconds for a member"""
    user_id = includeUser(discord_user, guild_id)
    with pooled_connection() as cursor:
        query = f"""SELECT voice_time FROM user_records
    WHERE user_id = {user_id} AND server_guild_id = {guild_id};"""
        cursor.execute(query)
        myresult = cursor.fetchone()
        return myresult[0] if myresult else 0


def getAllVoiceRecords(guild_id: int, limit: int = 10):
    """Retrieve top voice call records for a guild sorted by duration"""
    with pooled_connection() as cursor:
        query = f"""SELECT discord_user.discord_user_id, user_records.voice_time
    FROM user_records
    JOIN discord_user ON discord_user.user_id = user_records.user_id
    WHERE user_records.server_guild_id = {guild_id}
    ORDER BY user_records.voice_time DESC
    LIMIT {limit};"""
        cursor.execute(query)
        records = cursor.fetchall()
        return [{'user_id': row["discord_user_id"], 'seconds': row["voice_time"]} for row in records]
