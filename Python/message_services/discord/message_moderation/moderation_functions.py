from commands.default_commands import calcular_idade
import asyncio
import re

async def moderate(bot, message):
    if await portaria(bot, message): return True
    return False


async def portaria(bot, message):
    need_correction = False
    if message.channel.id == 860472155782119464:  # ID do canal de portaria
        need_correction = await check_age(bot, message)
        
        return need_correction
    return False
async def check_age(bot, message):
    pattern1 = r'\b(\d{2}/\d{2}/\d{4})\b.*?(\d{1,2})\s?anos\b'  # Regex para encontrar a data seguida de "00 anos"
    pattern2 = r'\b(\d{1,2})\s?anos\b.*?\b(\d{2}/\d{2}/\d{4})\b'  # Regex para encontrar "00 anos" seguida da data
    match1 = re.search(pattern1, message.content)
    match2 = re.search(pattern2, message.content)
    if match1:
        data_nascimento = match1.group(1)
        idade = int(match1.group(2))
    elif match2:
        idade = int(match2.group(1))
        data_nascimento = match2.group(2)
    if match1 or match2:
        if calcular_idade(data_nascimento) != idade and idade > 0:
            await asyncio.sleep(3)
            await message.channel.send('Sua idade não bate com a data de nascimento que você informou meu querido, corrige isso u.u', reference=message)
            return True
        if idade == 0:
            await asyncio.sleep(3)
            await message.channel.send('Você não pode ter 0 anos, né?', reference=message)
            return True
    if re.search(r'\b(\d{1,2})\s?anos\b',message.content) or re.search(r'\b(\d{2}/\d{2}/\d{4})\b',message.content):
        await asyncio.sleep(3)
        await message.channel.send('Você precisa informar a sua data de nascimento junto com a sua idade: "X anos", você pode corrigir isso pra gente, por favor?', reference=message)
        await asyncio.sleep(1)
        await message.channel.send('segue esse exemplo: 20 anos, nascido em 01/01/2000')
        return True
    return False