import discord
import asyncio
import os
import sys
from discord.ext import commands
from colorama import init, Fore

# System Config
init(autoreset=True)
RED = "\033[38;2;255;0;0m"
W = Fore.WHITE

def banner():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"""
{RED}███╗   ███╗██████╗     ███╗   ███╗ ██████╗ ███████╗ ██████╗  ██████╗██╗███████╗████████╗██╗   ██╗
{RED}████╗ ████║██╔══██╗    ████╗ ████║██╔════╝ ██╔════╝██╔═══██╗██╔════╝██║██╔════╝╚══██╔══╝╚██╗ ██╔╝
{RED}██╔████╔██║██████╔╝    ██╔████╔██║██║      ███████╗██║   ██║██║     ██║█████╗     ██║    ╚████╔╝ 
{RED}██║╚██╔╝██║██╔══██╗    ██║╚██╔╝██║██║      ╚════██║██║   ██║██║     ██║██╔══╝     ██║     ╚██╔╝  
{RED}██║ ╚═╝ ██║██║  ██║    ██║ ╚═╝ ██║╚██████╗ ███████║╚██████╔╝╚██████╗██║███████╗   ██║      ██║   
{RED}╚═╝     ╚═╝╚═╝  ╚═╝    ╚═╝     ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝╚═╝╚══════╝   ╚═╝      ╚═╝   
{RED}────────────────────────────────────────────────────────────────────────────────────────────────────
{RED}  ᴍɪʀʀᴏʀ-ᴘʀᴏᴛᴏᴄᴏʟ ᴠ3.1 | ᴅᴇᴠ: ᴢʏᴘʜᴇʀ | ᴀᴜᴛʜ: ᴍʀ_ᴍᴄꜱᴏᴄɪᴇᴛʏ | ᴍᴏᴅᴇ: ɪɴꜱᴛᴀɴᴛ ꜱᴇʀᴠᴇʀ ᴄʟᴏɴᴇ
{RED}────────────────────────────────────────────────────────────────────────────────────────────────────""")

async def execute_mirror(token, source_id, target_id):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=".", intents=intents)

    @bot.event
    async def on_ready():
        banner()
        source = bot.get_guild(int(source_id))
        target = bot.get_guild(int(target_id))

        if not source or not target:
            print(f"{RED}[!] Error: Bot missing from Source or Target server.")
            await bot.close()
            return

        print(f"{RED}[*] Initiating Kernel Mirror: {source.name} -> {target.name}")
        
        # Phase 1: Vaporize Target
        print(f"{RED}[*] Purging target environment...")
        for channel in target.channels:
            try: await channel.delete()
            except: pass

        # Phase 2: Role Reconstruction
        print(f"{RED}[*] Synchronizing Roles...")
        role_map = {}
        for role in reversed(source.roles):
            if role.name != "@everyone" and not role.managed:
                try:
                    new_role = await target.create_role(
                        name=role.name, 
                        permissions=role.permissions, 
                        color=role.color, 
                        hoist=role.hoist, 
                        mentionable=role.mentionable
                    )
                    role_map[role] = new_role
                except: pass

        # Phase 3: Architectural Mapping
        print(f"{RED}[*] Mirroring Categories & Channels...")
        for category in source.categories:
            new_cat = await target.create_category(name=category.name)
            print(f"{RED}    [>] Category: {category.name}")
            for channel in category.channels:
                try:
                    if isinstance(channel, discord.TextChannel):
                        await new_cat.create_text_channel(name=channel.name, topic=channel.topic)
                    elif isinstance(channel, discord.VoiceChannel):
                        # FIXED: Removed the space in bitrate
                        await new_cat.create_voice_channel(name=channel.name, bitrate=channel.bitrate)
                except Exception as e:
                    print(f"{RED}    [!] Channel Error: {e}")

        print(f"\n{RED}[✓] ᴍɪʀʀᴏʀ ᴄᴏᴍᴘʟᴇᴛᴇ. {target.name} ɪꜱ ɴᴏᴡ ᴀ 1:1 ᴄᴏᴘʏ.")
        await bot.close()

    try:
        await bot.start(token)
    except discord.LoginFailure:
        print(f"{RED}[!] Invalid Token provided.")

def main():
    banner()
    t = input(f"{RED}Bot Token: {W}")
    s = input(f"{RED}Source Server ID: {W}")
    d = input(f"{RED}Target Server ID: {W}")
    
    print(f"{RED}[*] Linking to Discord API...")
    asyncio.run(execute_mirror(t, s, d))

if __name__ == "__main__":
    main()