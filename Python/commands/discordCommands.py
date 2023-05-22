from chatterbot.trainers import ListTrainer
from settings import DISCORD_ADMINS
from discord.ext import commands
import discord
import re



class DiscordCommands:
    def __init__(self, self_param, message):
        self.upperSelf = self_param
        self.chatBot = self_param.chatBot
        self.message = message

    async def say_as_bot(self):
        if self.message.content.startswith(f'>sayAs{self.chatBot.name}') and DISCORD_ADMINS.__contains__(self.message.author.id):
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

    async def insert_Training(self):
        if self.message.content.startswith('>insertTraining') and DISCORD_ADMINS.__contains__(self.message.author.id):
            await self.message.delete()
            if self.message.content[16] ==('[') and self.message.content.endswith(']'):
                trainer = ListTrainer(self.chatBot)
                conversation = self.message.content.replace('>insertTraining ', '')
                conversation = conversation.replace('[', '').replace(']', '')
                conversation = re.split((r',(?=(?:[^"]*"[^"]*")*[^"]*$)'), conversation)
                conversation = conversation.replace('"', '')
                for i in range(len(conversation)):
                    if conversation[i] != '' and i+1 < len(conversation):
                        trainer.train([conversation[i], conversation[i+1]])
                await self.message.author.send('obrigado pelo treinamento!')
            else:
                await self.message.author.send('Você precisa me enviar uma lista de conversas. \nExemplo: >insertTraining ["Olá", "Olá, tudo bem?"]')

async def run_discord_commands(chatBot, message):
    commands = DiscordCommands(chatBot, message)
    await commands.say_as_bot()
    await commands.insert_Training()