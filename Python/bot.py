from message_services.message_service import run_Services
from database.database import *
import asyncio, sys, codecs
import os

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
chatBot = {
    "name": "Coddy",
}


startDatabase()
run_Services(chatBot)

