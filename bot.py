import discord
from discord.ext import commands, tasks
import itertools
import os
from dotenv import load_dotenv

# 🌿 Lade Umgebungsvariablen aus .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 🔧 Intents konfigurieren
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# 🤖 Bot initialisieren
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# 🔁 Liste mit wechselnden Statusmeldungen
status_list = itertools.cycle([
  "777",
  "777",
  "777",
  "777",
  "777",
  "777"
    ])

# 🎮 Bot ist bereit
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

    # Alle Cogs automatisch laden
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"🔹 {filename} geladen")
            except Exception as e:
                print(f"⚠️ Fehler beim Laden von {filename}: {e}")

    # Slash-Commands synchronisieren
    try:
        synced = await bot.tree.sync()
        print(f"📜 {len(synced)} Slash-Commands synchronisiert.")
    except Exception as e:
        print(f"⚠️ Fehler beim Syncen der Slash-Befehle: {e}")

    # Status-Loop starten
    change_status.start()


# 🔁 Status wechselt alle 10 Sekunden
@tasks.loop(seconds=10)
async def change_status():
    await bot.change_presence(activity=discord.Game(next(status_list)))


# 🚀 Bot starten
if __name__ == "__main__":
    # Hier TOKEN direkt verwenden, nicht config.TOKEN
    bot.run(TOKEN)
