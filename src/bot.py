# Discord スケジュール調整Bot
# main.py

import os
import discord
from discord.ext import commands
from pymongo import MongoClient
from datetime import datetime
import pytz
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む
load_dotenv()

# 環境変数から設定を取得
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')

# Botの設定
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# MongoDBクライアントの設定
client = MongoClient(MONGODB_URI)
db = client['schedule_bot']
events_collection = db['events']
responses_collection = db['responses']

# タイムゾーンの設定 (日本時間)
JST = pytz.timezone('Asia/Tokyo')

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')
    
@bot.command(name='create_event')
async def create_event(ctx, title: str, date: str, *time_options):
    """
    イベントを作成するコマンド
    使用例: !create_event "会議" 2025-05-20 13:00 15:00 17:00
    """
    try:
        # 日付の検証
        event_date = datetime.strptime(date, '%Y-%m-%d')
        event_date = JST.localize(event_date)
        
        # イベント情報をMongoDBに保存
        event_id = events_collection.insert_one({
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'creator_id': ctx.author.id,
            'title': title,
            'date': event_date,
            'time_options': list(time_options),
            'created_at': datetime.now(JST)
        }).inserted_id
        
        # レスポンスメッセージの作成
        embed = discord.Embed(
            title=f"📅 スケジュール調整: {title}",
            description=f"日付: {date}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="時間オプション", value="\n".join([f"{i+1}. {time}" for i, time in enumerate(time_options)]))
        embed.add_field(name="参加方法", value="下記のコマンドで参加可能な時間を登録してください：\n"
                                        f"!respond {event_id} [時間番号(複数可)] \n"
                                        f"例: !respond {event_id} 1 3")
        
        embed.set_footer(text=f"イベントID: {event_id}")
        
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"形式エラー: 日付は'YYYY-MM-DD'形式で入力してください。\n例: !create_event \"ミーティング\" 2025-05-20 13:00 15:00 17:00")

@bot.command(name='respond')
async def respond_to_event(ctx, event_id: str, *time_indices):
    """
    イベントの時間オプションに対して応答するコマンド
    使用例: !respond 507f1f77bcf86cd799439011 1 3
    """
    try:
        # ObjectIdの検証
        from bson.objectid import ObjectId
        obj_id = ObjectId(event_id)
        
        # イベントの検索
        event = events_collection.find_one({'_id': obj_id})
        if not event:
            await ctx.send("指定されたイベントが見つかりません。")
            return
            
        # 時間インデックスの検証
        selected_times = []
        for idx in time_indices:
            try:
                index = int(idx) - 1
                if 0 <= index < len(event['time_options']):
                    selected_times.append(event['time_options'][index])
                else:
                    await ctx.send(f"無効な時間オプション番号です: {idx}")
                    return
            except ValueError:
                await ctx.send(f"無効な入力です: {idx}。数字を入力してください。")
                return
                
        # 既存の応答を更新または新規作成
        responses_collection.update_one(
            {
                'event_id': obj_id,
                'user_id': ctx.author.id
            },
            {
                '$set': {
                    'username': ctx.author.display_name,
                    'selected_times': selected_times,
                    'updated_at': datetime.now(JST)
                }
            },
            upsert=True
        )
        
        await ctx.send(f"{ctx.author.mention} さんの回答を登録しました。")
        
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='show_results')
async def show_results(ctx, event_id: str):
    """
    イベントの調整結果を表示するコマンド
    使用例: !show_results 507f1f77bcf86cd799439011
    """
    try:
        # ObjectIdの検証
        from bson.objectid import ObjectId
        obj_id = ObjectId(event_id)
        
        # イベントの検索
        event = events_collection.find_one({'_id': obj_id})
        if not event:
            await ctx.send("指定されたイベントが見つかりません。")
            return
            
        # イベントの応答を検索
        responses = list(responses_collection.find({'event_id': obj_id}))
        
        # 結果の集計
        time_counts = {time: 0 for time in event['time_options']}
        user_responses = {}
        
        for response in responses:
            user_responses[response['username']] = response['selected_times']
            for time in response['selected_times']:
                if time in time_counts:
                    time_counts[time] += 1
        
        # 結果の表示
        embed = discord.Embed(
            title=f"📊 調整結果: {event['title']}",
            description=f"日付: {event['date'].strftime('%Y-%m-%d')}",
            color=discord.Color.green()
        )
        
        # 時間ごとの参加者数
        time_results = []
        for i, time in enumerate(event['time_options']):
            count = time_counts[time]
            time_results.append(f"{i+1}. {time}: {count}人")
        
        embed.add_field(name="時間別参加者数", value="\n".join(time_results), inline=False)
        
        # 参加者ごとの選択時間
        users_results = []
        for username, times in user_responses.items():
            users_results.append(f"{username}: {', '.join(times)}")
        
        if users_results:
            embed.add_field(name="参加者一覧", value="\n".join(users_results), inline=False)
        else:
            embed.add_field(name="参加者一覧", value="まだ回答がありません。", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='delete_event')
async def delete_event(ctx, event_id: str):
    """
    イベントを削除するコマンド（作成者のみ可能）
    使用例: !delete_event 507f1f77bcf86cd799439011
    """
    try:
        # ObjectIdの検証
        from bson.objectid import ObjectId
        obj_id = ObjectId(event_id)
        
        # イベントの検索
        event = events_collection.find_one({'_id': obj_id})
        if not event:
            await ctx.send("指定されたイベントが見つかりません。")
            return
            
        # 作成者の確認
        if event['creator_id'] != ctx.author.id:
            await ctx.send("イベントの削除は作成者のみが実行できます。")
            return
            
        # イベントと関連する応答の削除
        events_collection.delete_one({'_id': obj_id})
        responses_collection.delete_many({'event_id': obj_id})
        
        await ctx.send(f"イベント '{event['title']}' を削除しました。")
        
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='help_schedule')
async def help_command(ctx):
    """
    ヘルプコマンド
    """
    embed = discord.Embed(
        title="📅 スケジュール調整Bot ヘルプ",
        description="スケジュール調整のためのコマンド一覧",
        color=discord.Color.blue()
    )
    
    commands_info = [
        ("!create_event [タイトル] [日付] [時間...]", "新しいイベントを作成します\n例: !create_event \"会議\" 2025-05-20 13:00 15:00 17:00"),
        ("!respond [イベントID] [時間番号...]", "イベントに応答します\n例: !respond 507f1f77bcf86cd799439011 1 3"),
        ("!show_results [イベントID]", "イベントの応答結果を表示します"),
        ("!delete_event [イベントID]", "イベントを削除します（作成者のみ）"),
        ("!help_schedule", "このヘルプメッセージを表示します")
    ]
    
    for cmd, desc in commands_info:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)