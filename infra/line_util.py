import logging
import os
import sys

from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler

from constants import ENV_PRODUCTION_FLAG

# ローカル環境の場合のみ.envを読み込む
if not os.environ.get(ENV_PRODUCTION_FLAG):
    load_dotenv()

def get_line_credentials():
    """LINE APIの認証情報を取得する

    Returns:
        tuple: (アクセストークン, チャンネルシークレット)
    """
    try:
        access_token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        channel_secret = os.environ["LINE_CHANNEL_SECRET"]
        return access_token, channel_secret
    except KeyError as e:
        logging.error(f"必要なLINE環境変数が設定されていません: {e}")
        sys.exit(1)

def initialize_line_api():
    """LINE APIクライアントとWebhookHandlerを初期化する

    Returns:
        tuple: (LineBotApi, WebhookHandler)
    """
    access_token, channel_secret = get_line_credentials()
    return LineBotApi(access_token), WebhookHandler(channel_secret)

# シングルトンパターンでLINE APIクライアントとWebhookHandlerを初期化
line_bot_api, webhook_handler = initialize_line_api() 