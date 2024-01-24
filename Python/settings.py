from deprecated.ia_propria.learning.learning import initialKnowledge
from adapters.logic_adapters import NoRepeatAdapter
import fileinput
import random

#

# Configurações de ambiente
DEBUG = True
ENVIRONMENT = 'development'

# Configurações do bot
BOT_NAME = 'Coddy'
BOT_LANG = 'pt-br'
CHATBOT = True
SOCIAL_MEDIAS=['Discord','Telegram','Instagram']


# Configurações Discord
DISCORD_INTENTS = ['guilds', 'members', 'messages', 'reactions', 'typing', 'presences', 'message_content']
DISCORD_GUILD_ID = 753321055682035712
DISCORD_ADMINS = [167436511787220992]
DISCORD_VIP_ROLES_ID = [763974424130748468,953014617368567818]
DISCORD_HAS_VIP_CUSTOM_ROLES = True
DISCORD_VIP_CUSTOM_ROLE_PREFIX = 'FurVip ~'
DISCORD_HAS_ROLE_DIVISION = True
DISCORD_VIP_ROLE_DIVISION_START_ID = 980557856061403147
DISCORD_VIP_ROLE_DIVISION_END_ID = 1049638793382219776
DISCORD_TEST_CHANNEL = 1106970650406555659
DISCORD_IS_TESTING = False
DISCORD_BUMP_WARN = True
DISCORD_BUMP_WARNING_TIME = [9,23]
DISCORD_HAS_BUMP_REWARD = True
DISCORD_BOT_PREFIX = '>'
DISCORD_STAFF_COLORS = ['#fff000','#ac75ff','#6bfa60']
DISCORD_INPUT = {
    'positive': '👍',
    'negative': '👎',
}

# Configurações Instagram
INSTAGRAM_TOKEN = 'mytoken'

# Configurações do telegram
TELEGRAM_BOT_USERNAME = '@Coddy_The_PetBot'
TELEGRAM_ADMIN = '162630794'

# Configurações de email
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'myemail@example.com'
EMAIL_HOST_PASSWORD = 'mypassword'
EMAIL_USE_TLS = True





