from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from settings import TELEGRAM_BOT_USERNAME, TELEGRAM_ADMIN
from IA_Functions.terceiras.openAI import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from typing import Final
from database.database import *
import requests
import asyncio

app = None

#commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Olá, eu sou o Coddy! Se precisar de ajuda, digite /help')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('olha, eu não vou poder te ajudar muito, mas se quiser, pode falar com o meu criador @Titioderg')

async def registrar_local_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    local = " ".join(context.args)
    mydbAndCursor = startConnection()
    availableLocals = getAllLocals(mydbAndCursor[0])
    if local.upper() in [local_dict['locale_abbrev'] for local_dict in availableLocals]:
        result = includeLocale(mydbAndCursor[0],local.upper(), update.message.chat.username, availableLocals)
        endConnectionWithCommit(mydbAndCursor)
        if result:
            for locale in availableLocals:
                if locale['locale_abbrev'] == local.upper():
                    return await update.message.reply_text(f'você foi registrado em {locale["locale_name"]}!')
        else:
            return await update.message.reply_text(f'Não foi possível registrar você! você já está registrado em algum local?')
    else:
        endConnectionWithCommit(mydbAndCursor)
        availableLocalsResponse = ',\n'.join(f'{local["locale_abbrev"]} = {local["locale_name"]}' for local in availableLocals)
        return await update.message.reply_text(f'''você precisa fornecer um local existente para se cadastrar!
Você deve usar apenas a sigla do local, sem acentos ou espaços.\n
Os locais disponiveis são:\n {availableLocalsResponse}''')
    
async def agendar_prox_evento_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type:str = update.message.chat.type
    if (message_type == 'group'):
        return await update.message.reply_text(f'esse comando só pode ser usado em chats privados')
    else:
        eventos = getEventsByOwner()
        if len(eventos) == 0:
            return await update.message.reply_text(f'Você não tem nenhum evento cadastrado!')
        else:
            buttons = [InlineKeyboardButton(text=e["nome"], callback_data=e["id"]) for e in eventos]
            keyboard_inline = InlineKeyboardMarkup(inline_keyboard=[buttons])
            await update.message.reply_text('Por favor escolha o evento para reagendar:', reply_markup=keyboard_inline)
    
async def eventUpdate(update:Update, context:ContextTypes.DEFAULT_TYPE):
    pass

async def reagendar(update:Update, context:ContextTypes.DEFAULT_TYPE):
    pass



def warn_admins(user:str, message: str):
    requests.post(f'https://api.telegram.org/bot{os.getenv("TELEGRAM_TOKEN")}/sendMessage?chat_id={TELEGRAM_ADMIN}&text={user}: {message}')



#responses
async def handle_response(text: str) -> str:
    processed_text:str = text.lower()
    ##response:str = str(activeChatBot.generate_response(Statement(processed_text)))
    response:str = "oi" ##await retornaRespostaGPT(processed_text, 'titio', None, None, 'Telegram') 
    return response

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type:str = update.message.chat.type
    text:str = update.message.text
    print(f'{update.message.chat.id} - {update.message.chat.username}: "{text}"')
    if (message_type == 'group'):
        if TELEGRAM_BOT_USERNAME in text:
            new_text:str = text.replace(TELEGRAM_BOT_USERNAME, '').strip()
            response:str = await handle_response(new_text) 
        else:
            return
    else:
        response:str = await handle_response(text)
    print(f'Coddy: {response}')
    await update.message.reply_text(response)



#errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')




def run_telegram_client(chatBot):
    print('Running telegram client...')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    app.activeChatBot = chatBot
    #Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('registrar_local', registrar_local_command))

    app.add_handler(CommandHandler('agendar_prox_evento', registrar_local_command))
    app.add_handler(CallbackQueryHandler(eventUpdate))
    app.add_handler(MessageHandler(filters.Text(), reagendar))

    #Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #Errors
    app.add_error_handler(error)

    print('Polling...')
    loop.run_until_complete(app.run_polling(poll_interval=3, timeout=10))