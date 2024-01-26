from discord.ext import commands
import discord
import re
import os


class DiscordCommands:
    def __init__(self, self_param, message):
        self.upperSelf = self_param
        self.chatBot = self_param.chatBot
        self.message = message

    async def say_as_bot(self):
        if self.message.content.startswith(f'>sayAs{self.chatBot.name}') and os.getenv('DISCORD_ADMINS').__contains__(self.message.author.id):
            await self.message.delete()
            if self.message.content.__contains__('<#'):
                channel_id = self.message.content.split('<#')[1].split('>')[0]
                channel = self.upperSelf.get_channel(int(channel_id))
                if channel is not None:
                    await channel.send(self.message.content.replace(f'>sayAs{self.chatBot.name}', '').replace(f'<#{channel_id}>', ''))
                else:
                    print(f"Canal de ID {channel_id} não encontrado.")
            else: 
                await self.message.user.send('Você precisa mencionar um canal para eu falar. \nExemplo: >sayAsCoddy <#123456789> Olá, eu sou o Coddy!')


async def run_discord_commands(chatBot, message):
    commands = DiscordCommands(chatBot, message)
    await commands.say_as_bot()
    await commands.insert_Training()