from notificationMethods.notificationMethod import NotificationMethod
import discord
import os
from dotenv import load_dotenv
import asyncio
import logging

logger = logging.getLogger(__name__)


class DiscordClientManager:
    _instance = None
    _client = None
    _token = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._token is None:
            load_dotenv()
            self._token = os.getenv('DISCORD_BOT_TOKEN')
            if not self._token:
                logger.error("Discord bot token not found")
    
    async def get_client(self):
        if not self._token:
            raise ValueError("No Discord token available")
            
        if self._client is None or self._client.is_closed():
            intents = discord.Intents.default()
            self._client = discord.Client(intents=intents)
            await self._client.start(self._token)
            
        return self._client
    
    async def send_to_channel(self, channel_id: int, message: str):
        try:
            client = await self.get_client()
            
            channel = client.get_channel(channel_id)
            if not channel:
                channel = await client.fetch_channel(channel_id)
            
            if not isinstance(channel, discord.TextChannel):
                logger.error(f"Channel {channel_id} is not a text channel")
                return
            
            await channel.send(message)
            
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
    
    async def close(self):
        if self._client and not self._client.is_closed():
            await self._client.close()


class DiscordChannelMessage(NotificationMethod):
    
    def __init__(self, id: str, channel_id: str):
        super().__init__(id)
        self.channel_id = int(channel_id)
        self.client_manager = DiscordClientManager()
    
    def send_notification(self, message: str) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_message(message))
        except RuntimeError:
            asyncio.run(self._send_message(message))
    
    async def _send_message(self, message: str) -> None:
        await self.client_manager.send_to_channel(self.channel_id, message)