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


def connectToDatabase():
    mydb = mysql.connector.connect(
        host=os.getenv('BOT_DATABASE_HOST'),
        user=os.getenv('BOT_DATABASE_USER'),
        password=os.getenv('BOT_DATABASE_PASSWORD'),
        database='coddy'
    )
    return mydb

def endConnection(mydb):
    cursor = mydb.cursor()
    mydb.close()
    cursor.close()

def endConnectionWithCommit(mydb):
    mydb.commit()
    endConnection(mydb)
    
connection_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)

@contextmanager
def pooled_connection():
    connection = connection_pool.get_connection()
    cursor: MySQLCursorAbstract = connection.cursor(dictionary=True)
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
    mydb = connectToDatabase()
    cursor = mydb.cursor(buffered=True)
    #verifica se a comunidade já está no banco de dados
    query = f"""SELECT * FROM communities"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    if myresult == []:
        botOriginalGuildName = discord.utils.get(guild.client.guilds, id=int(os.getenv('BOT_GUILD_ID'))).name
        query = f"""INSERT IGNORE INTO communities (name)
VALUES ('{botOriginalGuildName}');"""
        cursor.execute(query)
        query = f"""INSERT IGNORE INTO discord_servers (community_id, name, guild_id)
VALUES ('{myresult[-1][0]}', '{guild.name}', '{guild.id}');"""
        cursor.execute(query)
    else:
        existInCommunities = False
        for community in myresult:
            if community[1] in guild.name:
                existInCommunities = True
                query = f"""INSERT IGNORE INTO discord_servers (community_id, name, guild_id) 
            VALUES ('{community[0]}', '{guild.name}', '{guild.id}');"""
            cursor.execute(query)
            continue
        if not existInCommunities:
            query = f"""INSERT IGNORE INTO communities (name)
VALUES ('{guild.name}');""" 
            cursor.execute(query)
            query = f"""SELECT * FROM communities"""
            cursor.execute(query)
            myresult = cursor.fetchall()
            query = f"""INSERT IGNORE INTO discord_servers (community_id, name, guild_id)
VALUES ('{myresult[-1][0]}', '{guild.name}', '{guild.id}');"""
            cursor.execute(query)
    query = f"""INSERT IGNORE INTO server_settings (server_guild_id) 
VALUES ('{guild.id}');"""
    cursor.execute(query)
    mydb.commit()
    
    # Recupera as configurações do servidor
    query = f"""SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'server_settings';"""
    cursor.execute(query)
    todas_colunas = cursor.fetchall()

    dynamic_query = f"""SELECT discord_servers.name, discord_servers.guild_id"""
    for column in todas_colunas:
        if column[0] != 'server_guild_id' and column[0] != 'id':
            dynamic_query += f", server_settings.{column[0]}"

    dynamic_query += f"""
FROM discord_servers
LEFT JOIN server_settings ON discord_servers.guild_id = server_settings.server_guild_id
WHERE discord_servers.guild_id = '{guild.id}'"""

    cursor.execute(dynamic_query)
    myresult = cursor.fetchall()

    column_names = ['name', 'guildId']
    for column in todas_colunas:
        if column[0] != 'server_guild_id' and column[0] != 'id':
            columnName = column[0].split('_')
            columnName = "".join(element.title() if element!=columnName[0] else element for element in columnName)
            column_names.append(columnName)
    config = dict(zip(column_names, myresult[0]))

    
    cursor.close()
    mydb.close()

    return config

def getLevelConfig():
    mydb = connectToDatabase()
    cursor = mydb.cursor(buffered=True)
    query = f"""SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'level_config';"""
    

def hasGPTEnabled(guild:discord.Guild):
    mydb = connectToDatabase()
    cursor = mydb.cursor(buffered=True)
    query = f"""SELECT has_gpt_enabled, gpt_model FROM server_settings
