from message_services.discord_service import run_discord_client
import sys, codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
chatBot = {
    "name": "Coddy",
}


run_discord_client(chatBot)



