import datetime
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random

from flask import abort
from linebot.models import PostbackEvent, TextSendMessage

from constants import (BUTTON_EXPIRY_MINUTES, BUTTON_TYPE_ADDITIONAL_MOOD,
                       BUTTON_TYPE_INITIAL_MOOD, BUTTON_TYPE_SCALE,
                       ID_REGISTRATION_ACCEPT, ID_REGISTRATION_REJECT,
                       INPUT_MODE_CONFIRMATION, INPUT_MODE_ID_REGISTRATION,
                       INPUT_MODE_NEUTRAL, INPUT_MODE_REACTION,
                       INPUT_MODE_SITUATION, VALENCE_NONE)
from infra.db_util import get_connection
from infra.line_util import line_bot_api
from infra.query import (get_all_mood_names, get_latest_monitor,
                         get_max_mood_number, get_mood_name,
                         get_scale_range_values, get_sending_datetime,
                         get_user_input_mode, get_valence)
from infra.service import (insert_monitor_detail,
                           update_monitor_detail_intensity,
                           update_monitor_finished_datetime,
                           update_monitor_responding_datetime,
                           update_user_input_mode)
from modules.mood_buttons import MoodButtons
from modules.mood_summarizer import MoodSummarizer
from modules.scale_buttons import ScaleButtons


