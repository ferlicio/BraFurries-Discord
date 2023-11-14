from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.trainers import ListTrainer
import sqlite3
import discord
import re


def initialKnowledge(chatBot, corpusScopes):
    corpus_trainer = ChatterBotCorpusTrainer(chatBot)
    if (corpusScopes != '' and corpusScopes != []):
        for corpusScope in corpusScopes:
            corpus_trainer.train(corpusScope)

def essentialLearning(chatBot, conversations):
    trainer = ListTrainer(chatBot)
    if conversations == []: 
        return print('conversations is empty')
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    for i in range(len(conversations)):
        prompts = conversations[i]
        responses = conversations[i+1] if i+1 < len(conversations) else []
        for prompt in prompts:
            for response in responses:
                if response != '' or prompt != '':
                    query = "SELECT * FROM statement WHERE in_response_to = ? AND text = ?"
                    cursor.execute(query, (prompt,response))
                    result = cursor.fetchone()
                    if result == None:                        
                        trainer.train([
                            prompt,
                            response
                        ])
    cursor.close()
    conn.close()

async def discordDeepLearning(self, reaction, user, DISCORD_INPUT):
    trainer = ListTrainer(self.chatBot)
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()

    if reaction.emoji == DISCORD_INPUT['negative']:
        user = await self.fetch_user(user.id)
        answeredMessage = None
        async for msg in reaction.message.channel.history(limit=10):
            if msg.id == reaction.message.id:
                answeredMessage = ''
            if msg.author.id == user.id and answeredMessage == '':
                answeredMessage = msg.content
                await user.send(f"ei, eu vi que você não gostou do jeito que respondi a essa mensagem:")
                await user.send(f"'{answeredMessage}'. Qual seria a resposta correta?")
                break

    if reaction.emoji == DISCORD_INPUT['positive']:
        answerToMessage = None
        async for msg in reaction.message.channel.history(limit=10):
            if msg.id == reaction.message.id:
                answerToMessage = msg.content
            if msg.author.id == user.id and answerToMessage != None:
                answeredMessage = msg.content
                query = "SELECT * FROM statement WHERE in_response_to = ? AND text = ?"
                cursor.execute(query, (answeredMessage, answerToMessage))
                result = cursor.fetchone()
                if result == None:
                    trainer.train([answeredMessage, answerToMessage])
                break

async def DMDiscordDeepLearning(self, message):
    trainer = ListTrainer(self.chatBot)
    if isinstance(message.channel, discord.DMChannel):
        async for msg in message.channel.history(limit=2):
            if msg.author.id == self.user.id and msg.content.__contains__("Qual seria a resposta correta?"):
                content = re.findall(r"'(.*?)'", msg.content)
                trainer.train([content[0], message.content])
                await message.add_reaction('🥰')
                await message.channel.send("Obrigado por me ensinar!")
                break

async def simpleLearning(self, message, response):
    trainer = ListTrainer(self.chatBot)
    trainer.train([message, response])

