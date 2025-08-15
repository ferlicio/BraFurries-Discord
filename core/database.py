from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schemas.models.user import User, CustomRole, Warning
from schemas.enums.server_messages import ServerMessagesEnum
from schemas.models.user import SimpleUserBirthday
from mysql.connector.cursor import MySQLCursorAbstract
from core.utilities import snake_to_camel
from mysql.connector import pooling
import mysql.connector
from datetime import date, datetime
from typing import Union, Optional
from core.verifications import validate_birthdate
import discord
import os.path
import dotenv
from contextlib import contextmanager
import logging
import unicodedata
from settings import DISCORD_MEMBER_NOT_VERIFIED_ROLE

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
    pool_name="Discord", 
    pool_size=10, 
    pool_reset_session=False,
    **db_config
)

def normalize_text(text: Optional[str]) -> str:
    """Normalize text removing accents and special characters."""
    if text is None:
        return ""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

@contextmanager
def pooled_connection(buffered: bool = True):
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
            query = f"""INSERT IGNORE INTO community_discord (community_id, name, guild_id)
    VALUES ('{cursor.lastrowid}', '{guild.name}', '{guild.id}');"""
            cursor.execute(query)
        else:
            existInCommunities = False
            for community in communities:
                if community["name"] in guild.name:
                    existInCommunities = True
                    query = f"""INSERT IGNORE INTO community_discord (community_id, name, guild_id) 
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
                query = f"""INSERT IGNORE INTO community_discord (community_id, name, guild_id)
    VALUES ('{community[-1]["id"]}', '{guild.name}', '{guild.id}');"""
                cursor.execute(query)
        query = f"""INSERT IGNORE INTO config_server_settings (server_guild_id) 
    VALUES ('{guild.id}');"""
        cursor.execute(query)
        
        # Recupera as configurações do servidor
        cursor.execute("""
        SELECT COLUMN_NAME
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_NAME = 'config_server_settings'
        """)
        todas_colunas = cursor.fetchall()

        nomes = [
            row['COLUMN_NAME']
            for row in todas_colunas
            if row['COLUMN_NAME'] not in ('server_guild_id', 'id')
        ]

        extras = ", ".join(f"config_server_settings.{col} AS {snake_to_camel(col)}" for col in nomes)

        # 4) monta a query completa
        dynamic_query = f"""
            SELECT
            community_discord.name,
            community_discord.guild_id AS guildId
            {',' if extras else ''}{extras}
            FROM community_discord
            LEFT JOIN config_server_settings
            ON community_discord.guild_id = config_server_settings.server_guild_id
            WHERE community_discord.guild_id = %s
        """

        cursor.execute(dynamic_query, (guild.id,))
        config = cursor.fetchone()

        return config


def getCommandVisibleChannels(command_name: str) -> list[int]:
    """Mocked fetch of channel IDs where a command output is public.

    Parameters
    ----------
    command_name: str
        Name of the command to check.

    Returns
    -------
    list[int]
        Channel IDs in which the command should be visible to everyone.
    """
    # TODO: Replace this with a real database query
    return [753704857290014920, 852932512435011704]


def getLogConfig(guild_id: int, log_type: str):
    """Retrieve logging configuration for a given guild and log type."""
    with pooled_connection() as cursor:
        query = (
            "SELECT enabled, log_channel FROM config_logs "
            "WHERE server_guild_id = %s AND type = %s"
        )
        cursor.execute(query, (guild_id, log_type))
        return cursor.fetchone()


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
        FROM config_server_settings
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
            "SELECT user_id FROM user_discord WHERE discord_user_id = %s",
            (discord_user_id,)
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None




def includeUser(user: Union[discord.Member, discord.User, str], guildId: int = os.getenv("DISCORD_GUILD_ID"), approvedAt: datetime = None) -> int:
    """Ensure a user exists in the database and return the internal id."""
    with pooled_connection(True) as cursor:
        if isinstance(user, discord.Member):
            username = user.name
            display_name = user.display_name
            db_username = normalize_text(username)
            db_display_name = normalize_text(display_name)
            member_since = user.joined_at.strftime("%Y-%m-%d %H:%M:%S")
            approved = 0 if discord.utils.get(user.guild.roles, id=860453882323927060) in user.roles else 1
            cursor.execute(
                "SELECT user_id, display_name FROM user_discord WHERE discord_user_id = %s",
                (user.id,),
            )
            result = cursor.fetchone()
        elif isinstance(user, discord.User):
            username = user.name
            display_name = user.name
            db_username = normalize_text(username)
            db_display_name = normalize_text(display_name)
            member_since = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            approved = 0
            cursor.execute(
                "SELECT user_id, display_name FROM user_discord WHERE discord_user_id = %s",
                (user.id,),
            )
            result = cursor.fetchone()
        else:
            username = user
            display_name = user
            db_username = normalize_text(username)
            db_display_name = normalize_text(display_name)
            member_since = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            approved = 0
            cursor.execute(
                "SELECT user_id, display_name FROM user_telegram WHERE username = %s",
                (user,),
            )
            result = cursor.fetchone()

        approved_at_str = approvedAt.strftime("%Y-%m-%d %H:%M:%S") if approvedAt else None

        if result:
            user_id = result["user_id"]

            if result["display_name"] != db_display_name:
                table = "user_discord" if isinstance(user, discord.Member) else "user_telegram"
                cursor.execute(
                    f"UPDATE {table} SET display_name = %s WHERE user_id = %s",
                    (db_display_name, user_id),
                )
            cursor.execute("SELECT display_name FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row and row["display_name"] != db_display_name:
                cursor.execute("UPDATE users SET display_name = %s WHERE id = %s", (db_display_name, user_id))

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
                    "SELECT community_id FROM community_discord WHERE guild_id = %s",
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
                (db_display_name, db_username),
            )
        except Exception as e:
            raise Exception(
                "Nome de usuário inválido. Não é possivel aprovar membros com caracteres especiais."
            ) from e

        user_id = cursor.lastrowid
        if not user_id:
            cursor.execute("SELECT id FROM users WHERE username = %s", (db_username,))
            row = cursor.fetchone()
            user_id = row.get("id") if row else None

        cursor.execute(
            "SELECT community_id FROM community_discord WHERE guild_id = %s",
            (guildId,),
        )
        community_id = cursor.fetchone()["community_id"]
        cursor.execute(
            "INSERT INTO user_community_status (user_id, community_id, member_since, approved, approved_at, is_vip, banned)"
            " VALUES (%s, %s, %s, %s, %s, false, false)",
            (user_id, community_id, member_since, approved, approved_at_str),
        )

        try:
            if isinstance(user, discord.Member) or isinstance(user, discord.User):
                cursor.execute(
                    "INSERT INTO user_discord (user_id, discord_user_id, username, display_name) VALUES (%s, %s, %s, %s)",
                    (user_id, user.id, db_username, normalize_text(user.nick) if isinstance(user, discord.Member) and user.nick else db_display_name),
                )
            else:
                cursor.execute(
                    "INSERT IGNORE INTO user_telegram (user_id, username, display_name) VALUES (%s, %s, %s)",
                    (user_id, db_username, db_display_name),
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
        
def includeBirthday(
    guildId: int,
    date: date,
    user: discord.User,
    mentionable: bool,
    userId: int | None = None,
    registered: bool = False,
) -> bool:
    """Create or update a birthday entry for a user.

    The stored birth date is only changed when the provided ``date`` is later
    than the existing value and the record has not been verified yet.
    """

    validate_birthdate(date)

    user_id = userId if userId is not None else includeUser(user, guildId)

    with pooled_connection() as cursor:
        cursor.execute(
            "SELECT birth_date, mentionable, registered, verified FROM user_birthday WHERE user_id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        birthday = (
            {
                "date": row["birth_date"],
                "mentionable": row["mentionable"],
                "registered": row["registered"],
                "verified": row["verified"],
            }
            if row
            else None
        )

    if birthday:
        update_date = (
            birthday["verified"] == 0 and birthday["date"] != date and date > birthday["date"]
        )
        if (
            birthday["registered"] == 0
            or birthday["mentionable"] != mentionable
            or update_date
        ):
            try:
                with pooled_connection() as cursor:
                    cursor.execute(
                        "SELECT approved_at FROM user_community_status WHERE user_id = %s",
                        (user_id,),
                    )
                    approved_row = cursor.fetchone()
                    approved_at = approved_row["approved_at"] if approved_row else None
                    if approved_at and not isinstance(approved_at, datetime):
                        approved_at = datetime.strptime(str(approved_at), "%Y-%m-%d %H:%M:%S")

                    verified_sql = (
                        ", verified = 1"
                        if approved_at
                        and (datetime.now() - approved_at).days > 40
                        and date == birthday["date"]
                        else ""
                    )

                    set_clauses = []
                    params: list = []
                    if update_date:
                        set_clauses.append("birth_date = %s")
                        params.append(date)
                    set_clauses.append("mentionable = %s")
                    params.append(mentionable)
                    set_clauses.append("registered = 1")

                    query = (
                        f"UPDATE user_birthday SET {', '.join(set_clauses)}{verified_sql} WHERE user_id = %s"
                    )
                    params.append(user_id)
                    cursor.execute(query, tuple(params))
            except Exception as e:
                raise RuntimeError("Erro ao atualizar aniversário") from e

            if birthday["registered"] == 1:
                raise Exception("Changed Entry")
            return True

        if birthday["registered"] == 1:
            raise Exception("Duplicate entry")

        return False

    try:
        with pooled_connection() as cursor:
            cursor.execute(
                "INSERT INTO user_birthday (user_id, birth_date, verified, mentionable, registered) VALUES (%s, %s, FALSE, %s, %s)",
                (user_id, date, mentionable, registered),
            )
            return True
    except Exception as e:
        raise e

def getAllBirthdays():
    with pooled_connection() as cursor:
        query = f"""SELECT user_discord.discord_user_id, user_birthday.birth_date
    FROM user_discord
    JOIN user_birthday ON user_discord.user_id = user_birthday.user_id
    WHERE user_birthday.mentionable = 1;"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        #convertendo para uma lista de dicionários
        myresult = [{'user_id': i["discord_user_id"], 'birth_date': i["birth_date"]} for i in myresult]
        return myresult

