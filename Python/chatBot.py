from chatterbot import ChatBot
from IA_Functions.propria.learning.learning import essentialLearning
from IA_Functions.propria.learning.conversations import conversations_with_variables
from settings import BOT_NAME, LOGIC_ADAPTERS, STORAGE_ADAPTER, initializeProject
from message_services.message_service import run_Services
import asyncio, sys, codecs

chatBot = ChatBot(
    name=BOT_NAME,
    read_only=True,
    storage_adapter=STORAGE_ADAPTER,
    logic_adapters=LOGIC_ADAPTERS
)

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

initializeProject(chatBot)
essentialLearning(chatBot,conversations_with_variables())
run_Services(chatBot)

""" while inputChat != '/quit':
    inputChat = input('Você: ')
    if inputChat != '/quit': 
        response = chatBot.get_response(inputChat)
        print(response)
        deepLearning(chatBot, '', inputChat, response) """