def handle_postback_event(event: PostbackEvent):
    """ボタン押下（Postback）イベントの処理"""
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
    
    logging.info("ボタンイベント")
    # --------------------------------------------------------------------------
    # LINEユーザーIDおよびPOSTBACKデータの取得
    # --------------------------------------------------------------------------
    line_user_id = event.source.user_id
    postback_data = event.postback.data

    # POSTBACKデータが「ボタンタイプ」と「ユーザー応答」に分割されている場合、それぞれを取得
    splits = postback_data.split()
    button_type = None
    user_response = None
    if len(splits) == 2:
        button_type = splits[0]
        user_response = splits[1]
    
    valence = None
    # ボタンタイプがadditional_mood_buttonの場合は、valenceを取得
    if button_type == BUTTON_TYPE_ADDITIONAL_MOOD:
        valence = get_valence(c, int(user_response))

    # --------------------------------------------------------------------------
    # 現在のユーザー入力モードと気分変換器の取得
    # --------------------------------------------------------------------------
    try:
        input_mode = get_user_input_mode(c, line_user_id)
        mood_summarizer = MoodSummarizer(c, line_user_id)
    except Exception as e:
        logging.error(f"ユーザー入力モード取得エラー: {e}")
        return

    # --------------------------------------------------------------------------
    # 参加者ID登録モード（step2）の場合の処理
    # --------------------------------------------------------------------------
    if postback_data == ID_REGISTRATION_ACCEPT and input_mode == INPUT_MODE_ID_REGISTRATION:
        try:
            # 「開始する」ボタンが押された場合：ID入力を促すメッセージ送信
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="IDを入力してください。")
            )
        except Exception as e:
            logging.error(f"ID入力促進メッセージ送信エラー: {e}")
        try:
            update_user_input_mode(c, line_user_id, INPUT_MODE_CONFIRMATION)
            conn.commit()
        except Exception as e:
            logging.error("ユーザー入力モード更新時エラー: %s", e)
            conn.rollback()
    elif postback_data == ID_REGISTRATION_REJECT and input_mode == INPUT_MODE_ID_REGISTRATION:
        try:
            # 「やめる」ボタンが押された場合：ID登録中断の旨を通知
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ID登録を中断しました。")
            )
        except Exception as e:
            logging.error(f"ID登録中断メッセージ送信エラー: {e}")
        try:
            update_user_input_mode(c, line_user_id, INPUT_MODE_NEUTRAL)
            conn.commit()
        except Exception as e:
            logging.error("ユーザー入力モード更新時エラー: %s", e)
            conn.rollback()

    # --------------------------------------------------------------------------
    # 最新のモニタリング状態を取得
    # --------------------------------------------------------------------------
    if input_mode == INPUT_MODE_NEUTRAL:
        try:
            latest_monitor = get_latest_monitor(c, line_user_id)
            if latest_monitor is None:
                logging.error("モニタリングデータが見つかりません")
                conn.close()
                c.close()
                return
            
            monitor_id = latest_monitor[0] # モニタリングID
            finished_datetime = latest_monitor[1] # モニタリング完了日時
            is_monitor_finished = (finished_datetime is not None) # モニタリングが完了しているかどうか
            sending_datetime = get_sending_datetime(c, monitor_id) # モニタリング送信日時
        except Exception as e:
            logging.error(f"モニタリング状態取得エラー: {e}")
            return

    # --------------------------------------------------------------------------
    # 90分経過している場合、ボタンの有効期限切れを通知
    # --------------------------------------------------------------------------
    if input_mode == INPUT_MODE_NEUTRAL and sending_datetime + datetime.timedelta(minutes=BUTTON_EXPIRY_MINUTES) < datetime.datetime.now():
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"{BUTTON_EXPIRY_MINUTES}分経過したためボタンが無効になりました。次回の通知をお待ちください。")
            )
        except Exception as e:
            logging.error(f"有効期限切れメッセージ送信エラー: {e}")

    # --------------------------------------------------------------------------
    # 既にモニタリングが完了している場合の処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_NEUTRAL and is_monitor_finished and button_type in [BUTTON_TYPE_INITIAL_MOOD, BUTTON_TYPE_ADDITIONAL_MOOD, BUTTON_TYPE_SCALE]:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="すでにモニタリングは完了済みのようです。次回の通知をお待ちください。")
            )
        except Exception as e:
            logging.error(f"モニタリング完了済みメッセージ送信エラー: {e}")

    # --------------------------------------------------------------------------
    # 通知反応（気分押下）後の返答と保存処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_NEUTRAL and not is_monitor_finished and button_type in [BUTTON_TYPE_INITIAL_MOOD, BUTTON_TYPE_ADDITIONAL_MOOD] and valence != VALENCE_NONE:
        try:
            # 気分マスタから気分名を取得
            mood_name = get_mood_name(c, user_response)
            # スケール範囲を取得
            scale_values = get_scale_range_values(c)
            min_scale = int(scale_values[0])
            max_scale = int(scale_values[-1])
            # スケールボタンを生成
            scale_buttons = ScaleButtons.get_scale_buttons(min_scale, max_scale)
            
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    [TextSendMessage(text=f"「{mood_name}」という気分をどの程度感じていますか？"),
                     scale_buttons]
                )
            except Exception as e:
                logging.error(f"気分強度質問メッセージ送信エラー: {e}")

            try:
                user_response_encoded = user_response.encode('utf-8')
                # monitor_detailに挿入するモニタリング番号を作成
                max_mood_number = get_max_mood_number(c, monitor_id)
                mood_number = 1 if max_mood_number is None else max_mood_number + 1
                # monitor_detailに押下された気分を挿入し、応答日時の更新
                insert_monitor_detail(c, monitor_id, line_user_id, mood_number, user_response_encoded)
                update_monitor_responding_datetime(c, datetime.datetime.now(), monitor_id)
                conn.commit()
            except Exception as e:
                logging.error("データベース更新エラー: %s", e)
                conn.rollback()
        except Exception as e:
            logging.error(f"気分処理エラー: {e}")

    # --------------------------------------------------------------------------
    # Likert スケール（気分の強度選択）押下時の処理
    # --------------------------------------------------------------------------
    elif input_mode == INPUT_MODE_NEUTRAL and not is_monitor_finished and button_type == BUTTON_TYPE_SCALE:
        try:
            # 有効なスケール値を取得
            scale_values = get_scale_range_values(c)
            if user_response not in scale_values:
                logging.error(f"無効なスケール値が選択されました: {user_response}")
                return

            try:
                update_monitor_detail_intensity(c, user_response, monitor_id)
                mood_list = get_all_mood_names(c)
                conn.commit()
            except Exception as e:
                logging.error("データベース更新エラー: %s", e)
                conn.rollback()
                return

            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    [TextSendMessage(text=mood_summarizer.get_summarized_moods()[-1]+"と感じるんですね。"),
                     TextSendMessage(text="他に感じた気分や感情はありますか？"),
                     MoodButtons.get_additional_message(c, mood_list)]
                )
            except Exception as e:
                logging.error(f"追加気分質問メッセージ送信エラー: {e}")
        except Exception as e:
            logging.error(f"Likertスケール処理エラー: {e}")

    # --------------------------------------------------------------------------
    # 気分「なし」押下後の分岐処理
    # --------------------------------------------------------------------------
    elif valence == VALENCE_NONE and button_type == BUTTON_TYPE_ADDITIONAL_MOOD:
        try:
            # 乱数による分岐（終了=0、状況入力=2、反応入力=3）
            random_choice = random.choice([INPUT_MODE_NEUTRAL, INPUT_MODE_SITUATION, INPUT_MODE_REACTION])
            moods = ""
            if random_choice == INPUT_MODE_NEUTRAL:
                try:
                    # 終了処理：気分が1つだけ選択された場合
                    if len(mood_summarizer.get_summarized_moods()) == 1:
                        try:
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=mood_summarizer.get_summarized_moods()[0]+"というほかは当てはまらなかったんですね。\n以上で完了です！")
                            )
                        except Exception as e:
                            logging.error(f"終了メッセージ送信エラー: {e}")
                        update_monitor_finished_datetime(c, datetime.datetime.now(), line_user_id)
                        conn.commit()
                    # 終了処理：気分が複数選択された場合
                    else:
                        # 変換済み気分を「、」で繋げて表示する
                        moods = "、".join(mood_summarizer.get_summarized_moods())
                        try:
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=moods+"という感じがするんですね。\n以上で完了です！")
                            )
                        except Exception as e:
                            logging.error(f"終了メッセージ送信エラー: {e}")
                        update_monitor_finished_datetime(c, datetime.datetime.now(), line_user_id)
                        conn.commit()
                except Exception as e:
                    logging.error(f"モニタリング終了処理エラー: {e}")

            elif random_choice == INPUT_MODE_SITUATION:
                try:
                    # 状況入力モード開始：気分に影響した状況の入力を促す
                    # サマリー済み気分を「、」で繋げて表示する
                    update_user_input_mode(c, line_user_id, INPUT_MODE_SITUATION) # 状況入力モードに変更
                    conn.commit()  # データベースの変更をコミット
                    moods = "、".join(mood_summarizer.get_summarized_moods()) # 例："少し「落ち込む」、かなり「不安だ」"
                    try:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=moods+"という感じがするんですね。\nその気分に影響した状況をふりかえって、入力してみてください。分からなければ勘でもかまいません。")
                        )
                    except Exception as e:
                        logging.error(f"状況入力促進メッセージ送信エラー: {e}")
                except Exception as e:
                    logging.error(f"状況入力モード開始エラー: {e}")

            elif random_choice == INPUT_MODE_REACTION:
                try:
                    # 反応入力モード開始：気分にともなう反応の入力を促す
                    # サマリー済み気分を「、」で繋げて表示する
                    update_user_input_mode(c, line_user_id, INPUT_MODE_REACTION) # 反応入力モードに変更
                    conn.commit()  # データベースの変更をコミット
                    moods = "、".join(mood_summarizer.get_summarized_moods()) # 例："少し「落ち込む」、かなり「不安だ」"
                    try:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=moods+"という感じがするんですね。\nその気分にともなって生じた、からだの反応や行動をふりかえって、入力してみてください。分からなければ勘でもかまいません。")
                        )
                    except Exception as e:
                        logging.error(f"反応入力促進メッセージ送信エラー: {e}")
                except Exception as e:
                    logging.error(f"反応入力モード開始エラー: {e}")
        except Exception as e:
            logging.error(f"気分「なし」押下後の分岐処理エラー: {e}")
            
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
