import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("No Discord token found in .env file")

# Bot setup with required intents
intents = discord.Intents.default()
intents.members = True  # Needed for member permission checking
intents.guilds = True   # Needed for guild data access
intents.message_content = True  # Needed for message commands
bot = commands.Bot(
    command_prefix='/', 
    intents=intents,
    # This setting makes the bot respond to mentions and adds help command
    help_command=commands.DefaultHelpCommand(),
)

@bot.event
async def setup_hook():
    print("Setup hook running...")
    try:
        await load_extensions()
        print("Setup complete!")
    except Exception as e:
        print(f"Error during setup: {e}")

# Load all cogs
async def load_extensions():
    print("Loading extensions...")
    for file in Path("./cogs").glob("*.py"):
        if file.stem != "__init__":
            try:
                await bot.load_extension(f"cogs.{file.stem}")
                print(f"Loaded extension: cogs.{file.stem}")
            except Exception as e:
                print(f"Failed to load extension cogs.{file.stem}: {e}")

@bot.event
async def on_ready():
    print("\nBot is starting up...")
    print(f"Connected to Discord: {bot.is_ready()}")
    print(f"Bot user object: {bot.user}")
    
    if bot.user:
        # Calculate needed permissions:
        # VIEW_CHANNELS (1 << 10) = 1024
        # SEND_MESSAGES (1 << 11) = 2048
        # MANAGE_ROLES (1 << 28) = 268435456
        permissions = 1024 + 2048 + 268435456
        
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions={permissions}&scope=bot%20applications.commands"
        print(f"\nLogged in as {bot.user} (ID: {bot.user.id})")
        print("------")
        print("Use this URL to invite the bot to your server:")
        print(invite_url)
        print("------")
        
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    else:
        print("WARNING: bot.user is None. The bot might not be properly connected to Discord.")

async def main():
    try:
        print("Starting bot...")
        async with bot:
            print("Bot context initialized")
            await bot.start(str(TOKEN))
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutdown by user")
    except Exception as e:
        print(f"Fatal error: {e}")
