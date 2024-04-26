from discord.ext import commands

class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)
        self.levels = {}
        self.economy = {}
        self.gptModel = {}

    def __str__(self) -> str:
        return str(self.__dict__)


class MyBot(commands.Bot):
    def __init__(self, config:Config, *args, **kwargs):
        super(MyBot, self).__init__(*args, **kwargs)
        self.config = config
        

