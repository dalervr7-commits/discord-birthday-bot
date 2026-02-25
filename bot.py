import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

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
# FILE FUNCTIONS
# ==============================

def load_data(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)

    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# WARNING SYSTEM
# ==============================

def add_warning(user_id):
    warnings = load_data("warnings.json")
    user_id = str(user_id)

    if user_id not in warnings:
        warnings[user_id] = 0

    warnings[user_id] += 1
    save_data("warnings.json", warnings)
    return warnings[user_id]

# ==============================
# ANTI SPAM SETUP
# ==============================

user_message_times = {}
SPAM_LIMIT = 5
SPAM_SECONDS = 5

BAD_WORDS = ["badword1", "badword2"]  # Customize

# ==============================
# XP SYSTEM + AUTOMOD
# ==============================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = datetime.now()

    # ==================
    # ANTI SPAM
    # ==================
    if message.author.id not in user_message_times:
        user_message_times[message.author.id] = []

    user_message_times[message.author.id].append(now)

    user_message_times[message.author.id] = [
        t for t in user_message_times[message.author.id]
        if (now - t).seconds < SPAM_SECONDS
    ]

    if len(user_message_times[message.author.id]) >= SPAM_LIMIT:
        await message.delete()
        warn_count = add_warning(message.author.id)
        await message.channel.send(
            f"⚠️ {message.author.mention} Stop spamming! Warning {warn_count}/3"
        )

        if warn_count >= 3:
            try:
                await message.author.timeout(timedelta(minutes=10), reason="Spam")
                await message.channel.send(
                    f"🔇 {message.author.mention} timed out for 10 minutes."
                )
            except:
                pass
        return

    # ==================
    # BAD WORD FILTER
    # ==================
    if any(word in message.content.lower() for word in BAD_WORDS):
        await message.delete()
        warn_count = add_warning(message.author.id)
        await message.channel.send(
            f"🚫 {message.author.mention} Watch your language! Warning {warn_count}/3"
        )

        if warn_count >= 3:
            try:
                await message.author.timeout(timedelta(minutes=10), reason="Bad language")
                await message.channel.send(
                    f"🔇 {message.author.mention} timed out for 10 minutes."
                )
            except:
                pass
        return

    # ==================
    # XP SYSTEM
    # ==================
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

# ==============================
# LEVEL COMMANDS
# ==============================

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

# ==============================
# MODERATION COMMANDS
# ==============================

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, time: int, unit: str):
    if unit == "m":
        duration = timedelta(minutes=time)
    elif unit == "h":
        duration = timedelta(hours=time)
    else:
        await ctx.send("Use m (minutes) or h (hours)")
        return

    await member.timeout(duration, reason=f"Timeout by {ctx.author}")
    await ctx.send(f"🔇 {member.mention} timed out for {time}{unit}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 {member.mention} timeout removed.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)

# ==============================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    birthday_check.start()

bot.run(TOKEN)
