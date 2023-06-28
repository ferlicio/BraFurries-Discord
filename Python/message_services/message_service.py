from message_services.discord.discord_service import run_discord_client
from message_services.telegram.telegram_service import run_telegram_client
from settings import SOCIAL_MEDIAS
import threading

def run_Services(chatBot):
    threads = []
    if SOCIAL_MEDIAS.__contains__('Discord'):
        discordServer = threading.Thread(target=run_discord_client, args=(chatBot,))
        threads.append(discordServer)
    if SOCIAL_MEDIAS.__contains__('Telegram'):
        telegramServer = threading.Thread(target=run_telegram_client, args=(chatBot,))
        threads.append(telegramServer)
        
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()