def getUserInfo(user: Union[discord.Member, discord.User], guildId: int, userId: int = None) -> User :
    """Retrieve a user from the database. Optionally registers the user if missing."""
    user_id = includeUser(user, guildId)

    with pooled_connection() as cursor:
        query = (
            "SELECT user_discord.discord_user_id, user_discord.display_name, "
            "user_community_status.member_since, user_community_status.approved, "
            "user_community_status.approved_at, user_community_status.is_vip, "
            "user_community_status.is_partner, user_level.current_level, "
            "user_birthday.birth_date, user_birthday.verified, locale.locale_name, "
            "user_economy.bank_balance "
            "FROM users "
            "LEFT JOIN user_discord ON users.id = user_discord.user_id "
            "LEFT JOIN user_community_status ON users.id = user_community_status.user_id "
            "LEFT JOIN user_birthday ON user_birthday.user_id = users.id "
            "LEFT JOIN user_level ON user_level.user_id = users.id AND user_level.server_guild_id = %s "
            "LEFT JOIN user_locale ON user_locale.user_id = users.id "
            "LEFT JOIN locale ON locale.id = user_locale.locale_id "
            "LEFT JOIN user_warnings ON user_warnings.user_id = users.id "
            "LEFT JOIN user_economy ON user_economy.user_id = users.id AND user_economy.server_guild_id = %s "
            "WHERE user_discord.user_id = %s"
        )
        cursor.execute(query, (guildId, guildId, user_id))
        dbUser = cursor.fetchone()
        if not dbUser:
            return None

        userToReturn = User(
            id=user_id,
            discordId=user.id,
            username=user.name,
            displayName=getattr(user, 'display_name', user.name),
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
            "SELECT user_warnings.date, user_warnings.reason, user_warnings.expired "
            "FROM user_warnings JOIN users ON user_warnings.user_id = users.id "
            "WHERE users.id = %s",
            (user_id,),
        )
        warnings = cursor.fetchall() or []
        userToReturn.warnings = [Warning(i["date"], i["reason"], i["expired"]) for i in warnings]

        return userToReturn


