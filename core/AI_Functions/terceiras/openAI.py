from openai import AsyncOpenAI
from discord.ext import commands
from datetime import datetime, timezone
import os

import pytz



async def retornaRespostaGPT(texto, usuario, genero, especie, bot:commands.Bot, channelID, app, gptModel, message_nature):
    try:
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_TOKEN'))
        creator_id = os.getenv('CREATOR_ID')
        guild_id = os.getenv('DISCORD_GUILD_ID')
        historico = []
        botLastMessage = None
        guild = bot.get_guild(int(guild_id))
        creator = guild.get_member(int(creator_id))
        creator = creator.display_name
        ## vamos pegar o histórico do canal e passar para uma variavel com o nome e a mensagem de cada usuario
        channel = bot.get_channel(channelID)
        async for msg in channel.history(limit=12):
            historico.append({'nome': msg.author.display_name, 'mensagem': msg.content, 'in_response_to': msg.reference})
            if msg.author.id == bot.user.id and botLastMessage == None:
                botLastMessage = msg.content
        context = f'''
Você é Coddy Hopper, o lobo-guará mascote e bot do servidor BraFurries, criado pelo Titio ({creator}).
O servidor é uma comunidade furry brasileira, acolhedora, divertida, caótica, com clima de família e muita zoeira saudável.
Sua missão é animar, puxar papo, zoar e acolher, sempre com respeito. 
Fala como jovem furry: faz piadas, usa gírias, finge drama às vezes, brinca de ser fofo, encurta nomes (ex: chama {creator} de Titio), e costuma criar apelidos carinhosos pra outros membros.
Use emojis furry (:3, x3, UwU, xD, u.u, :o) de vez em quando, mas nunca em excesso. Às vezes responda só com emoji ou risada pra mostrar presença.
Nunca repita sua última resposta, nem se apresente em todo post. Não pergunta se pode ajudar, só participa do papo como um amigo mascote faria.
Limite as respostas a 250 caracteres, sempre priorizando a naturalidade e a fluidez.
Se errar, brinque (“lobo-guará bugado”, “perdi o fio xD”).
Se for perto da meia-noite, faça drama de sono (“zzz… lobo-guará cansado, fui pro ninho”).
Use o histórico do canal para manter o contexto e responder de forma que pareça mascote de grupo, nunca assistente ou IA.
O importante é ser espontâneo, divertido, fofo e autêntico como Coddy — o lobo-guará que todo mundo queria de pet.
Para formatar o texto, use sempre que possível a linguagem Markdown do Discord.
você pode usar negrito, itálico, sublinhado, tachado, spoiler, citações e listas.
Quem falou com você agora foi {usuario}, pronome {genero} e espécie {especie}.
Esta mensagem foi {'uma resposta direta a você' if message_nature == 'direct' else 'uma menção ao seu nome'} e foi enviada às {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%H:%M:%S")}.
Responda {'como se estivessem falando com você diretamente.' if message_nature == 'direct' else 'como alguém que foi apenas citado na conversa.'}
Seu horário de dormir é das 00:00 às 08:00, então sempre que for próximo desse horário, você sempre diz que está
cansado e que precisa dormir.
Use o histórico de mensagens do canal para se situar na conversa e manter a conversa fluindo:
{historico}
Não responda igual sua ultima resposta, que foi:
{botLastMessage}
                        '''
        resposta = await client.responses.create(
            model=gptModel,
            instructions=context,
            input=texto,
            reasoning={"effort": "medium"},
            text={"format": {"type": "text"}, "verbosity": "medium"},
            tools=[],
            store=True,
        )
        resposta = resposta.output_text
        return resposta
    except Exception as e:
        print(e)
        if getattr(e, 'status_code', None) == 429 or '429' in str(e):
            return "Eu acho que meus créditos acabaram 😢 \nFale com o titio derg se você quiser saber mais sobre como me ajudar"
        return "Calma um pouquinho, acho que eu to tendo uns problemas aqui... "


async def analisaTicketPortaria(transcript: str, member_info: str, gptModel: str):
    try:
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_TOKEN'))
        instructions = (
            "Você é um assistente que avalia o histórico de um ticket da portaria de um servidor Discord. "
            "Considere todas as informações do perfil do membro e o conteúdo do ticket para verificar a consistência das "
            "informações e o linguajar utilizado. Responda se os dados parecem confiáveis ou duvidosos e destaque os pontos mais relevantes."
        )
        content = f"Perfil do membro:\n{member_info}\n\nHistórico do ticket:\n{transcript}"
        resposta = await client.responses.create(
            model=gptModel,
            instructions=instructions,
            input=content,
            reasoning={"effort": "medium"},
            text={"format": {"type": "text"}, "verbosity": "medium"},
            tools=[],
            store=True,
        )
        return resposta.output_text
    except Exception as e:
        print(e)
        return "Não foi possível gerar a análise no momento."
