from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update, KeyboardButton, Message
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, Application, ContextTypes
from database.database import endConnection, endConnectionWithCommit, getEventsByOwner, rescheduleEventDate, scheduleNextEventDate, startConnection
from datetime import datetime
import re


async def agendarEvento(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user = update.message.chat.username
    if update.message.chat.username == 'Titioderg' and len(context.args) > 0:
        user = context.args[0]
    mydbAndCursor = startConnection()
    events = getEventsByOwner(mydbAndCursor[0],user)
    endConnection(mydbAndCursor)
    if len(events) == 0:
        return await update.message.reply_text(f'Você não tem nenhum evento cadastrado!')
    buttons = [[InlineKeyboardButton(text=e["event_name"], callback_data=e["id"])] for e in events]
    keyboard_inline = InlineKeyboardMarkup(inline_keyboard=buttons)
    context.user_data["events"] = events
    await update.message.reply_text('Por favor escolha o evento para reagendar:', reply_markup=keyboard_inline)


async def eventUpdate(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(query.id)
    evento_id = int(query.data)
    event = next(e for e in context.user_data["events"] if e["id"] == evento_id)
    context.user_data["event"] = event
    event_description = f'''*{event["event_name"]}*
*Data*: {event["starting_datetime"].strftime("%d/%m/%Y") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") 
    else f"{event['starting_datetime'].strftime('%d')} a {event['ending_datetime'].strftime('%d/%m/%Y')}"}{" - das "+event["starting_datetime"].strftime("%H:%M")+" às "+event["ending_datetime"].strftime("%H:%M") if event["starting_datetime"].strftime("%d/%m/%Y") == event["ending_datetime"].strftime("%d/%m/%Y") else ''}
*Local*: {event["city"]}, {event["state_abbrev"]}
*Endereço*: {event["address"]}'''
    if event['group_chat_link']!=None: event_description += f"""
*Chat do evento*: {event['group_chat_link']}"""
    if event['website']!=None: event_description += f"""
*Site*: {event['website']}""" 
    event_description += f"""*Preço*: {"De R$"+str(f"{event['price']:.2f}").replace('.',',')+" a "+"R${:,.2f}".format(event['max_price']).replace(",", "x").replace(".", ",").replace("x", ".") if (event['price']!=0 and event['max_price']!=0) 
        else f'R$'+str(f"{event['price']:.2f}").replace('.',',') if event['max_price']==0 and event['price']!=0 else 'Gratuito'}"""
    if event['description']!=None: event_description += f"""\n\n_{event['description']}_ """
    await query.edit_message_text(text=f'''{event_description}''', parse_mode='Markdown')
    if event['ending_datetime'] > datetime.now():
        buttons = [[KeyboardButton("Reagendar"),KeyboardButton("Cancelar")],[]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
        return await context.bot.send_message(chat_id=query.message.chat_id, text=f'Este evento ainda não foi finalizado. O que você deseja fazer?', reply_markup=reply_markup)
    else: 
        return await context.bot.send_message(chat_id=query.message.chat_id, text=f'Digite a nova data no formato _DD/MM/YYYY_:', reply_markup=reply_markup)


async def handleEventDateChange(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if 'event' not in context.user_data or not context.user_data['event']: return
    try: data = datetime.strptime(update.message.text, "%d/%m/%Y")
    except ValueError:
        return await context.bot.send_message(chat_id=update.message.chat_id, text='Data inválida! Você informou uma data no formato "DD/MM/AAAA"?')
    # Atualizar a data do evento no banco de dados
    mydbAndCursor = startConnection()
    event = context.user_data["event"]
    if context.user_data['reagendandoEvento']:
        result = rescheduleEventDate(mydbAndCursor[0], event['event_name'], data, update.message.chat.username)
        context.user_data.pop("reagendandoEvento")
    else: result = scheduleNextEventDate(mydbAndCursor[0], event['event_name'], data, update.message.chat.username)
    endConnectionWithCommit(mydbAndCursor)
    context.user_data.pop("event")
    context.user_data.pop("events")
    if result == True:
        return await context.bot.send_message(chat_id=update.message.chat_id, text=f'O evento *{event["event_name"]}* foi agendado para {data} com sucesso!', parse_mode='Markdown')

async def reagendarEvento(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if 'event' not in context.user_data or not context.user_data['event']: return
    if update.message.text == 'Cancelar': 
        context.user_data.pop("event")
        context.user_data.pop("events") 
        return await context.bot.send_message(chat_id=update.message.chat_id, text=f'Operação cancelada!')
    else:
        context.user_data['reagendandoEvento'] = True
        return await context.bot.send_message(chat_id=update.message.chat_id, text=f'Digite a nova data no formato _DD/MM/YYYY_:', parse_mode='Markdown')


def main() -> None:
    app = Application.builder().token('6227842110:AAGIY9SeyEcnhu80ftA5dJk70ieCyt2Y_s8').build()

    app.add_handler(CommandHandler("agendar_evento", agendarEvento))
    app.add_handler(CallbackQueryHandler(eventUpdate))
    app.add_handler(MessageHandler(filters.Regex('^\d{2}/\d{2}/\d{4}$'), handleEventDateChange))
    app.add_handler(MessageHandler(filters.Regex('^(Reagendar|Cancelar)$'), reagendarEvento))

    app.run_polling()

if __name__ == '__main__':
    main()
 