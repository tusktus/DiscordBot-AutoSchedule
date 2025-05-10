import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from db import save_schedule, get_all_schedules

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
guild = discord.Object(id=GUILD_ID)

@bot.tree.command(name="schedule_create", description="候補日をカンマ区切りで入力", guild=guild)
@app_commands.describe(dates="例: 5/15,5/16,5/17")
async def schedule_create(interaction: discord.Interaction, dates: str):
    date_list = [d.strip() for d in dates.split(",")]
    save_schedule(interaction.user.id, date_list)
    await interaction.response.send_message(f"{len(date_list)} 件の候補日を保存しました。")

@bot.tree.command(name="schedule_list", description="保存されたスケジュールを表示", guild=guild)
async def schedule_list(interaction: discord.Interaction):
    all_schedules = get_all_schedules()
    if not all_schedules:
        await interaction.response.send_message("スケジュールはまだ登録されていません。")
        return

    lines = []
    for entry in all_schedules:
        user = await bot.fetch_user(entry["user_id"])
        dates = ", ".join(entry["dates"])
        lines.append(f"{user.name}: {dates}")

    message = "\n".join(lines)
    await interaction.response.send_message(f"登録済みスケジュール:\n{message}")

@bot.event
async def on_ready():
    await bot.tree.sync(guild=guild)
    print(f"Bot logged in as {bot.user}")
    print("Commands synced")

bot.run(TOKEN)
