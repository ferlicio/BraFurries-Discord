from message_services.discord.discord_service import run_discord_client
from message_services.telegram.telegram_service import run_telegram_client
import threading
import os

def run_Services(chatBot):
    threads = []
    if os.getenv('SOCIAL_MEDIAS').split(',').__contains__('Discord'):
        discordServer = threading.Thread(target=run_discord_client, args=(chatBot,))
        threads.append(discordServer)
    if os.getenv('SOCIAL_MEDIAS').split(',').__contains__('Telegram'):
        print('Telegram')
        telegramServer = threading.Thread(target=run_telegram_client, args=(chatBot,))
        threads.append(telegramServer)
        
    for thread in threads:
        thread.daemon = True
        thread.start()
    for thread in threads:
        thread.join()