def getAltAccounts(member: discord.Member | discord.User) -> list[int]:
    """Return a list of other Discord IDs linked to the same user."""
    user_id = getUserId(member.id)
    if user_id is None:
        return []

    with pooled_connection() as cursor:
        cursor.execute(
            "SELECT discord_user_id FROM user_discord WHERE user_id = %s AND discord_user_id <> %s",
            (user_id, member.id),
        )
        rows = cursor.fetchall() or []
        return [row["discord_user_id"] for row in rows]
    

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
        if events == []:
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

def admConnectTelegramAccount(discord_user:discord.Member, user_telegram:str):
    with pooled_connection() as cursor:
        #checa se o usuário já está cadastrado no banco de dados
        user_id = includeUser(discord_user)
        #checa se o user_telegram já está cadastrado no banco de dados
        query = f"""SELECT * FROM user_telegram WHERE user_id = '{user_id}';"""
        cursor.execute(query)
        myresult = cursor.fetchall()
        if myresult == []:
            try:
                query = f"""INSERT INTO user_telegram (user_id, username, display_name, banned)
            VALUES ('{user_id}', '{user_telegram}', '{discord_user.nick}', 'FALSE');"""
                cursor.execute(query)
                return True
            except:
                return False
        else:
            return True


def mergeDiscordAccounts(
    guild_id: int,
    member: Union[discord.Member, discord.User],
    existing_member: Union[discord.Member, discord.User],
) -> bool:
    """Link ``member`` to ``existing_member``'s user entry.

    Both parameters may be :class:`discord.Member` or :class:`discord.User`,
    allowing the association of accounts that are no longer in the server.

    All information tied to ``member`` is transferred so no data is lost. If
    duplicate rows exist in tables that should only contain one record per user,
    a simple precedence logic is applied to decide which information to keep:

    - ``user_community_status``: keep the oldest ``member_since`` entry
    - ``user_locale``: keep the locale of ``existing_member``
    - ``user_birthday``: keep the most recent ``birth_date``
    - ``user_records``: keep the highest ``voice_time`` and ``game_time``
    - ``user_custom_roles``: keep roles from ``existing_member``
    - ``user_economy``: bank balances are summed
    - ``user_level``: keep the row with highest ``total_xp``
    """

    with pooled_connection() as cursor:
        target_user_id = includeUser(existing_member, guild_id)
        current_user_id = getUserId(member.id)

        if current_user_id is None:
            try:
                cursor.execute(
                    "INSERT INTO user_discord (user_id, discord_user_id, username, display_name)"
                    " VALUES (%s, %s, %s, %s)",
                    (
                        target_user_id,
                        member.id,
                        normalize_text(member.name),
                        normalize_text(member.display_name if isinstance(member, discord.Member) else member.name),
                    ),
                )
                return True
            except Exception as e:
                logging.error(e)
                return False

        if current_user_id == target_user_id:
            return True

        try:
            # -- community status: keep the oldest member_since and merge approval data --
            cursor.execute(
                "SELECT id, user_id, member_since, approved, approved_at "
                "FROM user_community_status WHERE user_id IN (%s,%s) "
                "ORDER BY member_since ASC",
                (target_user_id, current_user_id),
            )
            status_rows = cursor.fetchall()
            if status_rows:
                keep = status_rows[0]
                # Determine final approved_at and approved values
                final_approved_at = keep["approved_at"]
                final_approved = keep["approved"]
                for row in status_rows[1:]:
                    if row["approved_at"] and (
                        final_approved_at is None or row["approved_at"] < final_approved_at
                    ):
                        final_approved_at = row["approved_at"]
                    if row["approved"]:
                        final_approved = 1
                if keep["user_id"] != target_user_id or keep["approved"] != final_approved or keep["approved_at"] != final_approved_at:
                    keep_id = keep.get("id")
                    if keep_id is not None:
                        cursor.execute(
                            "UPDATE user_community_status SET user_id=%s, approved=%s, approved_at=%s WHERE id=%s",
                            (target_user_id, final_approved, final_approved_at, keep_id),
                        )
                for row in status_rows[1:]:
                    row_id = row.get("id")
                    if row_id is not None:
                        cursor.execute(
                            "DELETE FROM user_community_status WHERE id=%s",
                            (row_id,),
                        )

            # -- locale: prefer existing member --
            cursor.execute(
                "SELECT id, user_id FROM user_locale WHERE user_id IN (%s,%s)",
                (target_user_id, current_user_id),
            )
            loc_rows = cursor.fetchall()
            target_loc = next((r for r in loc_rows if r["user_id"] == target_user_id), None)
            other_loc = next((r for r in loc_rows if r["user_id"] == current_user_id), None)
            if other_loc:
                other_id = other_loc.get("id")
                if target_loc:
                    if other_id is not None:
                        cursor.execute(
                            "DELETE FROM user_locale WHERE id=%s",
                            (other_id,),
                        )
                else:
                    if other_id is not None:
                        cursor.execute(
                            "UPDATE user_locale SET user_id=%s WHERE id=%s",
                            (target_user_id, other_id),
                        )

            # -- birthday: keep the newest date --
            cursor.execute(
                "SELECT * FROM user_birthday WHERE user_id IN (%s,%s) "
                "ORDER BY birth_date DESC",
                (target_user_id, current_user_id),
            )
            bd_rows = cursor.fetchall()
            if bd_rows:
                keep = bd_rows[0]
                if keep["user_id"] != target_user_id:
                    keep_id = keep.get("id")
                    if keep_id is not None:
                        cursor.execute(
                            "UPDATE user_birthday SET user_id=%s, birth_date=%s, "
                            "verified=%s, mentionable=%s, registered=%s WHERE id=%s",
                            (
                                target_user_id,
                                keep["birth_date"],
                                keep["verified"],
                                keep["mentionable"],
                                keep["registered"],
                                keep_id,
                            ),
                        )
                for row in bd_rows[1:]:
                    row_id = row.get("id")
                    if row_id is not None:
                        cursor.execute(
                            "DELETE FROM user_birthday WHERE id=%s",
                            (row_id,),
                        )

            # -- warnings --
            cursor.execute(
                "UPDATE user_warnings SET user_id=%s WHERE user_id=%s",
                (target_user_id, current_user_id),
            )

            # -- events --
            cursor.execute(
                "UPDATE events SET host_user_id=%s WHERE host_user_id=%s",
                (target_user_id, current_user_id),
            )

            # -- records: keep largest values per server --
            cursor.execute(
                "SELECT * FROM user_records WHERE user_id IN (%s,%s)",
                (target_user_id, current_user_id),
            )
            rec_rows = cursor.fetchall() or []
            rec_map = {}
            for row in rec_rows:
                key = row["server_guild_id"]
                if key not in rec_map:
                    rec_map[key] = row
                else:
                    old = rec_map[key]
                    voice_time = max(row.get("voice_time", 0), old.get("voice_time", 0))
                    if row.get("game_time", 0) > old.get("game_time", 0):
                        game_time = row.get("game_time")
                        game_name = row.get("game_name")
                    else:
                        game_time = old.get("game_time")
                        game_name = old.get("game_name")
                    rec_map[key] = {
                        "server_guild_id": key,
                        "voice_time": voice_time,
                        "game_time": game_time,
                        "game_name": game_name,
                    }
            for server_id, data in rec_map.items():
                cursor.execute(
                    """INSERT INTO user_records (user_id, server_guild_id, voice_time, game_time, game_name)
                    VALUES (%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        voice_time = IF(%s > voice_time, %s, voice_time),
                        game_time = IF(%s > game_time, %s, game_time),
                        game_name = IF(%s > game_time, %s, game_name)""",
                    (
                        target_user_id,
                        server_id,
                        data.get("voice_time"),
                        data.get("game_time"),
                        data.get("game_name"),
                        data.get("voice_time"),
                        data.get("voice_time"),
                        data.get("game_time"),
                        data.get("game_time"),
                        data.get("game_time"),
                        data.get("game_name"),
                    ),
                )
            cursor.execute(
                "DELETE FROM user_records WHERE user_id=%s",
                (current_user_id,),
            )

            # -- custom roles --
            cursor.execute(
                "SELECT id, user_id FROM user_custom_roles WHERE user_id IN (%s,%s)",
                (target_user_id, current_user_id),
            )
            role_rows = cursor.fetchall()
            target_role = next((r for r in role_rows if r["user_id"] == target_user_id), None)
            other_role = next((r for r in role_rows if r["user_id"] == current_user_id), None)
            if other_role:
                other_id = other_role.get("id")
                if target_role:
                    if other_id is not None:
                        cursor.execute(
                            "DELETE FROM user_custom_roles WHERE id=%s",
                            (other_id,),
                        )
                else:
                    if other_id is not None:
                        cursor.execute(
                            "UPDATE user_custom_roles SET user_id=%s WHERE id=%s",
                            (target_user_id, other_id),
                        )

            # -- economy: sum balances per server --
            cursor.execute(
                "SELECT * FROM user_economy WHERE user_id IN (%s,%s)",
                (target_user_id, current_user_id),
            )
            eco_rows = cursor.fetchall() or []
            eco_map = {}
            for row in eco_rows:
                key = row["server_guild_id"]
                if key in eco_map:
                    eco_map[key]["bank_balance"] += row.get("bank_balance", 0)
                else:
                    eco_map[key] = row
            for row in eco_map.values():
                cursor.execute(
                    """INSERT INTO user_economy (user_id, server_guild_id, bank_balance)
                        VALUES (%s,%s,%s)
                        ON DUPLICATE KEY UPDATE bank_balance=%s""",
                    (
                        target_user_id,
                        row["server_guild_id"],
                        row.get("bank_balance", 0),
                        row.get("bank_balance", 0),
                    ),
                )
            cursor.execute(
                "DELETE FROM user_economy WHERE user_id=%s",
                (current_user_id,),
            )

            # -- level: keep highest total_xp per server --
            cursor.execute(
                "SELECT * FROM user_level WHERE user_id IN (%s,%s)",
                (target_user_id, current_user_id),
            )
            lvl_rows = cursor.fetchall() or []
            lvl_map = {}
            for row in lvl_rows:
                key = row["server_guild_id"]
                if key not in lvl_map or row.get("total_xp", 0) > lvl_map[key].get("total_xp", 0):
                    lvl_map[key] = row
            for row in lvl_map.values():
                cursor.execute(
                    """INSERT INTO user_level (user_id, server_guild_id, total_xp, current_level)
                        VALUES (%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                            total_xp = IF(%s>total_xp, %s, total_xp),
                            current_level = IF(%s>current_level, %s, current_level)""",
                    (
                        target_user_id,
                        row["server_guild_id"],
                        row.get("total_xp"),
                        row.get("current_level"),
                        row.get("total_xp", 0),
                        row.get("total_xp", 0),
                        row.get("current_level", 0),
                        row.get("current_level", 0),
                    ),
                )
            cursor.execute(
                "DELETE FROM user_level WHERE user_id=%s",
                (current_user_id,),
            )

            # -- telegram account --
            cursor.execute(
                "UPDATE user_telegram SET user_id=%s WHERE user_id=%s",
                (target_user_id, current_user_id),
            )

            # -- final mapping and cleanup --
            cursor.execute(
                "UPDATE user_discord SET user_id=%s WHERE discord_user_id=%s",
                (target_user_id, member.id),
            )
            cursor.execute(
                "DELETE FROM user_birthday WHERE user_id=%s",
                (current_user_id,),
            )
            cursor.execute("DELETE FROM users WHERE id=%s", (current_user_id,))

            return True
        except Exception as e:
            logging.error(e)
            return False
    

