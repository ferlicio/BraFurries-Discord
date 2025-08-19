from core.AI_Functions.terceiras.openAI import *
from core.routine_functions import *
from core.discord_events import *
from core.verifications import *
from core.database import *
from settings import DISCORD_MEMBER_NOT_VERIFIED_ROLE
from discord.ext import tasks
from discord import app_commands
from schemas.models.bot import *
from schemas.models.locals import *
from schemas.types.server_messages import *
from datetime import datetime, timedelta, time, timezone
from dateutil import tz, relativedelta
from typing import Literal
import requests
import discord
import re
import os
import sys

DEFAULT_ALLOWED_MENTIONS = discord.AllowedMentions(everyone=False, roles=False)

def sanitize_mentions(content: str) -> str:
    content = re.sub(r'@everyone', '@​everyone', content, flags=re.IGNORECASE)
    content = re.sub(r'@here', '@​here', content, flags=re.IGNORECASE)
    content = re.sub(r'<@&\d+>', '', content)
    return content

_original_send = discord.abc.Messageable.send

async def send_filtered(self, content=None, *args, **kwargs):
    if isinstance(content, str):
        content = sanitize_mentions(content)
    kwargs.setdefault('allowed_mentions', DEFAULT_ALLOWED_MENTIONS)
    return await _original_send(self, content=content, *args, **kwargs)

discord.abc.Messageable.send = send_filtered

BIRTHDAY_REGEX = re.compile(r'(\d{1,2})(?:\s?(?:d[eo]|\/|\\|\.)\s?|\s?)(\d{1,2}|(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))(?:\s?(?:d[eo]|\/|\\|\.)\s?|\s?)(\d{4})')
MONTHS = ['00','janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

intents = discord.Intents.default()
for DISCORD_INTENT in DISCORD_INTENTS:
    setattr(intents, DISCORD_INTENT, True)
bot = MyBot(config=None,command_prefix=DISCORD_BOT_PREFIX, intents=discord.Intents.all(), allowed_mentions=DEFAULT_ALLOWED_MENTIONS)
levelConfig = None
timezone_offset = -3.0  # Pacific Standard Time (UTC−08:00)
def now() -> datetime: return (datetime.now(timezone(timedelta(hours=timezone_offset)))).replace(tzinfo=None)
initialized = False

async def load_cogs():
    """Carrega todas as cogs do bot e retorna uma lista de erros."""
    errors = []
    for filename in os.listdir('cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
            except Exception as e:
                errors.append((filename, e))
    return errors


async def initialize_bot():
    global initialized
    if initialized: return

    # guild = bot.get_guild(DISCORD_GUILD_ID)
    # bot.config.append(Config(getConfig(guild)))
    errors = await load_cogs()
    guild = bot.get_guild(DISCORD_GUILD_ID)
    bot.config = Config(getConfig(guild))
    if errors:
        print('Falha ao carregar todas as cogs. Sincronização de comandos cancelada.')
        for filename, err in errors:
            print(f' - {filename}: {err}')
    else:
        print('Todas as cogs carregadas com sucesso!')
        try:
            synced = await bot.tree.sync()
            print(f'{len(synced)} Comandos sincronizados com sucesso!')
        except Exception as e:
            print(e)
    print(bot.config)
    # print(bot.config[0])
    if DISCORD_BUMP_WARN: bumpWarning.start()
    if DISCORD_HAS_BUMP_REWARD: bumpReward.start()
    cronJobs12h.start()
    cronJobs2h.start()
    cronJobs30m.start()
    timeSpecificTasks.start()
    dailyRestart.start()
    initialized = True


@bot.event
async def on_ready():
    print(f'Logado como {bot.user}')
    await initialize_bot()

    
@bot.tree.error
async def on_app_command_error(ctx, error):
    if isinstance(error, app_commands.AppCommandError) and 'Member' in str(error) and 'not found' in str(error):
        match = re.search(r"(\d{17,20})", str(error))
        if match:
            member_id = int(match.group(1))
            try:
                user = await bot.fetch_user(member_id)
            except Exception:
                user = None
            includeUser(user if user else str(member_id), ctx.guild.id)
        return await ctx.response.send_message('Não foi possível encontrar o membro informado.', ephemeral=True)
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send('Você não informou todos os argumentos necessários para o comando')
    if isinstance(error, commands.BadArgument):
        return await ctx.send('Você informou um argumento inválido para o comando')
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send('Você não tem permissão para fazer isso')
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f'Esse comando está em cooldown! Tente novamente em {error.retry_after:.2f} segundos')
    channel_name = getattr(ctx.channel, 'name', str(ctx.channel))
    user_name = getattr(ctx.user, 'display_name', str(ctx.user))
    text = f'Coddy apresentou um erro: \n**Canal**: {channel_name} \n**Usuário**: {user_name} \n**Erro**:{error}'
    return requests.post(
        f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage?chat_id={os.getenv('TELEGRAM_ADMIN')}&text={text}"
    )

@bot.event
async def on_message(message: discord.Message):
    await warnMemberWithMissingQuestions(message)

    if message.author.bot:
        return
    
    await mentionArtRoles(bot, message)
    await secureArtPosts(message)
    await handle_ai_response(bot, message)

@bot.event
async def on_reaction_add(reaction, user):
    pass

@bot.event
async def on_member_update(before:discord.member.Member, after:discord.member.Member):
    changes = checkRolesUpdate(before, after)
    visitor_role = after.guild.get_role(DISCORD_MEMBER_NOT_VERIFIED_ROLE)
    if changes and visitor_role in changes.get('removidos', []):
        try:
            includeUser(after, after.guild.id, now())
        except Exception as e:
            print(f'Erro ao registrar membro aprovado: {e}')
    if before.nick != after.nick:
        await logProfileChange(
            bot,
            after.guild,
            after,
            {"Apelido": (before.nick or before.name, after.nick or after.name)},
        )


@bot.event
async def on_user_update(before: discord.User, after: discord.User):
    changes = {}
    if before.global_name != after.global_name:
        changes["Nome de exibição"] = (before.global_name, after.global_name)
    if before.name != after.name:
        changes["Nome de usuário"] = (before.name, after.name)
    if not changes:
        return

    for guild in bot.guilds:
        member = guild.get_member(after.id)
        if member:
            await logProfileChange(bot, guild, member, changes)



@tasks.loop(hours=12)
async def cronJobs12h():
    await removeTempRoles(bot)

@tasks.loop(hours=2)
async def cronJobs2h():
    await checkTicketsState(bot)

@tasks.loop(minutes=30)
async def cronJobs30m():
    # getServerConfigurations(bot)
    if bot.config.hasLevels != False: 
        print('Configurações de níveis não encontradas')
        pass
    
@tasks.loop(hours=1)
async def timeSpecificTasks():
    """Executa verificações que dependem de horários específicos."""
    if now().hour == 12:
        await sendBirthdayMessages(bot)


@tasks.loop(time=time(hour=4, tzinfo=timezone(timedelta(hours=timezone_offset))))
async def dailyRestart():
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)




