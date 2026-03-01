import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

OWNER_ROLE_NAME = "ShortX Owner"

# ---------- FILES ----------
LEVEL_FILE = "levels.json"
BIRTHDAY_FILE = "birthdays.json"

# ---------- LOAD DATA ----------
def load_data(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

levels = load_data(LEVEL_FILE)
birthdays = load_data(BIRTHDAY_FILE)

# ---------- READY ----------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

    print(f"✅ Logged in as {bot.user}")

# ---------- LEVEL SYSTEM ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)

    if user_id not in levels:
        levels[user_id] = {"xp": 0, "level": 1}

    levels[user_id]["xp"] += 5

    if levels[user_id]["xp"] >= levels[user_id]["level"] * 100:
        levels[user_id]["xp"] = 0
        levels[user_id]["level"] += 1
        await message.channel.send(
            f"🎉 {message.author.mention} leveled up to {levels[user_id]['level']}!"
        )

    save_data(LEVEL_FILE, levels)

    await bot.process_commands(message)

# ---------- LEADERBOARD ----------
@bot.tree.command(name="leaderboard", description="Show top 10 users")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(levels.items(), key=lambda x: x[1]["level"], reverse=True)

    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())

    for i, (user_id, data) in enumerate(sorted_users[:10], start=1):
        user = bot.get_user(int(user_id))
        name = user.name if user else "Unknown"
        embed.add_field(
            name=f"{i}. {name}",
            value=f"Level {data['level']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ---------- BIRTHDAY ----------
@bot.tree.command(name="setbirthday", description="Set your birthday (DD-MM)")
async def setbirthday(interaction: discord.Interaction, date: str):
    birthdays[str(interaction.user.id)] = date
    save_data(BIRTHDAY_FILE, birthdays)
    await interaction.response.send_message("🎂 Birthday saved!")

@tasks.loop(hours=24)
async def check_birthdays():
    today = datetime.now().strftime("%d-%m")
    for user_id, date in birthdays.items():
        if date == today:
            user = bot.get_user(int(user_id))
            if user:
                try:
                    await user.send("🎉 Happy Birthday from ShortX Bot!")
                except:
                    pass

# ---------- ROLE CHECK ----------
def is_owner():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        return role is not None
    return app_commands.check(predicate)

# ---------- MODERATION ----------
@bot.tree.command(name="timeout", description="Timeout a member")
@is_owner()
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: int,
    reason: str = "No reason"
):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(
        f"⏳ {member.mention} timed out for {minutes} minutes."
    )

@bot.tree.command(name="untimeout", description="Remove timeout")
@is_owner()
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(
        f"✅ Timeout removed from {member.mention}"
    )

@bot.tree.command(name="kick", description="Kick a member")
@is_owner()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} has been kicked.")

@bot.tree.command(name="ban", description="Ban a member")
@is_owner()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member.mention} has been banned.")

bot.run(TOKEN)
