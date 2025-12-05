# cogs/global_chat.py
import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

STORAGE_PATH = "data/storage.json"
os.makedirs("data", exist_ok=True)

def load_storage():
    if not os.path.exists(STORAGE_PATH):
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump({"guilds": {}, "blacklist": [], "global_channels": {}, "banned_words": []}, f, ensure_ascii=False, indent=2)
    with open(STORAGE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_storage(data):
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class GlobalChat(commands.Cog):
    """Core global chat relay — connects configured channels across guilds."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = load_storage()
        self.message_cache = {}  # local cache if needed
        self._relay_lock = asyncio.Lock()

    async def cog_load(self):
        # could start background tasks here if needed
        pass

    def is_guild_enabled(self, guild_id: str) -> bool:
        return str(guild_id) in self.storage.get("global_channels", {})

    def get_channel_map(self) -> Dict[str, int]:
        return self.storage.get("global_channels", {})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return  # ignore DMs
        guild_id = str(message.guild.id)
        channel_map = self.get_channel_map()
        if guild_id not in channel_map:
            return

        # Basic moderation: banned words
        banned_words = self.storage.get("banned_words", [])
        content_low = (message.content or "").lower()
        for word in banned_words:
            if word and word.lower() in content_low:
                try:
                    await message.delete()
                except Exception:
                    pass
                # log via logger cog if available
                logger = self.bot.get_cog("Logger")
                if logger:
                    await logger.log_event(f"Deleted message in {message.guild.name} ({message.guild.id}) due to banned word: {word}", level="WARN")
                return

        # Rate limiting: per user naive approach
        # You can expand this to store timestamps in storage for persistent cooldowns
        # Build the relay payload
        await self.relay_message(message)

    async def relay_message(self, message: discord.Message):
        """Relay a single message to all other configured global channels."""
        async with self._relay_lock:
            channel_map = self.get_channel_map()  # guild_id -> channel_id
            origin_guild = str(message.guild.id)
            origin_channel_id = message.channel.id

            # Build content: include author and origin server/channel
            header = f"**{message.author}** from **{message.guild.name}** (#{message.channel.name}) — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            body = message.content or ""
            # Attachments
            files = []
            for att in message.attachments:
                try:
                    fp = await att.to_file(use_cached=True)
                    files.append(fp)
                except Exception:
                    pass

            for gid, ch_id in list(channel_map.items()):
                if gid == origin_guild:
                    continue
                try:
                    ch = self.bot.get_channel(int(ch_id))
                    if not ch:
                        # channel may be gone; remove from storage
                        del channel_map[gid]
                        save_storage(self.storage)
                        continue
                    # preserve mentions but avoid pinging roles/ everyone by default:
                    allowed_mentions = discord.AllowedMentions(users=True, roles=False, everyone=False)
                    await ch.send(header + body, files=files if files else None, allowed_mentions=allowed_mentions)
                except Exception as e:
                    # log via logger cog
                    logger = self.bot.get_cog("Logger")
                    if logger:
                        await logger.log_event(f"Failed to relay message from {message.guild.id} to {gid}: {e}", level="ERROR")

    @commands.command(name="setglobal", help="Set the current channel as the global chat channel for this guild. ADMIN only.")
    @commands.has_permissions(administrator=True)
    async def set_global(self, ctx: commands.Context):
        self.storage.setdefault("global_channels", {})[str(ctx.guild.id)] = ctx.channel.id
        save_storage(self.storage)
        await ctx.send(f"✅ Dieser Kanal ist jetzt verbunden mit dem Global-Chat.")

    @commands.command(name="clearglobal", help="Remove this guild from global chat. ADMIN only.")
    @commands.has_permissions(administrator=True)
    async def clear_global(self, ctx: commands.Context):
        existing = self.storage.get("global_channels", {})
        if str(ctx.guild.id) in existing:
            del existing[str(ctx.guild.id)]
            save_storage(self.storage)
            await ctx.send("✅ Global-Chat für diese Gilde entfernt.")
        else:
            await ctx.send("ℹ️ Diese Gilde war nicht als Global-Chat registriert.")

    @commands.command(name="globalinfo", help="Zeigt alle verbundenen Guilds/Kanäle.")
    async def global_info(self, ctx: commands.Context):
        channel_map = self.get_channel_map()
        if not channel_map:
            await ctx.send("Kein Global-Chat konfiguriert.")
            return
        lines = []
        for gid, ch_id in channel_map.items():
            guild = self.bot.get_guild(int(gid))
            ch = self.bot.get_channel(int(ch_id))
            name = guild.name if guild else f"Guild not cached ({gid})"
            chname = ch.name if ch else f"Channel not cached ({ch_id})"
            lines.append(f"- {name} — #{chname} ({gid}/{ch_id})")
        await ctx.send("**Verbunden:**\n" + "\n".join(lines))

def setup(bot):
    bot.add_cog(GlobalChat(bot))
