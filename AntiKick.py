import discord
from discord.ext import commands
import asyncio
import json
import os
from dotenv import load_dotenv
from server import keep_alive

keep_alive()

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.moderation = True 

bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"kick_limit": 3, "enabled": True, "log_channel_id": "ID_DU_SALON_LOG"}, f)

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_config()

kick_count = {} 

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

@bot.event
async def on_audit_log_entry_create(entry):
    """Détecte les kicks et punit les modérateurs abusifs"""
    if entry.action == discord.AuditLogAction.kick and config["enabled"]:
        kicker = entry.user 
        guild = entry.guild
        log_channel_id = int(config["log_channel_id"])

        if kicker.bot:
            return

        if kicker.id not in kick_count:
            kick_count[kicker.id] = {"count": 1, "timestamp": asyncio.get_event_loop().time()}
        else:
            kick_count[kicker.id]["count"] += 1

        elapsed_time = asyncio.get_event_loop().time() - kick_count[kicker.id]["timestamp"]
        if elapsed_time > 60:
            kick_count[kicker.id] = {"count": 1, "timestamp": asyncio.get_event_loop().time()}
        elif kick_count[kicker.id]["count"] >= config["kick_limit"]:
            await guild.kick(kicker, reason="Kick abusif de membres")
            print(f"{kicker} a été kické pour avoir kické {config['kick_limit']} personnes en moins d'une minute.")

            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(
                    f"🚨 **{kicker}** a été kické pour avoir kické {config['kick_limit']} membres en moins d'une minute. L'action a été jugée abusive."
                )

            del kick_count[kicker.id]

class AntiKickSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Kick après 1 kick", value="1", description="Kick immédiatement."),
            discord.SelectOption(label="Kick après 2 kicks", value="2", description="Kick après 2 kicks."),
            discord.SelectOption(label="Kick après 3 kicks", value="3", description="Kick après 3 kicks (par défaut).")
        ]
        super().__init__(placeholder="Choisissez le mode de l'anti-kick", options=options)

    async def callback(self, interaction: discord.Interaction):
        config["kick_limit"] = int(self.values[0])
        save_config(config)
        await interaction.response.send_message(f"✅ Sécurité mise à jour : Punition après **{config['kick_limit']}** kicks.", ephemeral=True)

class DisableButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Désactiver l'Anti-Kick", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        config["enabled"] = False
        save_config(config)
        await interaction.response.send_message("🚫 **Anti-Kick désactivé.**", ephemeral=True)

class EnableButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Activer l'Anti-Kick", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        config["enabled"] = True
        save_config(config)
        await interaction.response.send_message("✅ **Anti-Kick activé.**", ephemeral=True)

class AntiKickView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(AntiKickSelect())
        self.add_item(DisableButton())
        self.add_item(EnableButton())

@bot.command()
@commands.has_permissions(administrator=True)
async def antikick(ctx):
    """Affiche le menu pour régler l'anti-kick"""
    embed = discord.Embed(title="🔒 Configuration de l'Anti-Kick", description="Sélectionnez un niveau de sécurité ou désactivez l'anti-kick.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=AntiKickView())

bot.run(token=token)