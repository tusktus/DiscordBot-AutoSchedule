# 環境設定とデプロイ手順

## 背景
ff14の固定活動にて、スプレッドシートに入力するのが面倒だったのでなんとなく作ってみたくなったもの。

## 1. 必要なファイル

### requirements.txt
```
discord.py==2.3.2
pymongo==4.6.1
python-dotenv==1.0.0
pytz==2023.3
```

### .env
```
DISCORD_TOKEN=あなたのDiscordボットトークン
MONGODB_URI=あなたのMongoDBの接続URI
GUILD_ID=あなたのDiscordサーバーID
```

### Dockerfile（Renderでのデプロイ用）
```Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

## 2. Discord Bot のセットアップ

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリック
3. アプリケーション名を入力し、「Create」をクリック
4. 左サイドバーの「Bot」をクリック
5. 「Add Bot」→「Yes, do it!」
6. トークンを「Reset Token」で生成し、コピーして`.env`ファイルの`DISCORD_TOKEN`に設定
7. 「MESSAGE CONTENT INTENT」をONに設定
8. 左サイドバーの「OAuth2」→「URL Generator」をクリック
9. SCOPESで「bot」を選択
10. BOT PERMISSIONSで以下を選択:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Add Reactions
11. 生成されたURLをコピーし、ブラウザで開いてボットをサーバーに招待

## 3. MongoDB のセットアップ

1. [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) にアクセスしてアカウント作成またはログイン
2. 「Create」→「Shared」（無料プラン）→「Create Cluster」
3. リージョンとプロバイダを選択して「Create Cluster」
4. 「Database Access」でユーザーを作成（パスワードを記録）
5. 「Network Access」でIPアドレスを追加（「Allow Access from Anywhere」でも可）
6. クラスタの「Connect」ボタンをクリック
7. 「Connect your application」を選択
8. 接続文字列をコピーし、`<password>`をあなたのパスワードに置き換えて`.env`ファイルの`MONGODB_URI`に設定

## 4. ローカルでのテスト方法

```bash
# リポジトリをクローンまたは作成
mkdir discord-schedule-bot
cd discord-schedule-bot

# 必要なファイルを作成
# main.py, requirements.txt, .env, Dockerfileを作成

# 仮想環境を作成して有効化（オプション）
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# ボットを実行
python main.py
```

## 5. Renderでのデプロイ手順

1. [Render](https://render.com/) にアクセスしてアカウント作成
2. ダッシュボードから「New」→「Web Service」を選択
3. GitHubリポジトリを接続するか、「Public Git repository」を選択して以下の情報を入力:
   - Repository: あなたのリポジトリURL
   - Name: サービス名（例: discord-schedule-bot）
   - Runtime: Docker
   - Branch: main （または使用するブランチ）
   - Root Directory: （空白でOK）
4. 「Advanced」を開き、環境変数を追加:
   - DISCORD_TOKEN: あなたのDiscordボットトークン
   - MONGODB_URI: あなたのMongoDBの接続URI
   - GUILD_ID: あなたのDiscordサーバーID（数字のみ）
5. 「Create Web Service」をクリック

## 6. 使用方法

ボットがサーバーに参加したら、以下のコマンドが使用できます：

1. `!help_schedule` - コマンド一覧とヘルプを表示
2. `!create_event "タイトル" 日付 時間1 時間2...` - 新しいイベントを作成
   例: `!create_event "週次ミーティング" 2025-05-20 13:00 15:00 17:00`
3. `!respond イベントID 時間番号1 時間番号2...` - イベントに応答
   例: `!respond 507f1f77bcf86cd799439011 1 3`
4. `!show_results イベントID` - イベントの調整結果を表示
5. `!delete_event イベントID` - イベントを削除（作成者のみ）

## 7. トラブルシューティング

1. ボットがオンラインにならない場合:
   - Discord Developer Portalで「MESSAGE CONTENT INTENT」が有効になっているか確認
   - `.env`ファイルのトークンが正しいか確認
   - Renderのログを確認

2. MongoDBに接続できない場合:
   - Network Accessの設定を確認（「Allow Access from Anywhere」を試す）
   - 接続文字列の`<password>`が正しく置き換えられているか確認

3. コマンドが応答しない場合:
   - ボットに必要な権限があるか確認
   - コマンドの形式が正しいか確認