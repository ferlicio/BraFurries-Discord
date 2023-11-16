from settings import BOT_DATABASE
import mysql.connector
import discord
from models.cities import cities
from datetime import date

class Config:
    def __init__(self, config_dict):
        self.config_dict = config_dict
        for key, value in config_dict.items():
            setattr(self, key, value)


def connectToDatabase():
    mydb = mysql.connector.connect(
        host=BOT_DATABASE['HOST'],
        user=BOT_DATABASE['USER'],
        password=BOT_DATABASE['PASSWORD'],
        database='coddy'
    )
    return mydb

def startConnection():
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    return [mydb, cursor]

def endConnection(mydbAndCursor:list):
    mydb = mydbAndCursor[0]
    cursor = mydbAndCursor[1]
    mydb.close()
    cursor.close()

def endConnectionWithCommit(mydbAndCursor:list):
    mydb = mydbAndCursor[0]
    mydb.commit()
    endConnection(mydbAndCursor)


def startDatabase():
    mydb = connectToDatabase()
    cursor = mydb.cursor()

    for abbrev, city in cities.items():
        query = f"""INSERT IGNORE INTO locale (locale_abbrev, locale_name) VALUES ('{abbrev}','{city}');"""
        cursor.execute(query)
    mydb.commit()

def getConfig(guild:discord.Guild):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    #inicia o servidor no banco de dados
    query = f"""INSERT IGNORE INTO discord_servers (name, guild_id) 
VALUES ('{guild.name}', '{guild.id}');"""
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

    column_names = ['name', 'guild_id']
    for column in todas_colunas:
        column_names.append(column[0])
    config = dict(zip(column_names, myresult[0]))

    print(config)
    cursor.close()
    mydb.close()
    return config


def getAllLocals(mydb):
    cursor = mydb.cursor()
    query = f"""SELECT * FROM locale"""
    cursor.execute(query)

    myResult = cursor.fetchall()
    locals_list = [{'id': local[0], 'locale_abbrev': local[1], 'locale_name': local[2]} for local in myResult]
    return locals_list

def includeUser(mydb,user:discord.User):
    cursor = mydb.cursor()
    query = f"""INSERT IGNORE INTO users (user_id, username)
VALUES ('{user.id}', '{user.name}');"""
    cursor.execute(query)

def includeLocale(mydb, abbrev:str, user:discord.User, availableLocals:list):
    includeUser(mydb, user)
    cursor = mydb.cursor()
    for local in availableLocals:
        if local['locale_abbrev'] == abbrev:
            query = f"""INSERT IGNORE INTO user_locale (user_id, locale_id) VALUES ('{user.id}','{local['id']}');"""
            cursor.execute(query)
            return True
    return False

def getByLocale(mydb, abbrev:str, availableLocals:list):
    cursor = mydb.cursor()
    for local in availableLocals:
        if local['locale_abbrev'] == abbrev:
            query = f"""SELECT users.username
FROM users
JOIN user_locale ON users.user_id = user_locale.user_id
JOIN locale ON user_locale.locale_id = locale.id
WHERE locale.locale_abbrev = '{abbrev}';"""
            cursor.execute(query)
            myresult = cursor.fetchall()
            #convertendo para lista
            myresult = [i[0] for i in myresult]
            return myresult
        
def includeBirthday(mydb, date:date, user:discord.User):
    includeUser(mydb, user)
    cursor = mydb.cursor()
    query = f"""INSERT IGNORE INTO user_birthday (user_id, birth_date) VALUES ('{user.id}','{date}');"""
    cursor.execute(query)
    return True

def getAllBirthdays(mydb):
    cursor = mydb.cursor()
    query = f"""SELECT users.username, user_birthday.birth_date
FROM users
JOIN user_birthday ON users.user_id = user_birthday.user_id;"""
    cursor.execute(query)
    myresult = cursor.fetchall()
    #convertendo para uma lista de dicionários
    myresult = [{'username': i[0], 'birth_date': i[1]} for i in myresult]
    return myresult