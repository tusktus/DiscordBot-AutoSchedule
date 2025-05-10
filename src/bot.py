import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")

# ギルドID（開発中のサーバーのIDに置き換えてください）
GUILD_ID = discord.Object(id=1370626910731894796)  # サーバーのID

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

mongo = MongoClient(MONGODB_URI)
db = mongo["schedule_bot"]
schedules = db["schedules"]

@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD_ID)
    print(f"✅ Logged in as {bot.user}")

# スケジュール作成コマンド
@app_commands.command(name="schedule_create", description="スケジュールを作成")
@app_commands.describe(title="イベント名", dates="候補日(カンマ区切りで複数指定)")
async def create_schedule(interaction: discord.Interaction, title: str, dates: str):
    date_list = [d.strip() for d in dates.split(",")]
    schedule = {
        "title": title,
        "creator_id": interaction.user.id,
        "candidates": date_list,
        "votes": {}  # user_id: [参加可能な日]
    }
    inserted = schedules.insert_one(schedule)
    await interaction.response.send_message(f"🗓 スケジュール作成: {title}\n候補日: {', '.join(date_list)}\nID: `{inserted.inserted_id}`")

# 投票コマンド
@app_commands.command(name="schedule_vote", description="スケジュールに投票")
@app_commands.describe(schedule_id="スケジュールID", available_dates="参加できる日(カンマ区切り)")
async def vote_schedule(interaction: discord.Interaction, schedule_id: str, available_dates: str):
    schedule = schedules.find_one({"_id": schedule_id})
    if not schedule:
        await interaction.response.send_message("❌ スケジュールが見つかりません。")
        return

    dates = [d.strip() for d in available_dates.split(",")]
    schedules.update_one(
        {"_id": schedule_id},
        {"$set": {f"votes.{str(interaction.user.id)}": dates}}
    )
    await interaction.response.send_message(f"✅ 投票完了！あなたの参加可能日: {', '.join(dates)}")

# 結果表示
@app_commands.command(name="schedule_result", description="スケジュールの集計結果を表示")
@app_commands.describe(schedule_id="スケジュールID")
async def show_result(interaction: discord.Interaction, schedule_id: str):
    schedule = schedules.find_one({"_id": schedule_id})
    if not schedule:
        await interaction.response.send_message("❌ スケジュールが見つかりません。")
        return

    vote_counts = {date: 0 for date in schedule["candidates"]}
    for _, user_dates in schedule.get("votes", {}).items():
        for d in user_dates:
            if d in vote_counts:
                vote_counts[d] += 1

    result_text = f"📊 スケジュール結果 ({schedule['title']})\n"
    for date, count in vote_counts.items():
        result_text += f"{date}: {count}人\n"

    await interaction.response.send_message(result_text)

# コマンド登録
bot.tree.add_command(create_schedule, guild=GUILD_ID)
bot.tree.add_command(vote_schedule, guild=GUILD_ID)
bot.tree.add_command(show_result, guild=GUILD_ID)

bot.run(DISCORD_TOKEN)
