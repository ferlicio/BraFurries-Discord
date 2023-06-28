from message_services.discord.discord_service import run_discord_client
from message_services.telegram.telegram_service import run_telegram_client
from settings import SOCIAL_MEDIAS
import threading

def run_Services(chatBot):
    """ if SOCIAL_MEDIAS.__contains__('Discord'):
        run_discord_client(chatBot) """
    if SOCIAL_MEDIAS.__contains__('Telegram'):
        run_telegram_client(chatBot)