WHERE server_guild_id = '{guild.id}';"""
    cursor.execute(query)
    myresult = cursor.fetchone()
    cursor.close()
    mydb.close()
    propriedades = ['enabled','model']
    gpt_dict = dict(zip(propriedades, myresult))
    return gpt_dict

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



def getAllLocals(mydb):
    cursor = mydb.cursor()
    query = f"""SELECT * FROM locale"""
    cursor.execute(query)

    myResult = cursor.fetchall()
    locals_list = [{'id': local[0], 'locale_abbrev': local[1], 'locale_name': local[2]} for local in myResult]
    return locals_list


def getUserId(discord_user_id: int):
    """Fetch the internal user id for a Discord member."""
    with pooled_connection() as cursor:
        cursor.execute(
            "SELECT user_id FROM discord_user WHERE discord_user_id = %s",
            (discord_user_id,)
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None




def includeUser(mydb, user: Union[discord.Member, str], guildId: int = os.getenv("DISCORD_GUILD_ID"), approvedAt: datetime = None) -> int:
    """Ensure a user exists in the database and return the internal id."""
    cursor = mydb.cursor(dictionary=True, buffered=True)

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

    mydb.commit()
    return user_id

def includeLocale(mydb, guildId: int, abbrev:str, user:discord.User, availableLocals:list):
    user_id = includeUser(mydb, user, guildId)
    cursor = mydb.cursor()
    for local in availableLocals:
        if local['locale_abbrev'] == abbrev:
            try:
                query = f"""INSERT INTO user_locale (user_id, locale_id) VALUES ('{user_id}','{local['id']}');"""
                cursor.execute(query)
                mydb.commit()
                return True
            except:
                return False

def getByLocale(mydb, abbrev:str, availableLocals:list):
    cursor = mydb.cursor()
    for local in availableLocals:
        if local['locale_abbrev'] == abbrev:
            query = f"""SELECT users.username
