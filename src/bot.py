import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await bot.tree.sync()
    print("Synced commands")

@app_commands.command(name="hello", description="テスト挨拶コマンド")
async def hello(interaction: discord.Interaction):
    try:
        # 応答を保留してからメッセージを送る
        await interaction.response.defer()
        await interaction.followup.send("こんにちは！")
    except discord.errors.NotFound as e:
        print(f"Error while responding to interaction: {e}")
        await interaction.followup.send("エラーが発生しました。もう一度試してください。")

bot.tree.add_command(hello)

import os
bot.run(os.getenv("DISCORD_TOKEN"))
