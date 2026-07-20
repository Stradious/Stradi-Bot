"""Stradious: a configurable Discord community bot."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from datetime import timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


def env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer Discord ID") from exc


def env_int_list(name: str, default: str = "") -> tuple[int, ...]:
    values = os.getenv(name, default)
    try:
        return tuple(int(value.strip()) for value in values.split(",") if value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a comma-separated list of Discord IDs") from exc


def env_str_list(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")
COMMAND_GUILD_IDS = env_int_list(
    "COMMAND_GUILD_IDS", "982318902530949180,1392780437734293615"
)
WELCOME_CHANNEL_ID = env_int("WELCOME_CHANNEL_ID", 1393132051472842802)
BOOST_CHANNEL_ID = env_int("BOOST_CHANNEL_ID")
BOOST_CHANNEL_NAMES = env_str_list("BOOST_CHANNEL_NAMES", "boosts,server-boosts,boost")
COUNTING_CHANNEL_ID = env_int("COUNTING_CHANNEL_ID", 1393114619777646683)
GIVEAWAY_CHANNEL_ID = env_int("GIVEAWAY_CHANNEL_ID", 1481864311373565983)
GIVEAWAY_ROLE_ID = env_int("GIVEAWAY_ROLE_ID", 1528066539721330698)
GIVEAWAY_ROLE_NAME = os.getenv("GIVEAWAY_ROLE_NAME", "Giveaways").strip()
BOT_NICKNAME = os.getenv("BOT_NICKNAME", "Strad's Servant").strip()
MEMBER_ROLE = os.getenv("MEMBER_ROLE", "Clowns")
SECRET_ROLE = os.getenv("SECRET_ROLE", "Gamer")
STATE_FILE = Path(os.getenv("STATE_FILE", "data/counting.json"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("stradious")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


@bot.event
async def setup_hook() -> None:
    try:
        global_commands = await bot.tree.sync()
        logger.info("Synced %s global slash command(s)", len(global_commands))
        for guild_id in COMMAND_GUILD_IDS:
            guild = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild)
            guild_commands = await bot.tree.sync(guild=guild)
            logger.info("Synced %s slash command(s) to guild %s", len(guild_commands), guild_id)
    except discord.HTTPException:
        logger.exception("Could not sync slash commands")


def load_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not load counting state")
        return {}


counting_state = load_state()


def save_state() -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(counting_state, indent=2), encoding="utf-8")
        temporary.replace(STATE_FILE)
    except OSError:
        logger.exception("Could not save counting state")


def convert_time_to_seconds(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)([smhd])", value.strip(), re.IGNORECASE)
    if not match:
        return None
    amount, unit = match.groups()
    return int(amount) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit.lower()]


def get_ordinal(number: int) -> str:
    suffix = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def normalize_channel_name(name: str) -> str:
    return name.strip().casefold().lstrip("#").replace(" ", "-")


def find_text_channel_by_name(guild: discord.Guild, names: tuple[str, ...]) -> discord.TextChannel | None:
    expected_names = {normalize_channel_name(name) for name in names}
    return discord.utils.find(
        lambda channel: normalize_channel_name(channel.name) in expected_names,
        guild.text_channels,
    )


def get_boost_channel(guild: discord.Guild) -> discord.TextChannel | None:
    if BOOST_CHANNEL_ID:
        if BOOST_CHANNEL_ID == WELCOME_CHANNEL_ID:
            logger.warning(
                "BOOST_CHANNEL_ID matches WELCOME_CHANNEL_ID in %s; looking up boost channel by name",
                guild.name,
            )
        else:
            channel = guild.get_channel(BOOST_CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                return channel
            logger.warning("Configured BOOST_CHANNEL_ID %s was not found in %s", BOOST_CHANNEL_ID, guild.name)

    channel = find_text_channel_by_name(guild, BOOST_CHANNEL_NAMES)
    if channel:
        return channel

    logger.warning(
        "No boost thank-you channel found in %s. Configure BOOST_CHANNEL_ID or create #boosts.",
        guild.name,
    )
    return None


@bot.event
async def on_ready() -> None:
    if BOT_NICKNAME:
        for guild in bot.guilds:
            member = guild.me
            if member and member.nick != BOT_NICKNAME:
                try:
                    await member.edit(nick=BOT_NICKNAME, reason="Configured Stradious bot nickname")
                except discord.Forbidden:
                    logger.warning("Missing permission to change nickname in %s", guild.name)
                except discord.HTTPException:
                    logger.exception("Could not change nickname in %s", guild.name)
    logger.info("Ready as %s (%s), serving %s guild(s)", bot.user, bot.user.id, len(bot.guilds))


@bot.event
async def on_member_join(member: discord.Member) -> None:
    role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE)
    if role:
        try:
            await member.add_roles(role, reason="Default Stradious member role")
        except discord.Forbidden:
            logger.warning("Missing permission to add role %s", MEMBER_ROLE)
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        total = member.guild.member_count or len(member.guild.members)
        await channel.send(
            f"Welcome to **{member.guild.name}**, {member.mention}! "
            f"You’re our **{get_ordinal(total)}** member."
        )


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    if before.premium_since is not None or after.premium_since is None:
        return

    channel = get_boost_channel(after.guild)
    if channel is None:
        return

    embed = discord.Embed(
        title="🚀 Thank you for boosting!",
        description=(
            f"{after.mention} just boosted **{after.guild.name}**!\n\n"
            "Your support helps the whole server unlock better perks. 💜"
        ),
        color=discord.Color.fuchsia(),
    )
    embed.set_thumbnail(url=after.display_avatar.url)
    embed.set_footer(text="You’re an absolute legend.")
    try:
        await channel.send(
            content=after.mention,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=[after]),
        )
    except discord.Forbidden:
        logger.warning("Missing permission to thank boosters in channel %s", channel.id)
    except discord.HTTPException:
        logger.exception("Could not send boost thank-you in %s", after.guild.name)


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if message.guild and message.channel.id == COUNTING_CHANNEL_ID:
        try:
            number = int(message.content.strip())
        except ValueError:
            await bot.process_commands(message)
            return

        state = counting_state.setdefault(
            str(message.guild.id), {"current": 0, "last_user": None, "best": 0}
        )
        expected = state["current"] + 1
        same_user = state["last_user"] == message.author.id
        if number != expected or same_user:
            await message.add_reaction("❌")
            reason = "double posting" if same_user else f"expected **{expected}**"
            await message.channel.send(
                f"{message.author.mention} broke the count at **{state['current']}** "
                f"({reason}). Start again at **1**!"
            )
            state.update({"current": 0, "last_user": None})
        else:
            await message.add_reaction("✅")
            state.update({"current": number, "last_user": message.author.id})
            state["best"] = max(state["best"], number)
        save_state()
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    error = getattr(error, "original", error)
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing `{error.param.name}`. Try `{PREFIX}help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"I couldn’t understand that value. Try `{PREFIX}help`.")
    elif isinstance(error, (commands.MissingRole, commands.NoPrivateMessage)):
        await ctx.send("You don’t have permission to use that command here.")
    else:
        logger.error("Command failed: %s", error, exc_info=error)
        await ctx.send("Something went wrong while running that command.")


@bot.hybrid_command(name="help", description="Show all Strad's Servant commands")
async def help_command(ctx: commands.Context) -> None:
    embed = discord.Embed(
        title=f"{BOT_NICKNAME or 'Stradious'} commands",
        description="Community tools, games, and giveaways.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name=f"{PREFIX}hello", value="Say hello", inline=True)
    embed.add_field(name=f"{PREFIX}coinflip", value="Flip a coin", inline=True)
    embed.add_field(name=f"{PREFIX}count", value="Show counting progress", inline=True)
    embed.add_field(name=f"{PREFIX}boosters", value="Show current server boosters", inline=True)
    embed.add_field(name=f"{PREFIX}poll <question>", value="Create a 👍 / 👎 poll", inline=False)
    embed.add_field(name=f"{PREFIX}assign / {PREFIX}remove", value=f"Manage the {SECRET_ROLE} role", inline=False)
    embed.add_field(name=f"{PREFIX}secret", value=f"Use the secret command with the {SECRET_ROLE} role", inline=False)
    embed.add_field(
        name=f"{PREFIX}gstart <time> <winners> <prize>",
        value="Start a giveaway from any server channel",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(description="Say hello")
async def hello(ctx: commands.Context) -> None:
    await ctx.send(f"Hello, {ctx.author.mention}! 👋")


@bot.hybrid_command(description=f"Give yourself the {SECRET_ROLE} role")
@commands.guild_only()
async def assign(ctx: commands.Context) -> None:
    role = discord.utils.get(ctx.guild.roles, name=SECRET_ROLE)
    if not role:
        await ctx.send(f"The **{SECRET_ROLE}** role does not exist.")
        return
    await ctx.author.add_roles(role, reason="Self-assigned through Stradious")
    await ctx.send(f"Added **{SECRET_ROLE}** to {ctx.author.mention}.")


@bot.hybrid_command(description=f"Remove the {SECRET_ROLE} role from yourself")
@commands.guild_only()
async def remove(ctx: commands.Context) -> None:
    role = discord.utils.get(ctx.guild.roles, name=SECRET_ROLE)
    if not role:
        await ctx.send(f"The **{SECRET_ROLE}** role does not exist.")
        return
    await ctx.author.remove_roles(role, reason="Self-removed through Stradious")
    await ctx.send(f"Removed **{SECRET_ROLE}** from {ctx.author.mention}.")


@bot.hybrid_command(description="Create a thumbs-up or thumbs-down poll")
async def poll(ctx: commands.Context, *, question: str) -> None:
    embed = discord.Embed(title="📊 New poll", description=question, color=discord.Color.blurple())
    embed.set_footer(text=f"Started by {ctx.author.display_name}")
    poll_message = await ctx.send(embed=embed)
    for emoji in ("👍", "👎"):
        await poll_message.add_reaction(emoji)


@bot.hybrid_command(description="Show the current and best counting totals")
@commands.guild_only()
async def count(ctx: commands.Context) -> None:
    state = counting_state.get(str(ctx.guild.id), {"current": 0, "best": 0})
    await ctx.send(f"Current count: **{state['current']}** · Server best: **{state['best']}**")


@bot.hybrid_command(description="Show everyone currently boosting this server")
@commands.guild_only()
async def boosters(ctx: commands.Context) -> None:
    members = sorted(
        (member for member in ctx.guild.members if member.premium_since is not None),
        key=lambda member: member.premium_since,
    )
    if not members:
        await ctx.send("This server doesn’t have any active boosters yet.")
        return

    booster_list = "\n".join(
        f"💜 {member.mention} — since {discord.utils.format_dt(member.premium_since, 'D')}"
        for member in members
    )
    embed = discord.Embed(
        title=f"🚀 {ctx.guild.name} Boosters",
        description=booster_list[:4096],
        color=discord.Color.fuchsia(),
    )
    embed.set_footer(text=f"{len(members)} active booster(s) — thank you!")
    await ctx.send(embed=embed)


@bot.hybrid_command(description=f"Use the secret command with the {SECRET_ROLE} role")
@commands.has_role(SECRET_ROLE)
async def secret(ctx: commands.Context) -> None:
    await ctx.send("Welcome to the club! 🎮")


@bot.hybrid_command(description="Flip a coin")
async def coinflip(ctx: commands.Context) -> None:
    result = random.choice(("Heads", "Tails"))
    embed = discord.Embed(title="🪙 Coin flip", description=f"{ctx.author.mention} flipped **{result}**!")
    await ctx.send(embed=embed)


@bot.hybrid_command(description="Start a giveaway with an optional image")
@app_commands.describe(
    duration="How long the giveaway lasts, such as 30s, 10m, 2h, or 7d",
    winners="Number of winners from 1 to 20",
    prize="What the winner receives",
    image="Optional image shown in the giveaway embed",
)
@commands.guild_only()
async def gstart(
    ctx: commands.Context,
    duration: str,
    winners: int,
    *,
    prize: str,
    image: discord.Attachment | None = None,
) -> None:
    seconds = convert_time_to_seconds(duration)
    if not seconds or seconds > 30 * 86400:
        await ctx.send("Use `30s`, `10m`, `2h`, or `7d` (maximum 30 days).")
        return
    if not 1 <= winners <= 20:
        await ctx.send("Winner count must be between 1 and 20.")
        return
    channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if channel is None:
        await ctx.send("The giveaway channel is not configured correctly.")
        return

    giveaway_guild = channel.guild
    giveaway_role = giveaway_guild.get_role(GIVEAWAY_ROLE_ID)
    if giveaway_role is None and GIVEAWAY_ROLE_NAME:
        expected_role_name = GIVEAWAY_ROLE_NAME.casefold()
        giveaway_role = discord.utils.find(
            lambda role: role.name.casefold() == expected_role_name
            or role.name.casefold().endswith(expected_role_name),
            giveaway_guild.roles,
        )
    if giveaway_role is None:
        await ctx.send(
            f"I couldn’t find the **{GIVEAWAY_ROLE_NAME or 'Giveaways'}** role. "
            "Check the role name or configure `GIVEAWAY_ROLE_ID`."
        )
        return

    bot_member = giveaway_guild.me
    can_ping_unmentionable_roles = bool(
        bot_member and channel.permissions_for(bot_member).mention_everyone
    )
    if not giveaway_role.mentionable and not can_ping_unmentionable_roles:
        await ctx.send(
            f"I found {giveaway_role.mention}, but Discord won’t let me ping it. "
            "Make that role mentionable or give me **Mention @everyone, @here, and All Roles**."
        )
        return

    giveaway_file = None
    if image is not None:
        content_type = image.content_type or ""
        image_suffixes = (".png", ".jpg", ".jpeg", ".gif", ".webp")
        if not content_type.startswith("image/") and not image.filename.lower().endswith(image_suffixes):
            await ctx.send("The giveaway attachment must be a PNG, JPG, GIF, or WEBP image.")
            return
        try:
            giveaway_file = await image.to_file()
        except discord.HTTPException:
            logger.exception("Could not download giveaway image")
            await ctx.send("I couldn’t process that image. Try uploading it again.")
            return

    end_time = discord.utils.utcnow() + timedelta(seconds=seconds)
    embed = discord.Embed(
        title="🎉 Giveaway",
        description=(
            f"**{prize}**\n\nReact with 🎉 to enter.\n"
            f"Ends {discord.utils.format_dt(end_time, 'R')} · **{winners}** winner(s)\n"
            f"Hosted by {ctx.author.mention}"
        ),
        color=discord.Color.blurple(),
    )
    if giveaway_file is not None:
        embed.set_image(url=f"attachment://{giveaway_file.filename}")
        giveaway = await channel.send(
            content=giveaway_role.mention,
            embed=embed,
            file=giveaway_file,
            allowed_mentions=discord.AllowedMentions(roles=[giveaway_role]),
        )
    else:
        giveaway = await channel.send(
            content=giveaway_role.mention,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=[giveaway_role]),
        )
    await giveaway.add_reaction("🎉")
    await ctx.send(f"Giveaway started in {channel.mention}.")

    await asyncio.sleep(seconds)
    giveaway = await channel.fetch_message(giveaway.id)
    ended_embed = giveaway.embeds[0].copy() if giveaway.embeds else embed.copy()
    ended_embed.description = (
        f"**{prize}**\n\nThis giveaway has ended.\n"
        f"Ended {discord.utils.format_dt(end_time, 'R')} · **{winners}** winner(s)\n"
        f"Hosted by {ctx.author.mention}"
    )
    try:
        await giveaway.edit(embed=ended_embed)
    except discord.HTTPException:
        logger.exception("Could not mark giveaway %s as ended", giveaway.id)

    reaction = discord.utils.get(giveaway.reactions, emoji="🎉")
    entrants = [user async for user in reaction.users() if not user.bot] if reaction else []
    if not entrants:
        await channel.send(f"The giveaway for **{prize}** ended with no entries.")
        return
    selected = random.sample(entrants, min(winners, len(entrants)))
    mentions = ", ".join(user.mention for user in selected)
    await channel.send(f"🎉 Congratulations {mentions}! You won **{prize}**!")


def main() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example to .env and add your token.")
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
