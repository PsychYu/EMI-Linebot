import logging
import os
import sys

import MySQLdb
from DBUtils.PooledDB import PooledDB
from dotenv import load_dotenv

from constants import (DB_CONNECTION_TIMEOUT, DB_MAX_CONNECTIONS,
                       DB_MAX_SHARED, DB_MIN_CONNECTIONS, ENCODING,
                       ENV_PRODUCTION_FLAG)

# ローカル環境の場合のみ.envを読み込む
if not os.environ.get(ENV_PRODUCTION_FLAG):
    load_dotenv()

# 環境変数の取得
try:
    REMOTE_HOST = os.environ['DB_HOST']
    REMOTE_DB_NAME = os.environ['DB_DATABASE']
    REMOTE_DB_USER = os.environ['DB_USERNAME']
    REMOTE_DB_PASS = os.environ['DB_PASSWORD']
except KeyError as e:
    logging.error(f"必要なDB環境変数が設定されていません: {e}")
    sys.exit(1)

# コネクションプールの作成
connection_pool = PooledDB(
    creator=MySQLdb,
    mincached=DB_MIN_CONNECTIONS,
    maxcached=DB_MAX_CONNECTIONS,
    maxshared=DB_MAX_SHARED,
    host=REMOTE_HOST,
    db=REMOTE_DB_NAME,
    user=REMOTE_DB_USER,
    passwd=REMOTE_DB_PASS,
    charset=ENCODING,
    connect_timeout=DB_CONNECTION_TIMEOUT
)

def get_connection():
    """コネクションプールから接続を取得する"""
    conn = connection_pool.connection()
    cursor = conn.cursor()
    
    try:
        # データベースの文字コードをUTF-8に設定
        cursor.execute(f"SET NAMES {ENCODING};")
        cursor.execute(f"SET character_set_connection = {ENCODING};")
        cursor.execute(f"SET character_set_results = {ENCODING};")
        cursor.execute(f"SET character_set_client = {ENCODING};")
        cursor.execute(f"SET character_set_database = {ENCODING};")
        cursor.execute(f"SET character_set_server = {ENCODING};")
    except Exception as e:
        logging.error(f"データベースの文字コード設定エラー: {e}")
        cursor.close()
        conn.close()
        raise
    
    return conn