async def assignTempRole(
    guild_id: int,
    discord_user: discord.Member,
    role_id: int | str,
    expiring_date: datetime,
    reason: str,
) -> bool:
    """Add a temporary role to ``discord_user`` and persist it in the database."""
    with pooled_connection() as cursor:
        cursor.execute(
            "SELECT id FROM community_discord WHERE guild_id = %s", (guild_id,)
        )
        row = cursor.fetchone()
        if not row:
            logging.error("Servidor %s não encontrado ao registrar temp role", guild_id)
            return False
        discord_community_id = row["id"]

        user_id = includeUser(discord_user, guild_id)
        cursor.execute("SELECT id FROM user_discord WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            logging.error(
                "Usuário %s não encontrado ao registrar temp role", discord_user.id
            )
            return False
        discord_user_id = row["id"]

        try:
            cursor.execute(
                "INSERT INTO user_temp_roles (disc_community_id, disc_user_id, role_id, expiring_date, reason)"
                " VALUES (%s, %s, %s, %s, %s)",
                (
                    discord_community_id,
                    discord_user_id,
                    int(role_id),
                    expiring_date,
                    reason,
                ),
            )
        except Exception as e:
            logging.error("Erro ao registrar temp role: %s", e)
            return False

    try:
        await discord_user.add_roles(discord_user.guild.get_role(int(role_id)))
    except Exception as e:
        logging.error("Erro ao adicionar cargo temporário: %s", e)
        return False

    return True
    
