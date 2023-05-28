import fileinput
from learning.learning import initialKnowledge

# Configurações de ambiente
DEBUG = True
ENVIRONMENT = 'development'

# Configurações do bot
BOT_NAME = 'Coddy'
BOT_LANG = 'pt-br'
CHATBOT = True
INITIALIZED = True
DEFAULT_RESPONSE = 'Desculpa, eu não entendi... nem sei o que te responder :c'
LOGIC_ADAPTERS = [
    'chatterbot.logic.MathematicalEvaluation',
    {
        "import_path": "chatterbot.logic.BestMatch",
        'default_response': DEFAULT_RESPONSE,
        'maximum_similarity_threshold': 0.70
    }
]
STORAGE_ADAPTER = 'chatterbot.storage.SQLStorageAdapter'
SOCIAL_MEDIAS=['Discord']
COMMUNITY_LEARNING = False


# Configurações Discord
DISCORD_TOKEN = 'MTEwNjc1NjI4MTQyMDc1OTA1MQ.GXs7c3.k4fU3HxMKGiGSlD8JpuUX3vJJckEUDH7jQZKAc'
DISCORD_INTENTS = ['guilds', 'members', 'messages', 'reactions', 'typing', 'presences','message_content']
DISCORD_ADMINS = [167436511787220992]
MODERATORS_ROLES = [961314680264081450]
DISCORD_TEST_CHANNEL = 1106970650406555659
DISCORD_IS_TESTING = True
DISCORD_BOT_PREFIX = '>'
DISCORD_INPUT = {
    'positive': '👍',
    'negative': '👎',
}

# Configurações Instagram
TOKEN = 'mytoken'

# Configurações de API externa
EXTERNAL_API_KEY = 'myapikey'
EXTERNAL_API_URL = 'https://api.example.com'

# Configurações de email
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'myemail@example.com'
EMAIL_HOST_PASSWORD = 'mypassword'
EMAIL_USE_TLS = True

# base de dados de inicialização corpus
corpus = {
    'pt-br': 'chatterbot.corpus.portuguese',
    'en-us': 'chatterbot.corpus.english'
}


def initializeProject(chatBot):
    if (not INITIALIZED):
        print('initializing...')
        initialKnowledge(chatBot,[corpus[BOT_LANG]])
        for linha in fileinput.input('settings.py', inplace=True):
            if (linha.strip() == 'INITIALIZED = False'):
                print('INITIALIZED = True')
            else:
                print(linha, end='')
        
        print('initialized!')