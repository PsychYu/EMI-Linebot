"""
定数の定義
"""

# 環境判定用の定数
ENV_PRODUCTION_FLAG = 'DYNO'  # 本番環境判定用の環境変数名（Herokuの場合はDYNO）

# スケジューラー関連の定数
SCHEDULER_MIN_HOUR = 10
SCHEDULER_MAX_HOUR = 15
SCHEDULER_BATCH_MINUTES = 10
SCHEDULER_MIN_INTERVAL_HOURS = 3
SCHEDULER_MIN_MINUTES = 0
SCHEDULER_MAX_MINUTES = 59
BUTTON_EXPIRY_MINUTES = 90  # ボタンの有効期限（分）

# 実験群設定
CONTROL_GROUP = 0  # 統制群
EXPERIMENTAL_GROUP = 1  # 実験群

# 入力モード
INPUT_MODE_NEUTRAL = 0
INPUT_MODE_ID_REGISTRATION = 1
INPUT_MODE_CONFIRMATION = 2
INPUT_MODE_SITUATION = 3
INPUT_MODE_REACTION = 4

# 強度レベルの閾値
INTENSITY_LOW = 2
INTENSITY_MEDIUM = 4
INTENSITY_HIGH = 5

# 感情価（Valence）
VALENCE_NONE = 99  # 「なし」ボタンの感情価
VALENCE_SEPARATOR = 88  # セパレータの感情価

# ボタンテキスト
BUTTON_TEXT_START = "開始する"
BUTTON_TEXT_CANCEL = "やめる"
BUTTON_TEXT_NONE = "なし"

# ボタンタイプ
BUTTON_TYPE_INITIAL_MOOD = "initial_mood_button"
BUTTON_TYPE_ADDITIONAL_MOOD = "additional_mood_button"
BUTTON_TYPE_SCALE = "scale_button" 

# ID登録関連
ID_REGISTRATION_ACCEPT = "1"
ID_REGISTRATION_REJECT = "0"
ID_REGISTRATION_PATTERNS = ["ID登録", "id登録", "Id登録"]
ID_LOCKED = 1    # 参加者IDロック有効
ID_UNLOCKED = 0  # 参加者IDロック無効

# データベース関連
# 参加者数や運用想定に応じて、接続数を調整する
ENCODING = 'utf8mb4'  # データベースのエンコーディング
DB_MIN_CONNECTIONS = 1  # プール開始時の最小接続数
DB_MAX_CONNECTIONS = 5  # プール内の最大接続数
DB_MAX_SHARED = 1  # コネクションを共有できるスレッド数
DB_CONNECTION_TIMEOUT = 30  # 接続タイムアウト（秒）