@tasks.loop(hours=2) #0.16   10 minutos
async def bumpWarning():
    currentTime = now().strftime("%H:%M:%S")
    if int(currentTime[:2])>=DISCORD_BUMP_WARNING_TIME[0] and int(currentTime[:2])<=DISCORD_BUMP_WARNING_TIME[1]:
        bumpChannel = bot.get_channel(853971735514316880)
        generalChannel = bot.get_channel(753348623844114452)
        async for msg in bumpChannel.history(limit=5):
            if msg.author.id == 302050872383242240:
                lastMessage = msg
                break
        lastBump = lastMessage.created_at.astimezone(tz.gettz('America/Sao_Paulo')).replace(tzinfo=None)
        timeSinceLastBump = now() - lastBump
        needToWarn = True
        async for msg in generalChannel.history(limit=200):
            if msg.author.id == 1106756281420759051 and msg.content.__contains__('bump'):
                if now() - msg.created_at.astimezone(tz.gettz('America/Sao_Paulo')).replace(tzinfo=None) < timedelta(hours=2):
                    needToWarn = False
                break
        if (timeSinceLastBump.days >= 1 or timeSinceLastBump.total_seconds() >= 7200) and needToWarn:
            from core.messages import bump
            import random
            await generalChannel.send(f"{bump[int(random.random() * len(bump))]} {lastMessage.jump_url}")

