import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re
import os

TOKEN = os.getenv("TOKEN")
OWNER_ROLE_NAME = "ShortX Owner"
MOD_LOG_CHANNEL = "mod-logs"

if TOKEN is None:
    raise ValueError("❌ TOKEN environment variable not set!")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

warnings = {}
spam_tracker = {}
levels = {}
xp = {}
birthdays = {}

# ==========================
# 🔒 ROLE CHECK
# ==========================
def is_owner():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=OWNER_ROLE_NAME)
        if role is None:
            await ctx.send("❌ Only ShortX Owner role can use this command.")
            return False
        return True
    return commands.check(predicate)


async def log_action(guild, embed):
    channel = discord.utils.get(guild.text_channels, name=MOD_LOG_CHANNEL)
    if channel:
        await channel.send(embed=embed)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_birthdays.start()


# ==========================
# 🎂 BIRTHDAY SYSTEM
# ==========================
@bot.command()
async def setbirthday(ctx, date: str):
    try:
        datetime.strptime(date, "%d-%m")
        birthdays[ctx.author.id] = date
        await ctx.send(f"🎂 Birthday set to {date}")
    except:
        await ctx.send("❌ Use format DD-MM (Example: 25-12)")


@tasks.loop(hours=24)
async def check_birthdays():
    today = datetime.now().strftime("%d-%m")
    for guild in bot.guilds:
        for user_id, date in birthdays.items():
            if date == today:
                member = guild.get_member(user_id)
                if member:
                    channel = guild.system_channel
                    if channel:
                        await channel.send(f"🎉 Happy Birthday {member.mention}!")


# ==========================
# 🏆 LEVEL + ANTI SPAM
# ==========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    user_id = message.author.id

    if user_id not in xp:
        xp[user_id] = 0
        levels[user_id] = 1

    xp[user_id] += 5

    if xp[user_id] >= levels[user_id] * 100:
        xp[user_id] = 0
        levels[user_id] += 1
        await message.channel.send(
            f"🏆 {message.author.mention} leveled up to {levels[user_id]}!"
        )

    if user_id not in spam_tracker:
        spam_tracker[user_id] = 0

    spam_tracker[user_id] += 1

    if spam_tracker[user_id] >= 6:
        await message.channel.send(f"{message.author.mention} ⚠ Stop spamming!")
        spam_tracker[user_id] = 0

    await bot.process_commands(message)


@bot.command()
async def level(ctx, member: discord.Member = None):
    member = member or ctx.author
    lvl = levels.get(member.id, 1)
    await ctx.send(f"🏆 {member.display_name} is Level {lvl}")


# ==========================
# ⚠ WARN SYSTEM
# ==========================
@bot.command()
@is_owner()
async def warn(ctx, member: discord.Member, *, reason=None):

    if member.id not in warnings:
        warnings[member.id] = 0

    warnings[member.id] += 1
    count = warnings[member.id]

    embed = discord.Embed(
        title="⚠ User Warned",
        description=f"{member.mention} now has {count} warning(s).",
        color=discord.Color.gold()
    )

    if reason:
        embed.add_field(name="Reason", value=reason)

    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)

    if count >= 3:
        await member.timeout(timedelta(minutes=10), reason="Reached 3 warnings")

        auto_embed = discord.Embed(
            title="🚨 Auto Timeout",
            description=f"{member.mention} auto-timed out for 10m.",
            color=discord.Color.orange()
        )

        await ctx.send(embed=auto_embed)
        await log_action(ctx.guild, auto_embed)


# ==========================
# ⏳ TIMEOUT
# ==========================
@bot.command()
@is_owner()
async def timeout(ctx, member: discord.Member, duration: str, *, reason=None):

    match = re.match(r"(\d+)([mh])", duration.lower())
    if not match:
        return await ctx.send("❌ Use format like 10m or 2h")

    amount = int(match.group(1))
    unit = match.group(2)

    delta = timedelta(minutes=amount) if unit == "m" else timedelta(hours=amount)

    await member.timeout(delta, reason=reason)

    embed = discord.Embed(
        title="⏳ User Timed Out",
        description=f"{member.mention} | Duration: {duration}",
        color=discord.Color.orange()
    )

    if reason:
        embed.add_field(name="Reason", value=reason)

    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)


# ==========================
# 👢 KICK
# ==========================
@bot.command()
@is_owner()
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)

    embed = discord.Embed(
        title="👢 User Kicked",
        description=f"{member.mention} has been kicked.",
        color=discord.Color.red()
    )

    if reason:
        embed.add_field(name="Reason", value=reason)

    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)


# ==========================
# 🔨 BAN
# ==========================
@bot.command()
@is_owner()
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)

    embed = discord.Embed(
        title="🔨 User Banned",
        description=f"{member.mention} has been banned.",
        color=discord.Color.dark_red()
    )

    if reason:
        embed.add_field(name="Reason", value=reason)

    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)


# ==========================
# 🧹 CLEAR
# ==========================
@bot.command()
@is_owner()
async def clear(ctx, amount: int):

    if amount > 100:
        return await ctx.send("❌ Max 100 messages at once.")

    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"✅ Deleted {amount} messages.")
    await msg.delete(delay=3)


# ==========================
# ❌ ERROR HANDLER
# ==========================
@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing arguments.")

    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument.")

    elif isinstance(error, commands.CheckFailure):
        pass

    else:
        await ctx.send(f"⚠ Error: {error}")


bot.run(TOKEN)
