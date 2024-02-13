from message_services.message_service import run_Services
from api.api_services import run_api
from database.database import *
import sys, codecs
import threading

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
chatBot = {
    "name": "Coddy",
}


startDatabase()

threads = []
threads.append(threading.Thread(target=run_Services, args=(chatBot,)))
threads.append(threading.Thread(target=run_api))

for thread in threads:
    thread.daemon = True
    thread.start()
for thread in threads:
    thread.join()
