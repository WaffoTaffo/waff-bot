import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import pycantonese

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="$",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command(aliases=["j"])
async def jyutping(ctx, *, sentence: str):
    # Split the sentence into individual lines (preserves empty lines too)
    lines = sentence.splitlines()
    converted_lines = []

    for line in lines:
        if not line.strip():
            # Keep blank lines as empty strings
            converted_lines.append("")
            continue

        jyutping_result = pycantonese.characters_to_jyutping(line)
        new_jyutping_result = []

        for char, jp in jyutping_result:
            if jp:
                jp = jp.replace(" ", "")
                jp = (
                    jp.replace("1", "ˉ¹")
                    .replace("2", "⸍²")
                    .replace("3", "-₃")
                    .replace("4", "⸜₄")
                    .replace("5", "⸝₅")
                    .replace("6", "ˍ₆")
                )
            else:
                jp = char
            new_jyutping_result.append(jp)

        converted_lines.append(" ".join(new_jyutping_result))

    # Join the converted lines back together with newlines
    jyutping_message = "\n".join(converted_lines)

    await ctx.send(jyutping_message)

@bot.command()
async def correct(ctx, *, correction: str):
    # Check if the message is a reply to another message
    if not ctx.message.reference:
        await ctx.send("Please reply directly to the bot's message you want to correct.")
        return

    # Fetch the target message being replied to
    try:
        target_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except (discord.NotFound, discord.HTTPException):
        await ctx.send("Could not find the message you are trying to correct.")
        return

    # Ensure the target message was sent by this bot
    if target_message.author != bot.user:
        await ctx.send("You can only correct messages sent by this bot.")
        return

    # Strip out any existing footer line if this message was corrected before
    original_text = target_message.content.split("\n\n*Jyutping last corrected by")[0]

    # Append the new correction and the updated footer text
    footer = f"\n\n*Jyutping last corrected by {ctx.author.name}*"
    new_content = f"{correction}{footer}"

    # Edit the bot's original message
    await target_message.edit(content=new_content)

    # Delete the user's `$correct` command message to keep chat clean
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass


@bot.command(name="help")
async def commands_help(ctx):
    await ctx.send(
        "**Available command(s):**\n"
        "`$jyutping <sentence>` (or `$j <sentence>`) - Convert a sentence to Jyutping\n"
        "`$correct <correction>` - Reply to a bot message with this command to edit it\n"
    )


bot.run(TOKEN)