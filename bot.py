import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

TOKEN = MTQ3NTIxMjI1Njg2NTQyMzYwMQ.GcKAwB.hXCbyQm_syWdWPCzzBgcufF0QkU_HODkiPp1WI
BIRTHDAY_CHANNEL_ID = 1475414781853700157

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================
# FILE SETUP
# ==========================

LEVELS_FILE = "levels.json"
BIRTHDAY_FILE = "birthdays.json"

def load_file(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)

def save_file(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ==========================
# READY EVENT
# ==========================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_birthdays.start()

# ==========================
# LEVEL SYSTEM
# ==========================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_file(LEVELS_FILE)
    user_id = str(message.author.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1}

    data[user_id]["xp"] += 10

    xp = data[user_id]["xp"]
    level = data[user_id]["level"]
    required_xp = 100 * level

    if xp >= required_xp:
        data[user_id]["level"] += 1
        data[user_id]["xp"] = 0
        await message.channel.send(
            f"🎉 {message.author.mention} leveled up to Level {level + 1}!"
        )

    save_file(LEVELS_FILE, data)

    await bot.process_commands(message)

@bot.command(name="r")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_file(LEVELS_FILE)
    user_id = str(member.id)

    if user_id not in data:
        await ctx.send("No XP yet.")
        return

    xp = data[user_id]["xp"]
    level = data[user_id]["level"]
    required_xp = 100 * level

    embed = discord.Embed(
        title=f"{member.name}'s Rank",
        color=discord.Color.blue()
    )
    embed.add_field(name="Level", value=level)
    embed.add_field(name="XP", value=f"{xp}/{required_xp}")
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command(name="lb")
async def leaderboard(ctx):
    data = load_file(LEVELS_FILE)

    sorted_users = sorted(
        data.items(),
        key=lambda x: (x[1]["level"], x[1]["xp"]),
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 Server Leaderboard",
        color=discord.Color.green()
    )

    for i, (user_id, info) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{i}. {user.name}",
            value=f"Level {info['level']} | XP {info['xp']}",
            inline=False
        )

    await ctx.send(embed=embed)

# ==========================
# BIRTHDAY SYSTEM
# ==========================

@bot.command(name="setbirthday")
async def set_birthday(ctx, date: str):
    """
    Format: !setbirthday DD-MM
    Example: !setbirthday 25-12
    """
    try:
        datetime.strptime(date, "%d-%m")
    except ValueError:
        await ctx.send("❌ Use format: DD-MM (Example: 25-12)")
        return

    data = load_file(BIRTHDAY_FILE)
    data[str(ctx.author.id)] = date
    save_file(BIRTHDAY_FILE, data)

    await ctx.send("🎂 Birthday saved successfully!")

@tasks.loop(hours=24)
async def check_birthdays():
    today = datetime.now().strftime("%d-%m")
    data = load_file(BIRTHDAY_FILE)

    for user_id, date in data.items():
        if date == today:
            channel = bot.get_channel(BIRTHDAY_CHANNEL_ID)
            if channel:
                user = await bot.fetch_user(int(user_id))
                await channel.send(f"🎉🎂 Happy Birthday {user.mention}!")

bot.run(TOKEN)
