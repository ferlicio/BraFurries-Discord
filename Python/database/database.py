from settings import BOT_DATABASE
import mysql.connector
import discord

def connectToDatabase():
    mydb = mysql.connector.connect(
        host=BOT_DATABASE['HOST'],
        user=BOT_DATABASE['USER'],
        password=BOT_DATABASE['PASSWORD'],
        database='coddy'
    )
    return mydb

def getConfig(guild:discord.Guild):
    mydb = connectToDatabase()
    cursor = mydb.cursor()
    #inicia o servidor no banco de dados
    query = f"""INSERT IGNORE INTO discord_servers (name, guild_id) 
VALUES ('{guild.name}', '{guild.id}');"""
    cursor.execute(query)
    query = f"""INSERT IGNORE INTO server_settings (server_guild_id, has_levels, has_economy) 
VALUES ('{guild.id}', '0', '0');"""
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