@tasks.loop(hours=6) #0.16   10 minutos
async def bumpReward():
    hourToReward = 12
    waitTime = hourToReward - now().hour if now().hour < hourToReward else 36 - now().hour
    await asyncio.sleep(waitTime*3600)
    if now().day == 1:
        #pegas as mensagens do ultimo mês no canal de bump
        channel = bot.get_channel(853971735514316880)
        guild = channel.guild
        vipRoles = getVIPConfigurations(guild)['VIPRoles']
        bumpers = {}
        bumpersNames = {}
        async for msg in channel.history(after=now() - relativedelta.relativedelta(months=1)):
            # se a mensagem for do bot e for do mês passado, conta como bump
            if msg.author.id == 302050872383242240:
                # agora vamos criar uma key para cada membro que deu bump
                bumper = guild.get_member(msg.interaction.user.id)
                if bumper == None:
                    continue
                if not bumpers.__contains__(msg.interaction.user.id):
                    bumpers[msg.interaction.user.id] = 0
                    bumpersNames[msg.interaction.user.name] = 0
                bumpers[msg.interaction.user.id] += 1
                bumpersNames[msg.interaction.user.name] += 1
        bumpers = dict(sorted(bumpers.items(), key=lambda item: item[1], reverse=True))
        bumpersNames = dict(sorted(bumpersNames.items(), key=lambda item: item[1], reverse=True))
        otherBumpers = bumpers.copy()
        topBumpers:list[discord.User] = []
        alreadyVipMembers = []
        for i in range(20):
            member = guild.get_member(list(bumpers.keys())[i])
            otherBumpers.pop(member.id)
            if member == None:
                continue
            topBumpers.append(member)
            if vipRoles in member.roles:
                alreadyVipMembers.append(member)
            if [member for member in topBumpers if member not in alreadyVipMembers].__len__() == 3 or i == (bumpers.__len__()-1):
                break
        for idx, membro in enumerate([member for member in topBumpers if member not in alreadyVipMembers]):
            with pooled_connection() as cursor:
                if idx == 0:
                    await assignTempRole(guild.id, membro, DISCORD_VIP_ROLES_ID[1], (now()+timedelta(days=21)).replace(tzinfo=None), "Bump Reward")
                    await membro.send(f"""Parabéns! Você foi um dos top 3 bumpers do mês passado no servidor da BraFurries e ganhou o cargo VIP {guild.get_role(DISCORD_VIP_ROLES_ID[1]).name} por 3 semanas!""")
                    (f"""
    Junto com o cargo, você também ganhou 1 nivel de VIP e algumas moedas! (em implementação)""")
                if idx == 1:
                    await assignTempRole(guild.id, membro, DISCORD_VIP_ROLES_ID[1], (now()+timedelta(days=14)).replace(tzinfo=None), "Bump Reward")
                    await membro.send(f"""Parabéns! Você foi um dos top 3 bumpers do mês passado no servidor da BraFurries e ganhou o cargo VIP {guild.get_role(DISCORD_VIP_ROLES_ID[1]).name} por 2 semanas!""")
                    (f"""
    Junto com o cargo, você também ganhou algumas moedas! (em implementação)""")
                if idx == 2:
                    await assignTempRole(guild.id, membro, DISCORD_VIP_ROLES_ID[1], (now()+timedelta(days=7)).replace(tzinfo=None), "Bump Reward")
                    await membro.send(f"Parabéns! Você foi um dos top 3 bumpers do mês passado no servidor da BraFurries e ganhou o cargo VIP {guild.get_role(DISCORD_VIP_ROLES_ID[1]).name} por 1 semana!")

        with pooled_connection() as cursor:     
            for idx, membro in enumerate([member for member in topBumpers if member in alreadyVipMembers]):
                if idx == 0:
                    if membro == topBumpers[0]:
                        await membro.send(f"""Parabéns! Você foi o membro que mais deu bump no servidor da BraFurries no mês passado! 

    Obrigado de coração por ajudar o servidor a crescer! <3""")
                        "Porém como você ja tem um cargo VIP, apenas iremos adicionar 1 nivel de VIP para você e mais algumas moedas(em implementação)!"
                if idx == 1:
                    if membro == topBumpers[1]:
                        await membro.send(f"""Parabéns! Você foi o segundo membro que mais deu bump no servidor da BraFurries no mês passado!

    Obrigado de coração por ajudar o servidor a crescer! <3""")
                        "Porém como você ja tem um cargo VIP, apenas iremos adicionar algumas moedas ao seu inventário!(em implementação)"
                if idx == 2:
                    if membro == topBumpers[2]:
                        await membro.send(f"""Parabéns! Você foi o terceiro membro que mais deu bump no servidor da BraFurries no mês passado!

    Obrigado de coração por ajudar o servidor a crescer! <3""")
                        "Porém como você ja tem um cargo VIP, apenas iremos adicionar algumas moedas ao seu inventário!(em implementação)"
        
        for membroId in otherBumpers:
            membro = guild.get_member(membroId)
            if membro == None:
                print(f"membro não encontrado: ${membroId}")
                continue
            try:
                print("agradecer bump: "+membro.name)
                await membro.send(f"""Oiê! Só passando para agradecer por ter dado bump no servidor da BraFurries no mês passado!
Você pode não ter sido um dos top 3 bumpers, mas saiba que sua ajuda é muito importante para o nosso servidor crescer! <3""")
            except Exception as e:
                print(f"ocorreu um erro ao enviar a mensagem: ${e}")
            
        # agora vamos mandar uma mensagem privada para o titio derg com os membros que deram mais bump
        titio = guild.get_member(167436511787220992)
        message = f"Os membros que deram bump no mês passado foram: \n"
        for member in bumpersNames:
            # se for o ultimo membro adiciona \n no final
            message += f"{member}: {bumpersNames[member]}"+ ("" if list(bumpersNames.keys())[-1] == member else "\n")
        await titio.send(message)

        from core.monthly_bumps import save_monthly_bumps
        save_monthly_bumps(guild.id, bumpers)
        


@bot.tree.command(name=f'testes', description=f'teste')
async def test(ctx: discord.Interaction):
    pass

def run_discord_client(chatBot):
    bot.chatBot = chatBot
    bot.run(os.getenv('DISCORD_TOKEN'))
