import logging
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import abort
from linebot.models import FollowEvent, TextSendMessage

from infra.db_util import get_connection
from infra.line_util import line_bot_api
from infra.query import get_participant_id
from infra.service import insert_user


def handle_follow_event(event: FollowEvent):
    """友だち登録イベントの処理"""
    # --------------------------------------------------------------------------
    # DB接続処理
    # --------------------------------------------------------------------------
    conn = None
    c = None
    try:
        conn = get_connection()
        c = conn.cursor()
    except Exception as e:
        logging.error("DB接続エラー: %s", e)
        abort(500)
    
    logging.info("友達登録イベント")
    # --------------------------------------------------------------------------
    # LINEユーザーID取得
    # --------------------------------------------------------------------------
    line_user_id = event.source.user_id
    # --------------------------------------------------------------------------
    # ユーザーがDBに未登録の場合、新規登録処理を実行
    # --------------------------------------------------------------------------
    try:
        if not get_participant_id(c, line_user_id):
            insert_user(c, line_user_id)
        conn.commit()
        # --------------------------------------------------------------------------
        # ウェルカムメッセージの送信
        # --------------------------------------------------------------------------
        try:
            line_bot_api.reply_message(
                reply_token=event.reply_token,
                messages=TextSendMessage(text='登録ありがとうございます！')
            )
        except Exception as e:
            logging.error("ウェルカムメッセージ送信エラー: %s", e)
    except Exception as e:
        logging.error("ユーザー登録エラー: %s", e)
        conn.rollback()
        try:
            line_bot_api.reply_message(
                reply_token=event.reply_token,
                messages=TextSendMessage(text='友達登録時にエラーが発生しました。研究者にお問い合わせください。')
            )
        except Exception as e:
            logging.error("登録失敗メッセージ送信エラー: %s", e)
    finally:
        if c is not None:
            c.close()
        if conn is not None:
            conn.close()