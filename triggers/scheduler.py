import datetime
import logging
import os
import random
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import (SCHEDULER_BATCH_MINUTES, SCHEDULER_MAX_HOUR,
                       SCHEDULER_MAX_MINUTES, SCHEDULER_MIN_HOUR,
                       SCHEDULER_MIN_INTERVAL_HOURS, SCHEDULER_MIN_MINUTES)
from infra.db_util import get_connection
from infra.line_util import line_bot_api
from infra.query import (get_all_mood_names, get_experiment_group_users,
                         get_latest_notification_plan,
                         get_notification_plans_for_today)
from infra.service import (insert_monitor, insert_notification_plans,
                           update_notification_plan_sent_time,
                           update_user_input_mode)
from modules.mood_buttons import MoodButtons

# ロガーの基本設定
logging.basicConfig(level=logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logging.getLogger().addHandler(handler)

datetime_now = datetime.datetime.now()

# heroku scheduler等のタスクスケジューラーで10分毎にバッチ実行する前提
if __name__ == "__main__":
    logging.info("スケジューラー実行")
    conn = None
    c = None
    try:
        conn = get_connection()
        c = conn.cursor()
    except Exception as e:
        logging.error("DB接続エラー:", e)
        sys.exit(1)

    # =====================================================================
    # 日付変更時に送信予定を作成する
    # =====================================================================

    # 送信日と送信完了時間が最新のレコードを送信予定から取得
    try:
        latest_notification_plan = get_latest_notification_plan(c)
    except Exception as e:
        logging.error("送信予定取得エラー:", e)
    
    if latest_notification_plan is None:
        # レコードが存在しない場合、前日の日付を設定
        last_sent_date = datetime_now.date() - datetime.timedelta(days=1)
    else:
        # 最終送信完了日
        last_sent_date = latest_notification_plan[0]

    # 日付が変わった時点（最終送信完了日が現在よりも古くなった時点）で、新規ランダム時間リストを生成
    if last_sent_date < datetime_now.date():
        # ランダム時間生成のために、SCHEDULER_MIN_HOUR~SCHEDULER_MAX_HOURのランダムな数値を3つ昇順に並べる
        rand_hour_list = sorted([
            random.randint(SCHEDULER_MIN_HOUR, SCHEDULER_MAX_HOUR),
            random.randint(SCHEDULER_MIN_HOUR, SCHEDULER_MAX_HOUR),
            random.randint(SCHEDULER_MIN_HOUR, SCHEDULER_MAX_HOUR)
        ])
        
        # 通知間にSCHEDULER_MIN_INTERVAL_HOURS(デフォルト3時間)以上の間隔を担保する
        # 1つ目の時間はSCHEDULER_MIN_HOUR(デフォルト10時)から~SCHEDULER_MAX_HOUR(デフォルト15時)のランダムな時間
        rand_hour_1 = rand_hour_list[0]
        # 2つ目の時間は1つ目の時間から最低SCHEDULER_MIN_INTERVAL_HOURS(デフォルト3時間)後(～18時)
        rand_hour_2 = rand_hour_list[1] + SCHEDULER_MIN_INTERVAL_HOURS
        # 3つ目の時間は2つ目の時間から最低SCHEDULER_MIN_INTERVAL_HOURS(デフォルト3時間)後(～21時)
        rand_hour_3 = rand_hour_list[2] + (SCHEDULER_MIN_INTERVAL_HOURS * 2)

        # 現在の年月日とランダムな分を上記の時間に付与してdatetimeを作成
        rand_datetime_1 = datetime.datetime(datetime_now.year, datetime_now.month, datetime_now.day, rand_hour_1, random.randint(SCHEDULER_MIN_MINUTES, SCHEDULER_MAX_MINUTES))
        rand_datetime_2 = datetime.datetime(datetime_now.year, datetime_now.month, datetime_now.day, rand_hour_2, random.randint(SCHEDULER_MIN_MINUTES, SCHEDULER_MAX_MINUTES))
        rand_datetime_3 = datetime.datetime(datetime_now.year, datetime_now.month, datetime_now.day, rand_hour_3, random.randint(SCHEDULER_MIN_MINUTES, SCHEDULER_MAX_MINUTES))

        # 生成したランダム時間3レコード分をDBに格納
        try:
            insert_notification_plans(c, datetime_now.date(), rand_datetime_1.time(), rand_datetime_2.time(), rand_datetime_3.time())
            conn.commit()
            logging.info("送信予定挿入完了")
        except Exception as e:
            logging.error("送信予定挿入時エラー:", e)
            conn.rollback()

    # =====================================================================
    # 送信予定時刻に送信を実行する
    # =====================================================================

    sending_number = None
    last_sent_time = None

    # 送信予定時間を取得
    try:
        notification_plans_for_today = get_notification_plans_for_today(c, datetime_now.date())
    except Exception as e:
        logging.error("送信予定取得エラー:", e)
    datetime_1 = datetime.datetime.strptime(f"{notification_plans_for_today[0][0]} {notification_plans_for_today[0][1]}", "%Y-%m-%d %H:%M:%S")
    datetime_2 = datetime.datetime.strptime(f"{notification_plans_for_today[1][0]} {notification_plans_for_today[1][1]}", "%Y-%m-%d %H:%M:%S")
    datetime_3 = datetime.datetime.strptime(f"{notification_plans_for_today[2][0]} {notification_plans_for_today[2][1]}", "%Y-%m-%d %H:%M:%S")

    # schedulerが10分毎のバッチ実行のため、空振りを防ぐためにそれぞれの予定時刻の前後10分を送信可能範囲とする
    batch_minutes = datetime.timedelta(minutes=SCHEDULER_BATCH_MINUTES)
    if (((datetime_1 - batch_minutes) <= datetime_now <= (datetime_1 + batch_minutes))):
        sending_number = 1 # 1回目の送信
        last_sent_time = notification_plans_for_today[0][2] # 1回目の送信完了時刻
    elif (((datetime_2 - batch_minutes) <= datetime_now <= (datetime_2 + batch_minutes))):
        sending_number = 2 # 2回目の送信
        last_sent_time = notification_plans_for_today[1][2] # 2回目の送信完了時刻
    elif (((datetime_3 - batch_minutes) <= datetime_now <= (datetime_3 + batch_minutes))):
        sending_number = 3 # 3回目の送信
        last_sent_time = notification_plans_for_today[2][2] # 3回目の送信完了時刻

    if sending_number is not None:
        # 二重送信防止のため、送信完了していない場合のみを送信対象とする
        if last_sent_time is None:
            logging.info("送信判定")
            # 実験群のユーザのLINE識別子および参加者IDのリストを取得
            try:
                ids = get_experiment_group_users(c)
                line_user_ids = [item[0] for item in ids]
                participant_ids = [item[1] for item in ids]
            except Exception as e:
                logging.error("実験群ユーザ取得エラー:", e)

            # 感情語リストの取得
            try:
                mood_words = get_all_mood_names(c)
            except Exception as e:
                logging.error("感情語リスト取得エラー:", e)
            
            # ユーザごとにループでメッセージ送信
            for line_user_id, participant_id in zip(line_user_ids, participant_ids):
                try:
                    # プッシュメッセージ送信
                    if line_user_id is None:
                        is_send = False
                    else: 
                        line_bot_api.push_message(to=line_user_id, messages=MoodButtons.get_initial_message(c, mood_words))
                        is_send = True
                    # monitorsに送信時刻を保存
                    insert_monitor(c, line_user_id, datetime_now)
                    # 入力モードをニュートラルに戻す
                    update_user_input_mode(c, line_user_id, 0)
                    if is_send:
                        logging.info(participant_id + "：送信完了")
                    else:
                        logging.info("送信対象が存在しないため送信せず")
                    # 送信完了時刻を保存する
                    update_notification_plan_sent_time(c, datetime_now, datetime_now.date(), sending_number)
                    conn.commit()
                except Exception as e:
                    logging.error(f"ユーザー {line_user_id} へのメッセージ送信中にエラーが発生しました:", e)
                    conn.rollback()
        else:
            logging.info("二重送信防止のため終了")

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
else:
    logging.error("スケジューラー実行エラー")