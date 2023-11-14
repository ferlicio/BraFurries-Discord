from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from settings import TELEGRAM_TOKEN, TELEGRAM_BOT_USERNAME, TELEGRAM_ADMIN
from chatterbot.conversation import Statement
from IA_Functions.terceiras.openAI import *
from telegram import Update
from typing import Final
import requests
import asyncio

activeChatBot = None

#commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Olá, eu sou o Coddy! Se precisar de ajuda, digite /help')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('olha, eu não vou poder te ajudar muito, mas se quiser, pode falar com o meu criador @Titioderg')

def warn_admins(user:str, message: str):
    requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_ADMIN}&text={user}: {message}')

#responses
async def handle_response(text: str) -> str:
    processed_text:str = text.lower()
    ##response:str = str(activeChatBot.generate_response(Statement(processed_text)))
    response:str = await retornaRespostaGPT(processed_text, 'titio', None, None, 'Telegram') 
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
    global activeChatBot
    activeChatBot = chatBot
    print('Running telegram client...')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    #Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))

    #Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #Errors
    app.add_error_handler(error)

    print('Polling...')
    loop.run_until_complete(app.run_polling(poll_interval=3, timeout=10))