import os
import json

import discord
from discord.ext import commands
from dotenv import load_dotenv

import pycantonese

from openai import OpenAI

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("DS_AK")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="$$",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    game = discord.Game("Use $$help")
    await bot.change_presence(activity=game)
    print(f"Logged in as {bot.user}")


def convert_to_jyutping(line):
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

    return " ".join(new_jyutping_result)

def query_deepseek(texts):
    """
    Accepts either a single string or a list of strings.
    Returns a single string if input was a string, or a list of strings if input was a list.
    """
    is_single = isinstance(texts, str)
    if is_single:
        texts = [texts]

    client = OpenAI(
        api_key=API_KEY,
        base_url="https://api.deepseek.com"
    )

    # Build a numbered list for the model
    lines_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))

    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": "You are a helpful assistant, please ensure all responses are only returned as a valid JSON."},
                {"role": "user", "content": f"You are a helpful Cantonese language assistant. For each of the following Cantonese texts, provide a natural, colloquial translation into English.\n\n"
                f"{lines_block}\n\n"
                "Return a JSON object with a single key 'translations' containing an array of strings in the same order as the input lines. "
                "If a specific line is not valid Cantonese text, use the string 'translation unavailable' for that entry.\n\n"
                "Example for 2 lines:\n"
                "```json\n"
                "{\n"
                '  "translations": ["hello", "thank you"]\n'
                "}\n"
                "```"},
            ],
            stream=False,
            extra_body={"thinking": {"type": "disabled"}}
        )

        result = json.loads(response.choices[0].message.content)
        translations = result.get("translations", [])

        # Ensure we have the same number of results
        while len(translations) < len(texts):
            translations.append("translation unavailable")

        if is_single:
            return translations[0]
        return translations

    except Exception as e:
        print(e)
        if is_single:
            return "translation unavailable"
        return ["translation unavailable"] * len(texts)


@bot.command(aliases=["j","J"])
async def jyutping(ctx, *, sentence: str):
    lines = sentence.splitlines()
    converted_lines = []

    for line in lines:
        if not line.strip():
            converted_lines.append("")
            continue

        converted_lines.append(convert_to_jyutping(line))

    jyutping_message = "\n".join(converted_lines)

    await ctx.send(jyutping_message)


@bot.command(aliases=["cj","CJ"])
async def cJyutping(ctx, *, sentence: str):
    lines = sentence.splitlines()
    combined_lines = []

    for line in lines:
        if not line.strip():
            combined_lines.append("")
            continue

        jyutping_text = convert_to_jyutping(line)
        combined_lines.append(f"{line}　{jyutping_text}")

    result_message = "\n".join(combined_lines)

    await ctx.send(result_message)

@bot.command(aliases=["cjt", "CJT"])
async def cJyutpingTranslate(ctx, *, sentence: str):
    lines = sentence.splitlines()

    # Separate non-empty lines for batch translation
    non_empty_indices = []
    non_empty_lines = []

    for i, line in enumerate(lines):
        if line.strip():
            non_empty_indices.append(i)
            non_empty_lines.append(line)

    translations = query_deepseek(non_empty_lines) if non_empty_lines else []

    # Map translations back to their original line positions
    translation_map = {}
    for idx, line_idx in enumerate(non_empty_indices):
        translation_map[line_idx] = translations[idx] if idx < len(translations) else "translation unavailable"

    combined_lines = []
    for i, line in enumerate(lines):
        if not line.strip():
            combined_lines.append("")
            continue

        jyutping_text = convert_to_jyutping(line)
        translation_text = translation_map.get(i, "translation unavailable")
        combined_lines.append(f"{line}　{jyutping_text}　{translation_text}")

    result_message = "\n".join(combined_lines)
    await ctx.send(result_message)


@bot.command()
async def correct(ctx, *, correction: str = None):
    if not correction:
        await ctx.send("Please provide a correction message.")
        return

    if not ctx.message.reference:
        await ctx.send("Please reply directly to the bot's message you want to correct.")
        return

    try:
        target_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except (discord.NotFound, discord.HTTPException):
        await ctx.send("Could not find the message you are trying to correct.")
        return

    if target_message.author != bot.user:
        await ctx.send("You can only correct messages sent by this bot.")
        return

    footer = f"\n-# *Jyutping last corrected by {ctx.author.name}*"
    new_content = f"{correction}{footer}"

    await target_message.edit(content=new_content)

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass


@bot.command(name="help")
async def commands_help(ctx):
    await ctx.send(
        "**Available command(s):**\n"
        "`$$jyutping <sentence>` (or `$$j/$$J <sentence>`) - Convert a sentence to Jyutping\n"
        "`$$cJyutping <sentence>` (or `$$cj/$$CJ <sentence>`) - Show original text with Jyutping appended to each line\n"
        "`$$cJyutpingTranslate <sentence>` (or `$$cjt/$$CJT <sentence>`) - Show original text with Jyutping and translation appended to each line\n"
        "`$$correct <correction>` - Reply to a bot message with this command to edit it\n"
    )


bot.run(TOKEN)