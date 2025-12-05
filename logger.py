# cogs/logger.py
import discord
from discord.ext import commands, tasks
import os, json, aiofiles
from datetime import datetime

STORAGE_PATH = "data/storage.json"
os.makedirs("logs", exist_ok=True)

async def async_read_storage():
    async with aiofiles.open(STORAGE_PATH, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content)

async def async_write_file(path, text):
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        await f.write(text + "\n")

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = os.getenv("FILE_LOG_PATH", "logs/globalchat_log.txt")

    async def log_event(self, message: str, level: str = "INFO"):
        """Log to text file and optionally to configured log channel/guild."""
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}][{level}] {message}"
        # write file
        try:
            await async_write_file(self.file_path, line)
        except Exception as e:
            print("Fehler beim Schreiben der Logdatei:", e)

        # try find configured log channel
        try:
            data = await async_read_storage()
            logconf = data.get("log") or {}
            gid = logconf.get("guild_id")
            cid = logconf.get("channel_id")
            if gid and cid:
                guild = self.bot.get_guild(int(gid))
                if guild:
                    ch = guild.get_channel(int(cid))
                else:
                    ch = self.bot.get_channel(int(cid))
                if ch:
                    # send a concise embed
                    embed = discord.Embed(title="GlobalChat Log", description=message, timestamp=datetime.utcnow(), color=discord.Color.blue())
                    embed.set_footer(text=level)
                    await ch.send(embed=embed)
        except Exception as e:
            print("Fehler beim Senden an Log-Channel:", e)

    # Example of hooking into message delete/edit events for logging
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author and message.author.bot:
            return
        await self.log_event(f"Message deleted in {getattr(message.guild, 'name', 'DM')}#{getattr(message.channel, 'name', '')} by {message.author}: {message.content}", level="WARN")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author and before.author.bot:
            return
        if before.content == after.content:
            return
        await self.log_event(f"Message edited in {getattr(before.guild, 'name', 'DM')}#{getattr(before.channel, 'name', '')} by {before.author}: '{before.content}' -> '{after.content}'", level="INFO")

def setup(bot):
    bot.add_cog(Logger(bot))
