import os
import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGODB_URI")

# MongoDB接続
client = MongoClient(MONGO_URI)
db = client["discord_scheduler"]
collection = db["schedules"]

# Bot準備
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- /create_schedule ---
@tree.command(name="create_schedule", description="スケジュールを作成します")
@app_commands.describe(event_name="イベント名", candidates="候補日程をカンマ区切りで（例：5/12 18:00, 5/13 19:00）")
async def create_schedule(interaction: discord.Interaction, event_name: str, candidates: str):
    candidate_list = [c.strip() for c in candidates.split(",") if c.strip()]
    if not candidate_list:
        await interaction.response.send_message("候補が正しく入力されていません。", ephemeral=True)
        return

    # MongoDBに保存
    collection.insert_one({
        "guild_id": interaction.guild.id,
        "channel_id": interaction.channel.id,
        "message_id": None,
        "event_name": event_name,
        "candidates": candidate_list,
        "responses": {}
    })

    await interaction.response.send_message(f"✅ イベント **{event_name}** を作成しました。\n候補: {', '.join(candidate_list)}")

# --- /respond_schedule ---
@tree.command(name="respond_schedule", description="スケジュールに回答します")
@app_commands.describe(event_name="イベント名")
async def respond_schedule(interaction: discord.Interaction, event_name: str):
    event = collection.find_one({"guild_id": interaction.guild.id, "event_name": event_name})
    if not event:
        await interaction.response.send_message("そのイベントは見つかりませんでした。", ephemeral=True)
        return

    options = [discord.SelectOption(label=c, value=c) for c in event["candidates"]]

    class ScheduleSelect(discord.ui.View):
        @discord.ui.select(placeholder="参加可能な候補日を選択（複数可）", options=options, min_values=1, max_values=len(options))
        async def select_callback(self, select, interaction2: discord.Interaction):
            selected = select.values
            # MongoDBに保存
            collection.update_one(
                {"_id": event["_id"]},
                {"$set": {f"responses.{interaction2.user.id}": selected}}
            )
            await interaction2.response.send_message(f"✅ 回答を保存しました: {', '.join(selected)}", ephemeral=True)

    await interaction.response.send_message(f"🗳 候補から選択してください：", view=ScheduleSelect(), ephemeral=True)

# --- /finalize_schedule ---
@tree.command(name="finalize_schedule", description="スケジュールを集計して最適な候補を決定します")
@app_commands.describe(event_name="イベント名", min_participants="最低参加人数（省略可）")
async def finalize_schedule(interaction: discord.Interaction, event_name: str, min_participants: int = 1):
    event = collection.find_one({"guild_id": interaction.guild.id, "event_name": event_name})
    if not event:
        await interaction.response.send_message("そのイベントは見つかりませんでした。", ephemeral=True)
        return

    # 集計
    tally = {c: 0 for c in event["candidates"]}
    for response in event["responses"].values():
        for c in response:
            tally[c] += 1

    sorted_candidates = sorted(tally.items(), key=lambda x: x[1], reverse=True)
    result_lines = []
    for c, count in sorted_candidates:
        if count >= min_participants:
            result_lines.append(f"- **{c}**：{count}人")

    if result_lines:
        msg = "\n".join(result_lines)
        await interaction.response.send_message(f"✅ 最適なスケジュール候補（{min_participants}人以上参加可能）:\n{msg}")
    else:
        await interaction.response.send_message("⚠ 条件に合う候補が見つかりませんでした。")

# --- Bot起動 ---
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync failed: {e}")

bot.run(TOKEN)
