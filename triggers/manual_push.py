import argparse
import logging
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

from constants import CONTROL_GROUP, EXPERIMENTAL_GROUP
from infra.db_util import get_connection
from infra.line_util import line_bot_api
from infra.query import get_active_message_templates, get_users_for_message


def send_messages_to_group(c, conn, templates_dict, group_id=None):
    """指定された群にメッセージを送信する処理
    
    Args:
        templates_dict: 群ごとのメッセージテンプレート
        group_id: 送信対象の群ID（Noneの場合は全ての群）
    
    Returns:
        bool: 処理が成功したかどうか
    """
    # 送信対象の群を決定
    if group_id is not None:
        target_groups = [group_id]
    else:
        # group_idが指定されていない場合は、有効なテンプレートがある全ての群を対象とする
        target_groups = list(templates_dict.keys())
    
    success = True
    
    # 各対象群に対してメッセージを送信
    for gid in target_groups:
        group_name = "統制群" if gid == 0 else "実験群"
        
        # ユーザー情報の取得
        try:
            users = get_users_for_message(c, gid)
        except Exception as e:
            logging.error(f"ユーザー情報の取得エラー: {e}")
            success = False
            continue
        
        if not users:
            logging.info("送信対象の" + f"{group_name}のユーザーが見つかりませんでした。")
            continue
        
        # 該当する群のメッセージテンプレートを取得
        if gid not in templates_dict:
            logging.error(f"{group_name}向けの有効なメッセージテンプレートが見つかりませんでした。")
            success = False
            continue
        
        message_content = templates_dict[gid]
        
        # 各ユーザーに対してメッセージを送信
        for user in users:
            user_id = user[0]  # line_user_id
            participant_id = user[1]  # participant_id
            try:
                line_bot_api.push_message(user_id, TextSendMessage(text=message_content))
                logging.info(f"{group_name}参加者ID: {participant_id}にメッセージを送信しました。")
                conn.commit()
            except LineBotApiError as e:
                logging.error(f"送信エラー（参加者ID: {participant_id}）: {str(e)}")
                success = False
    
    return success

if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='LINEメッセージ送信スクリプト')
    group_arg = parser.add_mutually_exclusive_group(required=True)
    group_arg.add_argument('--control', action='store_true', help='統制群(0)にメッセージを送信')
    group_arg.add_argument('--experimental', action='store_true', help='実験群(1)にメッセージを送信')
    group_arg.add_argument('--both', action='store_true', help='両方の群にメッセージを送信')
    args = parser.parse_args()

    # --------------------------------------------------------------------------
    # DB接続処理
    # --------------------------------------------------------------------------
    conn = None
    c = None
    try:
        conn = get_connection()
        c = conn.cursor()
    except Exception as e:
        logging.error(f"DB接続エラー: {e}")
        sys.exit(1)
    
    success = True

    try:
        # --------------------------------------------------------------------------
        # メッセージテンプレート取得処理
        # --------------------------------------------------------------------------
        templates = get_active_message_templates(c)
        
        # 群ごとのメッセージテンプレートを辞書に整理
        templates_dict = {}
        for target_group, message_content in templates:
            if target_group in templates_dict:
                logging.error(f"エラー: 群{target_group}に対して有効なメッセージテンプレートが複数存在します。")
                success = False
                break
            templates_dict[target_group] = message_content
        
        if not success:
            raise ValueError("メッセージテンプレートの重複エラー")
        
        # --------------------------------------------------------------------------
        # メッセージ送信処理
        # --------------------------------------------------------------------------
        # 指定された引数に基づいて処理を実行
        if args.control:
            logging.info("統制群へのメッセージ送信を開始します...")
            if not send_messages_to_group(c, conn, templates_dict, CONTROL_GROUP):
                success = False
        
        elif args.experimental:
            logging.info("実験群へのメッセージ送信を開始します...")
            if not send_messages_to_group(c, conn, templates_dict, EXPERIMENTAL_GROUP):
                success = False
        
        elif args.both:
            logging.info("両群へのメッセージ送信を開始します...")
            if not send_messages_to_group(c, conn, templates_dict):
                success = False
    
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")
        success = False
    
    finally:
        # --------------------------------------------------------------------------
        # DB接続クローズ処理
        # --------------------------------------------------------------------------
        try:
            if c:
                c.close()
            if conn:
                conn.close()
        except Exception as e:
            logging.error("接続を閉じる際にエラーが発生しました: %s", e)
    
    if not success:
        logging.error("処理が失敗しました。")
        sys.exit(1)
    
    logging.info("メッセージ送信処理が完了しました。")

else:
    logging.warning("このファイルは直接実行する必要があります。")