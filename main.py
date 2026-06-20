import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import random
import re
import asyncio

# Load environment variables from .env locally. Cloud hosts inject them directly.
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# Send logs to the terminal so cloud-hosting dashboards can display them.
handler = logging.StreamHandler()

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot Setup
bot = commands.Bot(command_prefix='!', intents=intents)

# Constants
secret_role = "Gamer"
WELCOME_CHANNEL_ID = 1393132051472842802
COINFLIP_CHANNEL_ID = 1393100231494602753
COUNTING_CHANNEL_ID = 1393114619777646683
GIVEAWAY_CHANNEL_ID = 1481864311373565983
GIVEAWAY_START_CHANNEL_ID = 1316295531160539179
GREEN_CHECK = '✅'
RED_X = '❌'
determine_flip = [1, 0]
counting_state = {}
role_all = "Clowns"

# Helper: Convert time string (e.g. 30s, 2m) to seconds
def convert_time_to_seconds(time_str):
    match = re.match(r"^(\d+)([smhd])$", time_str.lower())
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    return {
        "s": value,
        "m": value * 60,
        "h": value * 3600,
        "d": value * 86400
    }.get(unit)

# Helper: Add suffix to a number (e.g., 1st, 2nd)
def get_ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

# Event: Welcome new member
@bot.event
async def on_member_join(member):
    guild = member.guild
    welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
    clown_role = discord.utils.get(guild.roles, name="Clowns")

    if clown_role:
        try:
            await member.add_roles(clown_role)
        except discord.Forbidden:
            print(f"❌ Missing permissions to add 'Clown' role to {member.name}")
        except Exception as e:
            print(f"❌ Error adding 'Clown' role: {e}")

    if welcome_channel:
        member_number = len(guild.members)
        ordinal = get_ordinal(member_number)
        await welcome_channel.send(
            f"Hello, {member.name}, welcome to Stradi's Shack. "
            f"You are the {ordinal} member."
        )

# Event: Handle counting and commands
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Counting logic
    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            number = int(message.content.strip())
        except ValueError:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        if guild_id not in counting_state:
            counting_state[guild_id] = {
                'current': 0,
                'last_user': None,
                'best': 0
            }

        state = counting_state[guild_id]
        expected = state['current'] + 1

        if number != expected:
            await message.add_reaction(RED_X)
            await message.channel.send(
                f"{message.author.mention} RUINED IT AT **{state['current']}**!! "
                f"Next number is **{expected}**. **Wrong number.**"
            )
            state['current'] = 0
            state['last_user'] = None
            return

        if state['last_user'] == user_id:
            await message.add_reaction(RED_X)
            await message.channel.send(
                f"{message.author.mention} RUINED IT AT **{state['current']}**!! "
                f"**Double posting.**"
            )
            state['current'] = 0
            state['last_user'] = None
            return

        await message.add_reaction(GREEN_CHECK)
        state['current'] += 1
        state['last_user'] = user_id
        if state['current'] > state['best']:
            state['best'] = state['current']

    await bot.process_commands(message)

# Event: Deleted message in counting
@bot.event
async def on_message_delete(message):
    if message.channel.id != COUNTING_CHANNEL_ID or message.author.bot:
        return

    try:
        deleted_number = int(message.content.strip())
    except (ValueError, AttributeError):
        return

    guild_id = message.guild.id
    state = counting_state.get(guild_id)

    if not state or deleted_number > state['current']:
        return

    expected = state['current'] + 1
    embed = discord.Embed(
        title="⚠️ A number was deleted",
        description=(
            f"{message.author.mention} has deleted their number: **{deleted_number}**\n\n"
            f"The next number is **{expected}**."
        ),
        color=discord.Color.orange()
    )
    await message.channel.send(embed=embed)

# Commands

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async def assign(ctx):
    role = discord.utils.find(lambda r: r.name.lower() == secret_role.lower(), ctx.guild.roles)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention} is now assigned to {secret_role}")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
async def remove(ctx):
    role = discord.utils.find(lambda r: r.name.lower() == secret_role.lower(), ctx.guild.roles)
    if role:
        await ctx.author.remove_roles(role)
        await ctx.send(f"{ctx.author.mention} has had the {secret_role} removed")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
async def dm(ctx, *, msg):
    await ctx.author.send(f"You said: {msg}")

@bot.command()
async def reply(ctx):
    await ctx.reply("This is a reply to your message!")

@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")

@bot.command()
@commands.has_role(secret_role)
async def secret(ctx):
    await ctx.send("Welcome to the club!")

@secret.error
async def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to do that!")

# Coinflipping logic
@bot.command()
async def coinflip(ctx):
    # if ctx.channel.id != COINFLIP_CHANNEL_ID:
    #     await ctx.message.delete()
    #     return

    result = "Heads" if random.choice(determine_flip) == 1 else "Tails"
    embed = discord.Embed(
        title="Coinflip",
        description=f"{ctx.author.mention} Flipped coin, we got **{result}**!"
    )
    await ctx.send(embed=embed)

# Giveaway logic
@bot.command()
async def gstart(ctx, time: str, winners: int, *, prize: str):
    # Silently delete the message if not in the correct channel
    if ctx.channel.id != GIVEAWAY_START_CHANNEL_ID:
        await ctx.message.delete()
        return

    seconds = convert_time_to_seconds(time)
    if seconds is None:
        await ctx.send("❌ Invalid time format. Use `s`, `m`, `h`, or `d` (e.g. 30s, 1m, 2h, 1d).")
        return

    embed = discord.Embed(
        title="🎉 Giveaway Started!",
        description=(
            f"**Prize:** {prize}\n"
            f"**Hosted by:** {ctx.author.mention}\n"
            f"React with 🎉 to enter!\n\n"
            f"**Duration:** {time}\n"
            f"**Winners:** {winners}"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Giveaway ends soon. React now!")

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if giveaway_channel is None:
        return  # Optionally log this internally

    giveaway_message = await giveaway_channel.send(content="<@&1393364864331808960>", embed=embed)
    await giveaway_message.add_reaction("🎉")

    await asyncio.sleep(seconds)

    try:
        giveaway_message = await giveaway_channel.fetch_message(giveaway_message.id)
    except Exception as e:
        await giveaway_channel.send("❌ Giveaway ended, but I couldn't fetch the message.")
        print(f"[Giveaway] Fetch error: {e}")
        return

    reaction = discord.utils.get(giveaway_message.reactions, emoji="🎉")
    if not reaction:
        await giveaway_channel.send("❌ No one reacted. Giveaway cancelled.")
        return

    try:
        users = [user async for user in reaction.users() if not user.bot]
    except Exception as e:
        await giveaway_channel.send("❌ Could not read users from reactions.")
        print(f"[Giveaway] User fetch error: {e}")
        return

    if not users:
        await giveaway_channel.send("❌ No valid users reacted. Giveaway cancelled.")
        return

    if len(users) < winners:
        winners = len(users)

    selected = random.sample(users, winners)
    winner_mentions = ", ".join(user.mention for user in selected)

    await giveaway_channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}** 🎁")


# Run the bot
bot.run(token, log_handler=handler, log_level=logging.INFO)