FROM users
JOIN user_locale ON users.id = user_locale.user_id
JOIN locale ON user_locale.locale_id = locale.id
WHERE locale.locale_abbrev = '{abbrev}';"""
            cursor.execute(query)
            myresult = cursor.fetchall()
            #convertendo para lista
            myresult = [i[0] for i in myresult]
            return myresult
        
def includeBirthday(mydb, guildId: int, date:date, user:discord.User, mentionable:bool, userId:int=None, registered:bool=False):
    if userId != None:
        user_id = userId
    else:
        user_id = includeUser(mydb, user, guildId)
    cursor = mydb.cursor()
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
            mydb.commit()
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
            mydb.commit()
            return True
        except:
            return False

def getAllBirthdays():
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT discord_user.discord_user_id, user_birthday.birth_date
FROM discord_user
JOIN user_birthday ON discord_user.user_id = user_birthday.user_id
WHERE user_birthday.mentionable = 1;"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    endConnection(mydb)
    #convertendo para uma lista de dicionários
    myresult = [{'user_id': i[0], 'birth_date': i[1]} for i in myresult]
    return myresult

def getUserInfo(user: discord.Member, guildId: int, userId: int = None, create_if_missing: bool = True) -> User :
    """Retrieve a user from the database. Optionally registers the user if missing."""
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    user_id = includeUser(mydb, user, guildId)

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
    

def includeEvent(mydb, user: Union[discord.Member,str], locale_id:int, city:str, event_name:str, address:str, price:float, starting_datetime: datetime, ending_datetime: datetime, description: str, group_link:str, website:str, max_price:float, event_logo_url:str):
    user_id = includeUser(mydb, user)
    cursor = mydb.cursor()
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
        mydb.commit()
        return True
    except HttpError as error:
        print('An error occurred: %s' % error)

def getAllEvents():
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT events.id, events.event_name, events.address, events.point_name, events.price, events.max_price, events.starting_datetime, events.ending_datetime, events.description, events.group_chat_link, users.username, locale.locale_name, locale.locale_abbrev, events.city, events.website, events.out_of_tickets, events.sales_ended
FROM events
JOIN users ON events.host_user_id = users.id
JOIN locale ON events.locale_id = locale.id
WHERE events.approved = 1"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    endConnection(mydb)
    #convertendo para uma lista de dicionários
    propriedades = ['id','event_name', 'address', 'point_name', 'price', 'max_price', 'starting_datetime', 'ending_datetime', 'description', 'group_chat_link', 'host_user', 'state', 'state_abbrev', 'city', 'website', 'out_of_tickets', 'sales_ended']
    resultados_finais = []
    for i in myresult:
        evento_dict = dict(zip(propriedades, i))
        evento_dict['starting_datetime'] = datetime.strptime(f"{evento_dict['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
        evento_dict['ending_datetime'] = datetime.strptime(f"{evento_dict['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
        if evento_dict['website'] != None and not evento_dict['website'].__contains__('http'):
            evento_dict['website'] = f'https://{evento_dict["website"]}'
        if evento_dict['group_chat_link'] != None and not evento_dict['group_chat_link'].__contains__('http'):
            evento_dict['group_chat_link'] = f'https://{evento_dict["group_chat_link"]}'
        resultados_finais.append(evento_dict)
    myresult = [i for i in resultados_finais if i['ending_datetime'] >= datetime.now()]
    return myresult

def getAllPendingApprovalEvents():
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT events.id, events.event_name, events.address, events.point_name, events.price, events.max_price, events.starting_datetime, events.ending_datetime, events.description, events.group_chat_link, users.username, locale.locale_name, locale.locale_abbrev, events.city, events.website, events.out_of_tickets, events.sales_ended
FROM events
JOIN users ON events.host_user_id = users.id
JOIN locale ON events.locale_id = locale.id
WHERE events.approved = 0"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    endConnection(mydb)
    #convertendo para uma lista de dicionários
    propriedades = ['id','event_name', 'address', 'point_name', 'price', 'max_price', 'starting_datetime', 'ending_datetime', 'description', 'group_chat_link', 'host_user', 'state', 'state_abbrev', 'city', 'website', 'out_of_tickets', 'sales_ended']
    resultados_finais = []
    for i in myresult:
        evento_dict = dict(zip(propriedades, i))
        evento_dict['starting_datetime'] = datetime.strptime(f"{evento_dict['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
        evento_dict['ending_datetime'] = datetime.strptime(f"{evento_dict['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
        if evento_dict['website'] != None and not evento_dict['website'].__contains__('http'):
            evento_dict['website'] = f'https://{evento_dict["website"]}'
        if evento_dict['group_chat_link'] != None and not evento_dict['group_chat_link'].__contains__('http'):
            evento_dict['group_chat_link'] = f'https://{evento_dict["group_chat_link"]}'
        resultados_finais.append(evento_dict)
    myresult = resultados_finais
    return myresult

def getEventsByState(locale_id:int):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT events.id, events.event_name, events.address, events.point_name, events.price, events.max_price, events.starting_datetime, events.ending_datetime, events.description, events.group_chat_link, users.username, locale.locale_name, locale.locale_abbrev, events.city, events.website, events.out_of_tickets, events.sales_ended
FROM events
JOIN users ON events.host_user_id = users.id
JOIN locale ON events.locale_id = locale.id
WHERE events.locale_id = '{locale_id}'
AND events.approved = 1;"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    endConnection(mydb)
    #convertendo para uma lista de dicionários
    propriedades = ['id','event_name', 'address', 'point_name', 'price', 'max_price', 'starting_datetime', 'ending_datetime', 'description', 'group_chat_link', 'host_user', 'state', 'state_abbrev', 'city', 'website', 'out_of_tickets', 'sales_ended']
    resultados_finais = []
    for i in myresult:
        evento_dict = dict(zip(propriedades, i))
        evento_dict['starting_datetime'] = datetime.strptime(f"{evento_dict['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
        evento_dict['ending_datetime'] = datetime.strptime(f"{evento_dict['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
        if evento_dict['website'] != None and not evento_dict['website'].__contains__('http'):
            evento_dict['website'] = f'https://{evento_dict["website"]}'
        if evento_dict['group_chat_link'] != None and not evento_dict['group_chat_link'].__contains__('http'):
            evento_dict['group_chat_link'] = f'https://{evento_dict["group_chat_link"]}'
        resultados_finais.append(evento_dict)
    myresult = [i for i in resultados_finais if i['ending_datetime'] >= datetime.now()]
    return myresult

def getEventByName(event_name:str):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT events.id, events.event_name, events.address, events.point_name, events.price, events.max_price, events.starting_datetime, events.ending_datetime, events.description, events.group_chat_link, users.username, locale.locale_name, locale.locale_abbrev, events.city, events.website, events.event_logo_url, events.max_price, events.out_of_tickets, events.sales_ended
FROM events
JOIN users ON events.host_user_id = users.id
JOIN locale ON events.locale_id = locale.id
WHERE events.event_name = '{event_name}'
AND events.approved = 1;"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    if myresult == []:
        query = f"""SELECT events.id, events.event_name, events.address, events.point_name, events.price, events.max_price, events.starting_datetime, events.ending_datetime, events.description, events.group_chat_link, users.username, locale.locale_name, locale.locale_abbrev, events.city, events.website, events.event_logo_url, events.max_price, events.out_of_tickets, events.sales_ended
