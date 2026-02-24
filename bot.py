import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime

# ==============================
# CONFIG
# ==============================

TOKEN = os.getenv("TOKEN")
BIRTHDAY_CHANNEL_ID = 1475414781853700157

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# FILE SETUP
# ==============================

def load_data(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)
    with open(filename, "r") as f:
        return json.load(f)

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# XP SYSTEM
# ==============================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    levels = load_data("levels.json")
    user_id = str(message.author.id)

    if user_id not in levels:
        levels[user_id] = {"xp": 0, "level": 1}

    xp_gain = random.randint(5, 15)
    levels[user_id]["xp"] += xp_gain

    xp_needed = levels[user_id]["level"] * 100

    if levels[user_id]["xp"] >= xp_needed:
        levels[user_id]["xp"] = 0
        levels[user_id]["level"] += 1
        await message.channel.send(
            f"🎉 {message.author.mention} leveled up to Level {levels[user_id]['level']}!"
        )

    save_data("levels.json", levels)
    await bot.process_commands(message)

# Rank Command
@bot.command()
async def r(ctx):
    levels = load_data("levels.json")
    user_id = str(ctx.author.id)

    if user_id not in levels:
        await ctx.send("You have no XP yet!")
        return

    xp = levels[user_id]["xp"]
    level = levels[user_id]["level"]
    await ctx.send(f"📊 {ctx.author.mention} | Level: {level} | XP: {xp}")

# Leaderboard Command
@bot.command()
async def lb(ctx):
    levels = load_data("levels.json")

    sorted_users = sorted(
        levels.items(),
        key=lambda x: (x[1]["level"], x[1]["xp"]),
        reverse=True
    )

    leaderboard = "🏆 **Top 10 Leaderboard**\n\n"

    for i, (user_id, data) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        leaderboard += f"{i}. {user.name} | Level {data['level']} ({data['xp']} XP)\n"

    await ctx.send(leaderboard)

# ==============================
# BIRTHDAY SYSTEM
# ==============================

@bot.command()
async def setbirthday(ctx, day: int, month: int):
    birthdays = load_data("birthdays.json")
    user_id = str(ctx.author.id)

    birthdays[user_id] = {"day": day, "month": month}
    save_data("birthdays.json", birthdays)

    await ctx.send("🎂 Your birthday has been saved!")

@tasks.loop(hours=24)
async def birthday_check():
    today = datetime.now()
    birthdays = load_data("birthdays.json")

    channel = bot.get_channel(BIRTHDAY_CHANNEL_ID)
    if channel is None:
        return

    for user_id, data in birthdays.items():
        if data["day"] == today.day and data["month"] == today.month:
            user = await bot.fetch_user(int(user_id))
            await channel.send(f"🎉🎂 Happy Birthday {user.mention}! 🎂🎉")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    birthday_check.start()

# ==============================

bot.run(TOKEN)
