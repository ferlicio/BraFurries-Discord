from discord_service import run_discord_client
from settings import SOCIAL_MEDIAS

def run_Services(chatBot):
    if SOCIAL_MEDIAS.__contains__('Discord'):
        run_discord_client(chatBot)
