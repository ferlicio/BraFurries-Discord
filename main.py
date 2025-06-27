from message_services.discord_service import run_discord_client
import sys, codecs
import asyncio

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
chatBot = {
    "name": "Coddy",
}

async def main():
    await run_discord_client(chatBot)

if __name__ == "__main__":
    asyncio.run(main())



