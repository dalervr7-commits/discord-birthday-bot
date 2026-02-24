import discord
from discord.ext import commands, tasks
import json
import datetime
import os

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise ValueError("TOKEN environment variable not set.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- JSON FUNCTIONS ---------------- #

def load_json(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

birthdays = load_json("birthdays.json")
activity = load_json("activity.json")

# ---------------- ACTIVITY TRACKER ---------------- #

@bot.event
async def on_message(message):
    if not message.author.bot:
        user_id = str(message.author.id)
        activity[user_id] = activity.get(user_id, 0) + 1
        save_json("activity.json", activity)

    await bot.process_commands(message)

# ---------------- SET BIRTHDAY (PRIVATE EMBED STYLE) ---------------- #

@bot.tree.command(name="setbirthday", description="Set your birthday (DD-MM)")
async def setbirthday(interaction: discord.Interaction, date: str):
    try:
        parsed_date = datetime.datetime.strptime(date, "%d-%m")
    except ValueError:
        await interaction.response.send_message(
            "❌ Use format DD-MM (Example: 21-02)",
            ephemeral=True
        )
        return

    birthdays[str(interaction.user.id)] = date
    save_json("birthdays.json", birthdays)

    formatted_date = parsed_date.strftime("%B %d")

    embed = discord.Embed(
        title="🎂 Birthday Saved!",
        description=f"I've set your birthday to **{formatted_date}**.",
        color=0xF1C40F
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------- LEADERBOARD ---------------- #

@bot.tree.command(name="leaderboard", description="Top 10 active members")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(activity.items(), key=lambda x: x[1], reverse=True)
    top = sorted_users[:10]

    embed = discord.Embed(title="🏆 Top 10 Active Members", color=0x00ff00)

    for i, (user_id, count) in enumerate(top, start=1):
        try:
            user = await bot.fetch_user(int(user_id))
            embed.add_field(
                name=f"{i}. {user.name}",
                value=f"Messages: {count}",
                inline=False
            )
        except:
            continue

    await interaction.response.send_message(embed=embed)

# ---------------- BIRTHDAY CHECK ---------------- #

@tasks.loop(hours=24)
async def birthday_check():
    today = datetime.datetime.now().strftime("%d-%m")

    for guild in bot.guilds:
        birthday_channel = discord.utils.get(
            guild.text_channels,
            name="ᯓ✦∘˙🎂┃ʙɪʀᴛʜᴅᴀʏ"
        )

        if birthday_channel is None:
            continue

        for user_id, date in birthdays.items():
            if date == today:
                member = guild.get_member(int(user_id))
                if member:
                    embed = discord.Embed(
                        title="🎉 HAPPY BIRTHDAY 🎉",
                        description=f"🎂 Let's wish {member.mention} an amazing year ahead!",
                        color=0xFF69B4
                    )
                    await birthday_channel.send(embed=embed)

# ---------------- READY EVENT ---------------- #

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.tree.sync()
    birthday_check.start()

# ---------------- START BOT ---------------- #

bot.run(TOKEN)
