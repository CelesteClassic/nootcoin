from discord.ext import commands
import discord
import logging

import datetime
import config
import json

import asyncio
import subprocess
from multiprocessing import Pool

extensions = [
    "cogs.nootcoin",
    "cogs.admin"
]

class NootBot(commands.Bot):

    async def load_extensions(self):
        for extension in extensions:
            await self.load_extension(extension)

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix='$', intents=intents)
        self.logger = logging.getLogger('discord')

        asyncio.get_event_loop().run_until_complete(self.load_extensions())
            
    async def on_ready(self):
        self.uptime = datetime.datetime.utcnow()

        #game = discord.Game("Mining NootCoin")
        #await self.change_presence(activity=game)

        self.logger.warning(f'Online: {self.user} (ID: {self.user.id})')

    async def on_message(self, message):
        
        if message.author.bot:
            return
        
        if (message.channel.id == 642707799939481611 or message.channel.id == 514502736608231435 or message.channel.id == 1223664467670204428 or message.channel.id == 1224154388084555907):
            await self.process_commands(message)

    async def run(self):
        await super().start(config.token, reconnect=True)