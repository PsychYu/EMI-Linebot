import logging
import os
import sys

from flask import Flask, abort, request
from linebot.exceptions import InvalidSignatureError
from linebot.models import (FollowEvent, MessageEvent, PostbackEvent,
                            TextMessage)

# 各ハンドラのインポート（友達登録、メッセージ、ボタンイベントの処理）
from handlers.follow_event_handler import handle_follow_event
from handlers.message_event_handler import handle_message_event
from handlers.postback_event_handler import handle_postback_event
from infra.line_util import webhook_handler

app = Flask(__name__)

# ロガー設定（INFOレベルのログ出力）
logging.basicConfig(level=logging.INFO)
handler_logger = logging.StreamHandler()
handler_logger.setLevel(logging.INFO)
app.logger.addHandler(handler_logger)

# =====================================================================
# LINE BOT からのWebhookリクエストエンドポイントを定義
# ユーザーからのイベントを受信し、各ハンドラに振り分ける
# =====================================================================
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名情報を取得
    try:
        signature = request.headers.get('X-Line-Signature')
        if signature is None:
            logging.error("署名情報が見つかりません")
            abort(400)
            
        # リクエストボディをテキストとして取得
        body = request.get_data(as_text=True)
        
        # 受信したイベントを各ハンドラに振り分ける
        webhook_handler.handle(body, signature)
    except InvalidSignatureError:
        logging.error("不正な署名です")
        abort(400)
    except Exception as e:
        logging.error(f"Webhookハンドリングエラー: {e}")
        abort(500)
    
    return 'OK'

# =====================================================================
# 各イベントハンドラの登録
# ・FollowEvent: 友だち登録時の処理
# ・MessageEvent: ユーザーからのメッセージ入力時の処理
# ・PostbackEvent: ボタン押下時の処理
# =====================================================================
webhook_handler.add(FollowEvent)(handle_follow_event)
webhook_handler.add(MessageEvent, message=TextMessage)(handle_message_event)
webhook_handler.add(PostbackEvent)(handle_postback_event)

# =====================================================================
# アプリケーションの起動設定
# =====================================================================
if __name__ == "__main__":
    try:
        port = int(os.getenv("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    except ValueError as e:
        logging.error(f"ポート番号の変換エラー: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"アプリケーション起動エラー: {e}")
        sys.exit(1)
