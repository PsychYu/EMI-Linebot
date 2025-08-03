import datetime
import logging
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import abort
from linebot.models import MessageEvent, TextSendMessage

from constants import (BUTTON_TEXT_CANCEL, BUTTON_TEXT_NONE, BUTTON_TEXT_START,
                       ID_LOCKED, ID_REGISTRATION_PATTERNS,
                       INPUT_MODE_CONFIRMATION, INPUT_MODE_ID_REGISTRATION,
                       INPUT_MODE_NEUTRAL, INPUT_MODE_REACTION,
                       INPUT_MODE_SITUATION)
from infra.db_util import get_connection
from infra.line_util import line_bot_api
from infra.query import (get_all_mood_names, get_participant_id_lock_status,
                         get_scale_range_values, get_user_input_mode)
from infra.service import (update_monitor_finished_datetime,
                           update_user_input_mode, update_user_participant_id)
from modules.id_registration import IDRegistration
from modules.mood_summarizer import MoodSummarizer


def handle_message_event(event: MessageEvent):
    """文字入力イベントの処理"""
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
    
    # --------------------------------------------------------------------------
    # LINEユーザーIDおよび受信テキストの取得
    # --------------------------------------------------------------------------
    line_user_id = event.source.user_id
    text = event.message.text

    # --------------------------------------------------------------------------
    # ユーザー入力モードおよび気分変換器の取得
    # --------------------------------------------------------------------------
    try:
        input_mode = get_user_input_mode(c, line_user_id)
    except Exception as e:
        logging.error("ユーザー入力モード取得時エラー: %s", e)
        input_mode = INPUT_MODE_NEUTRAL

    mood_summarizer = MoodSummarizer(c, line_user_id)

    # --------------------------------------------------------------------------
    # ボタン押下で送信されるテキスト等を判定除外するためのフィルター
    # --------------------------------------------------------------------------
    try:
        mood_names = [mood[1] for mood in get_all_mood_names(c)]
        scale_values = get_scale_range_values(c)
        excluded_texts = set(mood_names + scale_values + [BUTTON_TEXT_START, BUTTON_TEXT_CANCEL])
        if input_mode in [INPUT_MODE_NEUTRAL, INPUT_MODE_ID_REGISTRATION, INPUT_MODE_CONFIRMATION] and text in excluded_texts:
            return
    except Exception as e:
        logging.error("ボタン押下で送信されるテキスト等を判定除外するためのフィルター時エラー: %s", e)

    logging.info("文字入力イベント")

    # --------------------------------------------------------------------------
    # 参加者ID登録（step1）の処理
    # --------------------------------------------------------------------------
    if text in ID_REGISTRATION_PATTERNS and input_mode == INPUT_MODE_NEUTRAL:
        try:
            is_locked = get_participant_id_lock_status(c, line_user_id)
        except Exception as e:
            logging.error(f"参加者ID情報取得エラー: {e}")
            abort(500)

        if is_locked == ID_LOCKED:
            # IDがロックされている場合、警告メッセージを送信
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="IDはすでに登録されています。")
                )
            except Exception as e:
                logging.error(f"メッセージ送信エラー: {e}")
        else:
            # ロックされていない場合、ID登録ボタンを送信し、入力モードを変更
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    IDRegistration.registration_message
                )
            except Exception as e:
                logging.error(f"ID登録ボタン送信エラー: {e}")
            try:
                update_user_input_mode(c, line_user_id, INPUT_MODE_ID_REGISTRATION)
                conn.commit()
            except Exception as e:
                logging.error("ユーザー入力モード更新時エラー: %s", e)
                conn.rollback()
        
        # ID登録ボタン押下後は、postback_event_handler.pyの参加者ID登録モード（step2）の場合の処理へ

    # --------------------------------------------------------------------------
    # 参加者ID登録（step3）の処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_CONFIRMATION:
        try:
            # ユーザーからの入力テキストを参加者IDとして登録
            update_user_participant_id(c, text, line_user_id)
            # 入力モードを解除
            update_user_input_mode(c, line_user_id, INPUT_MODE_NEUTRAL)
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="「"+text+"」がIDとして登録されました。")
                )
            except Exception as e:
                logging.error(f"ID登録完了メッセージ送信エラー: {e}")
            conn.commit()
        except Exception as e:
            logging.error("ID登録時エラー: %s", e)
            conn.rollback()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ID登録に失敗しました。研究者にお問い合わせください。")
            )

    # --------------------------------------------------------------------------
    # 状況入力モードの場合の処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_SITUATION and text != BUTTON_TEXT_NONE:
        try:
            moods = "、".join(mood_summarizer.get_summarized_moods()) # 例："少し「落ち込む」、かなり「不安だ」"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="「"+text+"」という状況があって、"+moods+"という気分になったんですね。\n以上で完了です！")
                )
            except Exception as e:
                logging.error(f"状況入力完了メッセージ送信エラー: {e}")
            try:
                update_monitor_finished_datetime(c, datetime.datetime.now(), line_user_id)
                update_user_input_mode(c, line_user_id, INPUT_MODE_NEUTRAL)
                conn.commit()
            except Exception as e:
                logging.error("モニタリング完了時エラー: %s", e)
                conn.rollback()
        except Exception as e:
            logging.error(f"気分サマリー取得エラー: {e}")

    # --------------------------------------------------------------------------
    # 反応入力モードの場合の処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_REACTION and text != BUTTON_TEXT_NONE:
        try:
            moods = "、".join(mood_summarizer.get_summarized_moods()) # 例："少し「落ち込む」、かなり「不安だ」"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="「"+text+"」という反応にともなって、"+moods+"という気分になったんですね。\n以上で完了です！")
                )
            except Exception as e:
                logging.error(f"反応入力完了メッセージ送信エラー: {e}")
            try:
                update_monitor_finished_datetime(c, datetime.datetime.now(), line_user_id)
                update_user_input_mode(c, line_user_id, INPUT_MODE_NEUTRAL)
                conn.commit()
            except Exception as e:
                logging.error("モニタリング完了時エラー: %s", e)
                conn.rollback()
        except Exception as e:
            logging.error(f"気分サマリー取得エラー: {e}")

    # --------------------------------------------------------------------------
    # その他（想定外）の入力の場合の処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_NEUTRAL:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="すみません。よくわかりませんでした…。")
            )
        except Exception as e:
            logging.error(f"不明テキストに対するメッセージ送信エラー: {e}")

    # --------------------------------------------------------------------------
    # DB接続のクローズ処理
    # --------------------------------------------------------------------------
    try:
        if c:
            c.close()
        if conn:
            conn.close()
    except Exception as e:
        logging.error("接続を閉じる際にエラーが発生しました: %s", e)