def getExpiringTempRoles(guild_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT id FROM community_discord WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        discord_community_id = cursor.fetchone()["id"]
        query = f"""SELECT user_temp_roles.id, user_temp_roles.role_id, user_discord.discord_user_id AS user_id FROM user_temp_roles
    JOIN user_discord ON user_temp_roles.disc_user_id = user_discord.id
    WHERE user_temp_roles.disc_community_id = '{discord_community_id}'
    AND user_temp_roles.expiring_date <= NOW();
        """
        cursor.execute(query)
        expiredTempRoles = cursor.fetchall()
        return expiredTempRoles

def deleteTempRole(tempRoleDBId:int):
    with pooled_connection() as cursor:
        try:
            query = f"""DELETE FROM user_temp_roles
        WHERE id = {tempRoleDBId}"""
            cursor.execute(query)
            return True
        except Exception as e:
            print(e)
            return False

def warnMember(guild_id:int, discord_user:discord.Member, reason:str):
    with pooled_connection() as cursor:
        user_id = includeUser(discord_user, guild_id)
        query = f"""SELECT community_id FROM community_discord WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        community_id = cursor.fetchone()["community_id"]
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            query = f"""INSERT INTO user_warnings (user_id, community_id, date, reason, expired)
            VALUES ('{user_id}', '{community_id}', '{date}', '{reason}', FALSE);"""
            cursor.execute(query)
            query = f"""SELECT COUNT(*) FROM user_warnings
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
        query = f"""SELECT community_id FROM community_discord WHERE guild_id = '{guild_id}';"""
        cursor.execute(query)
        community_id = cursor.fetchone()["community_id"]
        query = f"""SELECT date, reason, expired FROM user_warnings
    WHERE user_id = '{user_id}'
    AND community_id = '{community_id}';"""
        cursor.execute(query)
        results:list[Warning] = cursor.fetchall()
        warnings = [Warning(warning[0], warning[1], warning[2]) for warning in results]
        return warnings

def getStaffRoles(guild_id:int):
    with pooled_connection() as cursor:
        query = f"""SELECT staff_roles FROM config_server_settings WHERE server_guild_id = '{guild_id}';"""
        cursor.execute(query)
        return cursor.fetchall()

def registerUser(guild_id: int, discord_user: discord.Member, birthday: date, approved_date: date = None) -> bool:
    """Register a member in the database and save the birthday."""
    user_id = includeUser(
        discord_user,
        guild_id,
        datetime.now() if approved_date is None else approved_date,
    )

    if user_id is None:
        raise RuntimeError("Não foi possível registrar o usuário")

    try:
        birthdayRegistered = includeBirthday(
            guild_id,
            birthday,
            discord_user,
            False,
            user_id,
            False,
        )
    except Exception as e:
        raise RuntimeError("Erro ao registrar aniversário: " + str(e)) from e

    if not birthdayRegistered:
        raise RuntimeError("Não foi possível registrar o aniversário")

    return True

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
        query = f"""SELECT user_discord.discord_user_id, user_custom_roles.color, user_custom_roles.icon_id FROM user_custom_roles
    JOIN user_discord ON user_custom_roles.user_id = user_discord.user_id
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
        query = f"""SELECT user_discord.discord_user_id, user_birthday.birth_date FROM user_birthday
    JOIN user_discord ON user_birthday.user_id = user_discord.user_id
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
        query = f"""SELECT user_discord.discord_user_id, user_records.voice_time
    FROM user_records
    JOIN user_discord ON user_discord.user_id = user_records.user_id
    WHERE user_records.server_guild_id = {guild_id}
    ORDER BY user_records.voice_time DESC
    LIMIT {limit};"""
        cursor.execute(query)
        records = cursor.fetchall()
        return [{'user_id': row["discord_user_id"], 'seconds': row["voice_time"]} for row in records]


def updateGameRecord(guild_id:int, discord_user:discord.Member, seconds:int, game_name:str):
    """Update the longest continuous game time for a member and store the game name"""
    user_id = includeUser(discord_user, guild_id)
    with pooled_connection() as cursor:
        try:
            sql = """
            INSERT INTO user_records
              (user_id, server_guild_id, game_time, game_name)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              game_time  = IF(%s > game_time, %s,  game_time),
              game_name  = IF(%s > game_time, %s,  game_name)
            """
            params = (
                user_id, guild_id, seconds, game_name,  # INSERT
                seconds, seconds,                        # UPDATE game_time
                seconds, game_name                       # UPDATE game_name
            )
            cursor.execute(sql, params)
            return True
        except mysql.connector.Error as err:
            logging.error(f"Database error occurred: {err}")
            return False


def getGameTime(guild_id:int, discord_user:discord.Member) -> int:
    """Retrieve the total recorded game time in seconds for a member"""
    user_id = includeUser(discord_user, guild_id)
    with pooled_connection() as cursor:
        query = f"""SELECT game_time FROM user_records
    WHERE user_id = {user_id} AND server_guild_id = {guild_id};"""
        cursor.execute(query)
        myresult = cursor.fetchone()
        return myresult[0] if myresult else 0


def getAllGameRecords(guild_id: int, limit: int = 10, blacklist: list[str] = None):
    """Retrieve top game time records for a guild sorted by duration"""
    with pooled_connection() as cursor:
        exclusion = ""
        if blacklist:
            names = "', '".join(name.replace("'", "\\'") for name in blacklist)
            exclusion = f" AND user_records.game_name NOT IN ('{names}')"
        query = f"""SELECT user_discord.discord_user_id, user_records.game_time, user_records.game_name
    FROM user_records
    JOIN user_discord ON user_discord.user_id = user_records.user_id
    WHERE user_records.server_guild_id = {guild_id}{exclusion}
    ORDER BY user_records.game_time DESC
    LIMIT {limit};"""
        cursor.execute(query)
        records = cursor.fetchall()
        return [{'user_id': row["discord_user_id"], 'seconds': row["game_time"], 'game': row["game_name"]} for row in records]


def getBlacklistedGames(guild_id: int) -> list[str]:
    """Retrieve all blacklisted games for a guild"""
    with pooled_connection() as cursor:
        query = f"""SELECT game_name FROM blacklisted_games
    WHERE server_guild_id = {guild_id};"""
        cursor.execute(query)
        rows = cursor.fetchall()
        return [row["game_name"] for row in rows]


def addGameToBlacklist(guild_id: int, game_name: str) -> bool:
    """Add a game to the blacklist for a guild"""
    with pooled_connection() as cursor:
        try:
            query = """INSERT IGNORE INTO blacklisted_games (server_guild_id, game_name)
    VALUES (%s, %s);"""
            cursor.execute(query, (guild_id, game_name))
            return True
        except mysql.connector.Error as err:
            logging.error(f"Database error occurred: {err}")
            return False


def getVoiceRecordPosition(guild_id: int, discord_user: discord.Member | discord.User):
    """Return a member's voice record rank and value in seconds."""
    user_id = includeUser(discord_user, guild_id)
    sql = """
    SELECT voice_time, rank
    FROM (
      SELECT
        user_id,
        voice_time,
        RANK() OVER (
          PARTITION BY server_guild_id
          ORDER BY voice_time DESC
        ) AS rank
      FROM user_records
      WHERE server_guild_id = %s
    ) AS ranked
    WHERE user_id = %s
    """
    with pooled_connection() as cursor:
        cursor.execute(sql, (guild_id, user_id))
        row = cursor.fetchone()
        if not row or row["voice_time"] is None:
            return None
        return {"rank": row["rank"], "seconds": row["voice_time"]}


def getGameRecordPosition(
    guild_id: int,
    discord_user: discord.Member | discord.User,
    user_id: int | None = None,
):
    """Return a member's game record rank, value in seconds and game name."""
    user_id = includeUser(discord_user, guild_id) if user_id is None else user_id
    sql = """
    SELECT
      ur.game_time,
      ur.game_name,
      (
        SELECT COUNT(*) + 1
          FROM user_records u2
         WHERE u2.server_guild_id = ur.server_guild_id
           AND u2.game_time > ur.game_time
           AND NOT EXISTS (
             SELECT 1
               FROM blacklisted_games bg2
              WHERE bg2.server_guild_id = u2.server_guild_id
                AND bg2.game_name     = u2.game_name
           )
      ) AS rank
    FROM user_records ur
    WHERE ur.server_guild_id = %s
      AND ur.user_id        = %s
      AND NOT EXISTS (
        SELECT 1
          FROM blacklisted_games bg
         WHERE bg.server_guild_id = ur.server_guild_id
           AND bg.game_name       = ur.game_name
      )
    """
    with pooled_connection() as cursor:
        cursor.execute(sql, (guild_id, user_id))
        row = cursor.fetchone()
        if not row or row["game_time"] is None:
            return None
        return {
            "rank":    row["rank"],
            "seconds": row["game_time"],
            "game":    row["game_name"]
        }


def getProfileData(guild_id: int, user: discord.Member | discord.User):
    """Return a :class:`User` object with all profile information for the ``/perfil`` command using a single connection."""

    user_id = includeUser(user, guild_id)

    with pooled_connection() as cursor:
        info_query = (
            "SELECT user_discord.discord_user_id, user_discord.display_name, "
            "user_community_status.member_since, user_community_status.approved, "
            "user_community_status.approved_at, user_community_status.is_vip, "
            "user_community_status.is_partner, user_level.current_level, "
            "user_birthday.birth_date, user_birthday.verified, locale.locale_name, "
            "user_economy.bank_balance "
            "FROM users "
            "LEFT JOIN user_discord ON users.id = user_discord.user_id "
            "LEFT JOIN user_community_status ON users.id = user_community_status.user_id "
            "LEFT JOIN user_birthday ON user_birthday.user_id = users.id "
            "LEFT JOIN user_level ON user_level.user_id = users.id AND user_level.server_guild_id = %s "
            "LEFT JOIN user_locale ON user_locale.user_id = users.id "
            "LEFT JOIN locale ON locale.id = user_locale.locale_id "
            "LEFT JOIN user_economy ON user_economy.user_id = users.id AND user_economy.server_guild_id = %s "
            "WHERE user_discord.user_id = %s"
        )

        cursor.execute(info_query, (guild_id, guild_id, user_id))
        db_user = cursor.fetchone()
        if not db_user:
            return None

        approved = db_user["approved"]
        if isinstance(user, discord.Member):
            has_unverified_role = any(
                role.id == DISCORD_MEMBER_NOT_VERIFIED_ROLE for role in user.roles
            )
            approved = not has_unverified_role
            if approved != db_user["approved"]:
                cursor.execute(
                    "UPDATE user_community_status SET approved = %s WHERE user_id = %s",
                    (1 if approved else 0, user_id),
                )

        profile = User(
            id=user_id,
            discordId=user.id,
            username=user.name,
            displayName=getattr(user, "display_name", user.name),
            memberSince=db_user["member_since"],
            approved=approved,
            approvedAt=db_user["approved_at"],
            isVip=db_user["is_vip"],
            isPartner=db_user["is_partner"],
            level=db_user["current_level"],
            birthday=db_user["birth_date"],
            birthdayVerified=db_user["verified"],
            locale=db_user["locale_name"],
            coins=db_user["bank_balance"],
            warnings=[],
            inventory=[],
            staffOf=[],
        )

        cursor.execute(
            "SELECT user_warnings.date, user_warnings.reason, user_warnings.expired "
            "FROM user_warnings JOIN users ON user_warnings.user_id = users.id "
            "WHERE users.id = %s",
            (user_id,),
        )
        warnings = cursor.fetchall() or []
        profile.warnings = [Warning(i["date"], i["reason"], i["expired"]) for i in warnings]

        cursor.execute(
            "SELECT discord_user_id FROM user_discord WHERE user_id = %s AND discord_user_id <> %s",
            (user_id, user.id),
        )
        alt_rows = cursor.fetchall() or []
        profile.altAccounts = [row["discord_user_id"] for row in alt_rows]

        voice_sql = (
            "SELECT voice_time, rank "
            "FROM ("
            "  SELECT user_id, voice_time, "
            "    RANK() OVER (PARTITION BY server_guild_id ORDER BY voice_time DESC) AS rank "
            "  FROM user_records "
            "  WHERE server_guild_id = %s"
            ") AS ranked "
            "WHERE user_id = %s"
        )
        cursor.execute(voice_sql, (guild_id, user_id))
        row = cursor.fetchone()
        profile.voiceRecord = (
            {"rank": row["rank"], "seconds": row["voice_time"]} if row and row["voice_time"] is not None else None
        )

        game_sql = (
            "SELECT ur.game_time, ur.game_name, ("
            "    SELECT COUNT(*) + 1"
            "      FROM user_records u2"
            "     WHERE u2.server_guild_id = ur.server_guild_id"
            "       AND u2.game_time > ur.game_time"
            "       AND NOT EXISTS ("
            "         SELECT 1"
            "           FROM blacklisted_games bg2"
            "          WHERE bg2.server_guild_id = u2.server_guild_id"
            "            AND bg2.game_name     = u2.game_name"
            "       )"
            ") AS rank "
            "FROM user_records ur "
            "WHERE ur.server_guild_id = %s "
            "  AND ur.user_id        = %s "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM blacklisted_games bg "
            "    WHERE bg.server_guild_id = ur.server_guild_id "
            "      AND bg.game_name       = ur.game_name"
            "  )"
        )
        cursor.execute(game_sql, (guild_id, user_id))
        row = cursor.fetchone()
        if row and row["game_time"] is not None:
            profile.gameRecord = {"rank": row["rank"], "seconds": row["game_time"], "game": row["game_name"]}
        else:
            profile.gameRecord = None

        return profile