FROM events
JOIN users ON events.host_user_id = users.id
JOIN locale ON events.locale_id = locale.id
WHERE events.event_name LIKE '%{event_name}%'
AND events.approved = 1;"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        endConnection(mydb)
    #convertendo para uma lista de dicionários
    propriedades = ['id','event_name', 'address', 'point_name', 'price', 'max_price', 'starting_datetime', 'ending_datetime', 'description', 'group_chat_link', 'host_user', 'state', 'state_abbrev', 'city', 'website', 'logo_url', 'max_price', 'out_of_tickets', 'sales_ended']
    resultados_finais = []
    for i in myresult:
        evento_dict = dict(zip(propriedades, i))
        evento_dict['starting_datetime'] = datetime.strptime(f"{evento_dict['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
        evento_dict['ending_datetime'] = datetime.strptime(f"{evento_dict['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
        if evento_dict['website'] != None and not evento_dict['website'].__contains__('http'):
            evento_dict['website'] = f'https://{evento_dict["website"]}'
        if evento_dict['group_chat_link'] != None and not evento_dict['group_chat_link'].__contains__('http'):
            evento_dict['group_chat_link'] = f'https://{evento_dict["group_chat_link"]}'
        resultados_finais.append(evento_dict)
    return resultados_finais[0] if resultados_finais != [] else None 
    
def getEventsByOwner(mydb, owner_name:str):
    cursor = mydb.cursor()
    query = f"""SELECT events.id, events.event_name, events.address, events.point_name, events.price, events.max_price, events.starting_datetime, events.ending_datetime, events.description, events.group_chat_link, users.username, locale.locale_name, locale.locale_abbrev, events.city, events.website, events.out_of_tickets, events.sales_ended
FROM events
JOIN users ON events.host_user_id = users.id
JOIN locale ON events.locale_id = locale.id
WHERE users.username = '{owner_name}';"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    #convertendo para uma lista de dicionários
    propriedades = ['id','event_name', 'address', 'point_name', 'price', 'max_price', 'starting_datetime', 'ending_datetime', 'description', 'group_chat_link', 'host_user', 'state', 'state_abbrev', 'city', 'website', 'out_of_tickets', 'sales_ended']
    resultados_finais = []
    for i in myresult:
        evento_dict = dict(zip(propriedades, i))
        evento_dict['starting_datetime'] = datetime.strptime(f"{evento_dict['starting_datetime']}", '%Y-%m-%d %H:%M:%S')
        evento_dict['ending_datetime'] = datetime.strptime(f"{evento_dict['ending_datetime']}", '%Y-%m-%d %H:%M:%S')
        if evento_dict['website'] != None and not evento_dict['website'].__contains__('http'):
            evento_dict['website'] = f'https://{evento_dict["website"]}'
        if evento_dict['group_chat_link'] != None and not evento_dict['group_chat_link'].__contains__('http'):
            evento_dict['group_chat_link'] = f'https://{evento_dict["group_chat_link"]}'
        resultados_finais.append(evento_dict)
    return resultados_finais

def approveEventById(event_id:int):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT id FROM events WHERE id = {event_id} AND approved = 0;"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    if myresult == []:
        endConnection(mydb)
        return "não encontrado"
    try:
        query = f"""UPDATE events
    SET approved = 1
    WHERE id = {event_id};"""
        cursor.execute(query)
        endConnectionWithCommit(mydb)
        return True
    except:
        endConnection(mydb)
        return False


def scheduleNextEventDate(event_name:str, new_starting_datetime:datetime, user):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    #verifica se o evento já está agendado
    query = f"""SELECT events.id, events.event_name, events.starting_datetime, events.ending_datetime, users.username, events.price, events.max_price, events.group_chat_link, events.website, events.address, events.gcal_event_id
FROM events
JOIN users ON events.host_user_id = users.id
WHERE event_name = '{event_name}';"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    if myresult == []:
        endConnection(mydb)
        return "não encontrado"
    else:
        myresult = [{'id': i[0], 'event_name': i[1], 'starting_datetime': datetime.strptime(f'{i[2]}', '%Y-%m-%d %H:%M:%S'), 'ending_datetime': datetime.strptime(f'{i[3]}', '%Y-%m-%d %H:%M:%S'), 'host_user': i[4], 'price': i[5], 'max_price': i[6], 'group_chat_link': i[7], 'website': i[8], 'address': i[9], 'gcal_event_id':i[10]
                        } for i in myresult]
        """ if myresult[0]['ending_datetime'] > datetime.now():
            return "não encerrado" """
        updated = updateDateEvent(mydb, myresult, new_starting_datetime, user, True)
        endConnectionWithCommit(mydb)
        return updated


def rescheduleEventDate(mydb, event_name:str, new_starting_datetime:datetime, user):
    cursor = mydb.cursor()
    #verifica se o evento já está agendado
    query = f"""SELECT events.id, events.event_name, events.starting_datetime, events.ending_datetime, users.username, events.gcal_event_id, events.price, events.max_price, events.group_chat_link, events.website, events.address
FROM events
JOIN users ON events.host_user_id = users.id
WHERE event_name = '{event_name}';"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    if myresult == []:
        return "não encontrado"
    else:
        myresult = [{'id': i[0], 'event_name': i[1], 'starting_datetime': datetime.strptime(f'{i[2]}', '%Y-%m-%d %H:%M:%S'), 'ending_datetime': datetime.strptime(f'{i[3]}', '%Y-%m-%d %H:%M:%S'), 'host_user': i[4], 'gcal_event_id':i[5], 'price': i[6], 'max_price': i[7], 'group_chat_link': i[8], 'website': i[9], 'address': i[10]
                     } for i in myresult]
        if myresult[0]['ending_datetime'] > datetime.now() and myresult[0]['starting_datetime'] < datetime.now():
            return "em andamento"
        if myresult[0]['ending_datetime'] < datetime.now():
            return "encerrado"
        updated = updateDateEvent(mydb, myresult, new_starting_datetime, user, False)
        endConnectionWithCommit(mydb)
        return updated


def updateDateEvent(mydb, myresult, new_starting_datetime:datetime, user:str, isNextEvent:bool):
    cursor = mydb.cursor()
    if myresult[0]['host_user'].lower() != user.lower() and user.lower() != 'titioderg':
        return "não é o dono"
    #calculando a diferença entre a data inicial e a data final do evento
    event_duration = myresult[0]['ending_datetime'] - myresult[0]['starting_datetime']
    #setando o horario antigo para o event_date
    new_starting_datetime = new_starting_datetime.replace(hour=myresult[0]['starting_datetime'].hour, minute=myresult[0]['starting_datetime'].minute, second=myresult[0]['starting_datetime'].second)
    #somando a diferença com a data do evento
    new_ending_datetime = new_starting_datetime + event_duration
    creds = getCredentials()
    try:
        CalendarDescription = CreateGCalendarDescription(myresult[0]['price'], myresult[0]['max_price'], myresult[0]['group_chat_link'], myresult[0]['website'])
        eventToGCalendar = {
            "summary": myresult[0]['event_name'],
            "location": myresult[0]['address'],
            "description": CalendarDescription,
            "colorId": '7' if myresult[0]['price'] == 0 else '3',
            #7: azul    
            #3: roxo
            "start": {
                "dateTime": myresult[0]['starting_datetime'].isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": myresult[0]['ending_datetime'].isoformat(),
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
            eventId=myresult[0]['gcal_event_id'],
            body=eventToGCalendar).execute()
        #altera a data do evento
        query = f"""UPDATE events SET starting_datetime = '{new_starting_datetime}', ending_datetime = '{new_ending_datetime}' WHERE id = {myresult[0]['id']};"""
        cursor.execute(query)
        mydb.commit()
        return True
    except HttpError as error:
        print('An error occurred: %s' % error)

def admConnectTelegramAccount(discord_user:discord.Member, telegram_user:str):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    #checa se o usuário já está cadastrado no banco de dados
    user_id = includeUser(mydb, discord_user)
    #checa se o telegram_user já está cadastrado no banco de dados
    query = f"""SELECT * FROM telegram_user WHERE user_id = '{user_id}';"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    if myresult == []:
        try:
            query = f"""INSERT INTO telegram_user (user_id, username, display_name, banned)
        VALUES ('{user_id}', '{telegram_user}', '{discord_user.nick}', 'FALSE');"""
            cursor.execute(query)
            endConnectionWithCommit(mydb)
            return True
        except:
            endConnection(mydb)
            return False
    else:
        endConnection(mydb)
        return True
    

def assignTempRole(mydb, guild_id:int, discord_user:discord.Member, role_id:str, expiring_date:datetime, reason:str):
    cursor = mydb.cursor()
    query = f"""SELECT id FROM discord_servers WHERE guild_id = '{guild_id}';"""
    cursor.execute(query)
    discord_community_id = cursor.fetchall()[0][0]
    user_id = includeUser(mydb, discord_user, guild_id)
    query = f"""SELECT id FROM discord_user WHERE user_id = '{user_id}';"""
    cursor.execute(query)
    result = cursor.fetchall()
    discord_user_id = result[0][0]
    try:
        query = f"""INSERT INTO temp_roles (disc_community_id, disc_user_id, role_id, expiring_date, reason)
        VALUES ('{discord_community_id}', '{discord_user_id}', '{role_id}', '{expiring_date}', '{reason}');"""
        cursor.execute(query)
        mydb.commit()
        return True
    except Exception as e:
        print(e)
        return False
    
def getExpiringTempRoles(mydb, guild_id:int):
    cursor = mydb.cursor()
    query = f"""SELECT id FROM discord_servers WHERE guild_id = '{guild_id}';"""
    cursor.execute(query)
    discord_community_id = cursor.fetchall()[0][0]
    query = f"""SELECT temp_roles.id, temp_roles.role_id, discord_user.discord_user_id FROM temp_roles
JOIN discord_user ON temp_roles.disc_user_id = discord_user.id
WHERE temp_roles.disc_community_id = '{discord_community_id}'
AND temp_roles.expiring_date <= NOW();
    """
    cursor.execute(query)
    myresult = cursor.fetchall()
    ## convertendo para uma lista de dicionários
    propriedades = ['id','role_id', 'user_id']
    resultados_finais = []
    for i in myresult:
        temp_role_dict = dict(zip(propriedades, i))
        resultados_finais.append(temp_role_dict)
    return resultados_finais

def deleteTempRole(cursor, tempRoleDBId:int):
    query = f"""DELETE FROM temp_roles
WHERE id = {tempRoleDBId}"""
    cursor.execute(query)
    return True

def warnMember(mydb, guild_id:int, discord_user:discord.Member, reason:str):
    cursor = mydb.cursor()
    user_id = includeUser(mydb, discord_user, guild_id)
    query = f"""SELECT community_id FROM discord_servers WHERE guild_id = '{guild_id}';"""
    cursor.execute(query)
    community_id = cursor.fetchall()[0][0]
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        query = f"""INSERT INTO warnings (user_id, community_id, date, reason, expired)
        VALUES ('{user_id}', '{community_id}', '{date}', '{reason}', FALSE);"""
        cursor.execute(query)
        query = f"""SELECT COUNT(*) FROM warnings
WHERE user_id = '{user_id}'
AND community_id = '{community_id}';"""
        cursor.execute(query)
        warningsCount = cursor.fetchall()[0][0]
        #pegar o número de warnings necessários para banir o usuário
        query = f"""SELECT warnings_limit FROM warnings_settings
WHERE community_id = '{community_id}';"""
        cursor.execute(query)
        warningsLimit = cursor.fetchall()[0][0]
        mydb.commit()
        return {'warningsCount': warningsCount, 'warningsLimit': warningsLimit}
    except Exception as e:
        print(e)
        return False
    
def getMemberWarnings(guild_id:int, discord_user:discord.Member) -> list[Warning]:
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    user_id = includeUser(mydb, discord_user, guild_id)
    query = f"""SELECT community_id FROM discord_servers WHERE guild_id = '{guild_id}';"""
    cursor.execute(query)
    community_id = cursor.fetchall()[0][0]
    query = f"""SELECT date, reason, expired FROM warnings
WHERE user_id = '{user_id}'
AND community_id = '{community_id}';"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    resultados_finais:list[Warning] = []
    for i in myresult:
        warnings = Warning(i[0], i[1], i[2])
        resultados_finais.append(warnings)
    return resultados_finais

def getStaffRoles(guild_id:int):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT staff_roles FROM server_settings WHERE server_guild_id = '{guild_id}';"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    return myresult[0][0]

def registerUser(guild_id: int, discord_user: discord.Member, birthday: date, approved_date: date = None) -> bool:
    """Register a member in the database and saves the birthday."""
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    user_id = includeUser(mydb, discord_user, guild_id, datetime.now() if approved_date is None else approved_date)
    birthdayRegistered = False
    try:
        birthdayRegistered = includeBirthday(cursor.connection, guild_id, birthday, discord_user, False, user_id)
    except Exception as e:
        if not e.args[0].__contains__('Duplicate entry'):
            print(e)
        else:
            birthdayRegistered = True
    return user_id is not None and birthdayRegistered

def saveCustomRole(guild_id:int, discord_user:discord.Member, color:str=None, iconId:int=None):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    if color == None and iconId == None: return False
    try:
        user_id = includeUser(mydb, discord_user, guild_id)
        cursor = mydb.cursor(buffered=True)
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
            mydb.commit()
            return True
        else:
            query = f"""INSERT INTO user_custom_roles (server_guild_id, user_id, color, icon_id)
    VALUES ({guild_id}, {user_id}, {f"'{color}'" if color else 'NULL'},{f"{iconId}" if iconId else 'NULL'});"""
            cursor.execute(query)
            mydb.commit()
            return True
    except:
        return False
    

def getAllCustomRoles(guild_id:int):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT discord_user.discord_user_id, user_custom_roles.color, user_custom_roles.icon_id FROM user_custom_roles
JOIN discord_user ON user_custom_roles.user_id = discord_user.user_id
WHERE user_custom_roles.server_guild_id = '{guild_id}'
    """
    cursor.execute(query)
    myresult = cursor.fetchall()
    customRoles: list[CustomRole] = []
    for customRole in myresult:
        customRoles.append(CustomRole(customRole[0],customRole[1],customRole[2]))
    return customRoles


def grantNSFWAccess(guild_id:int, discord_user:discord.Member, birthday:date):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    approved = False
    try:
        user_id = includeUser(mydb, discord_user, guild_id)
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
    finally:
        if approved:
            endConnectionWithCommit(mydb)
        else:
            endConnection(mydb)
            
def getServerMessage(messageType:ServerMessagesEnum, guild_id:int):
    mydb = connectToDatabase()
    cursor = mydb.cursor(buffered=True)
    query = f"""SELECT {messageType} 
    FROM discord_server_messages
    WHERE server_guild_id = {guild_id}"""
    cursor.execute(query)
    myresult = cursor.fetchone()
    endConnection(mydb)
    return myresult[0] if myresult != None else None

def setServerMessage(guild_id:int, messageType:ServerMessagesEnum, message:str):
    mydb = connectToDatabase()
    cursor = mydb.cursor(buffered=True)
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
    finally:
        endConnectionWithCommit(mydb)


def getTodayBirthdays(guild_id:int):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT discord_user.discord_user_id, user_birthday.birth_date FROM user_birthday
JOIN discord_user ON user_birthday.user_id = discord_user.user_id
WHERE MONTH(birth_date) = MONTH(NOW())
AND DAY(birth_date) = DAY(NOW())
AND mentionable = 1;"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    endConnection(mydb)
    users:list[SimpleUserBirthday] = []
    for user in myresult:
        users.append(SimpleUserBirthday(user[0],user[1]))
    return users


def updateVoiceRecord(mydb, guild_id:int, discord_user:discord.Member, seconds:int):
    """Update the longest continuous voice call time for a member"""
    cursor = mydb.cursor()
    user_id = includeUser(mydb, discord_user, guild_id)
    try:
        query = f"""INSERT INTO user_records (user_id, server_guild_id, voice_time)
VALUES ({user_id}, {guild_id}, {seconds})
ON DUPLICATE KEY UPDATE voice_time = IF({seconds} > voice_time, {seconds}, voice_time);"""
        cursor.execute(query)
        mydb.commit()
        return True
    except mysql.connector.Error as err:
        logging.error(f"Database error occurred: {err}")
        return False


def getVoiceTime(guild_id:int, discord_user:discord.Member) -> int:
    """Retrieve the total recorded voice time in seconds for a member"""
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    user_id = includeUser(mydb, discord_user, guild_id)
    query = f"""SELECT voice_time FROM user_records
WHERE user_id = {user_id} AND server_guild_id = {guild_id};"""
    cursor.execute(query)
    myresult = cursor.fetchone()
    endConnection(mydb)
    return myresult[0] if myresult else 0


def getAllVoiceRecords(guild_id: int, limit: int = 10):
    """Retrieve top voice call records for a guild sorted by duration"""
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    query = f"""SELECT discord_user.discord_user_id, user_records.voice_time
FROM user_records
JOIN discord_user ON discord_user.user_id = user_records.user_id
WHERE user_records.server_guild_id = {guild_id}
ORDER BY user_records.voice_time DESC
LIMIT {limit};"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    endConnection(mydb)
    return [{'user_id': row[0], 'seconds': row[1]} for row in myresult]
