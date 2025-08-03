DROP TABLE IF EXISTS monitor_details CASCADE; 

DROP TABLE IF EXISTS monitors CASCADE; 

-- * BackupToTempTable
DROP TABLE IF EXISTS users CASCADE; 

DROP TABLE IF EXISTS notification_plans CASCADE; 

DROP TABLE IF EXISTS moods CASCADE; 

DROP TABLE IF EXISTS scale_ranges CASCADE; 

DROP TABLE IF EXISTS message_templates CASCADE; 

DROP VIEW IF EXISTS monitor_view CASCADE; 

-- 基本テーブル（外部キー参照されるテーブル）を先に作成
-- ユーザーテーブル
-- * RestoreFromTempTable
CREATE TABLE users( 
    line_user_id VARCHAR (33) PRIMARY KEY COMMENT 'ユーザー識別子:LINEから発行されるユーザー識別子'
    , participant_id CHAR (4) DEFAULT 'FILL' COMMENT '参加者ID:質問紙との照合に使用する、実験用の参加者ID; LINE登録後に参加者がLINEから登録更新'
    , input_mode TINYINT(1) DEFAULT 0 COMMENT '入力モード:0=ニュートラル、1=参加者ID入力開始モード、2=参加者ID入力待機モード、3=状況入力モード、4=反応入力モード'
    , group_id TINYINT(1) DEFAULT 9 COMMENT '群:0=統制群、1=実験群; 初期値9で、LINE登録後に実験者が0か1に手動変更'
    , is_temporary_send TINYINT(1) DEFAULT 0 COMMENT '臨時送信:0=FALSE、1=TRUE; モニタリング以外のメッセージ送信用'
    , is_participant_id_locked TINYINT(1) DEFAULT 0 COMMENT '参加者IDロック:0=FALSE、1=TRUE; TRUEの場合、参加者IDの変更を禁止'
); 

-- 気分テーブル
CREATE TABLE moods( 
    mood_id TINYINT(2) PRIMARY KEY COMMENT '気分ID'
    , mood_name VARCHAR (20) NOT NULL COMMENT '気分の名前'
    , valence TINYINT(2) NOT NULL COMMENT '感情価:1=Positive, 2=Negative, 3=Neutral, 99=None'
    , sort_order TINYINT(2) NOT NULL DEFAULT 99 COMMENT 'ソート順:表示順序を制御する数値'
); 

CREATE TABLE scale_ranges( 
    min_value TINYINT NOT NULL COMMENT '最小値'
    , max_value TINYINT NOT NULL COMMENT '最大値'
    , PRIMARY KEY (min_value, max_value)
); 

-- 通知計画テーブル
CREATE TABLE notification_plans( 
    sending_date DATE NOT NULL COMMENT '送信日:毎日0時に新規日付をINSERT'
    , sending_number TINYINT NOT NULL COMMENT '送信回:1=1回目、2=2回目、3=3回目'
    , sending_time TIME NOT NULL COMMENT '送信予定時刻:送信予定時刻'
    , sent_time DATETIME COMMENT '送信完了時刻:参加者全員の送信が完了した時刻'
    , PRIMARY KEY (sending_date, sending_number)
); 

-- メッセージテンプレートテーブル
CREATE TABLE message_templates( 
    message_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'メッセージID:一意のメッセージ識別子'
    , target_group TINYINT(2) NOT NULL COMMENT '送信対象:0=統制群、1=実験群'
    , message_content TEXT NOT NULL COMMENT 'メッセージ内容:送信するメッセージの本文'
    , is_disabled TINYINT(1) DEFAULT 0 COMMENT '無効フラグ:0=有効、1=無効'
    , created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時'
    , updated_at DATETIME DEFAULT CURRENT_TIMESTAMP 
        ON UPDATE CURRENT_TIMESTAMP COMMENT '更新日時'
); 

-- 外部キーを持つテーブルを後に作成
-- モニタリングテーブル
CREATE TABLE monitors( 
    monitor_id INT AUTO_INCREMENT COMMENT 'モニタリングID:モニタリング開始ごとに自動採番'
    , line_user_id VARCHAR (33) NOT NULL COMMENT 'ユーザー識別子'
    , sending_datetime DATETIME NOT NULL COMMENT '送信日時:メッセージ送信日時'
    , responding_datetime DATETIME COMMENT '反応開始日時:ユーザーがメッセージに反応開始した日時'
    , finished_datetime DATETIME COMMENT '完了日時:ユーザーがモニタリングを完了した日時'
    , PRIMARY KEY (monitor_id, line_user_id)
    , FOREIGN KEY (line_user_id) REFERENCES users(line_user_id)
); 

-- モニタリング詳細テーブル
CREATE TABLE monitor_details( 
    monitor_id INT NOT NULL COMMENT 'モニタリングID'
    , line_user_id VARCHAR (33) NOT NULL COMMENT 'ユーザー識別子'
    , mood_number INT NOT NULL COMMENT '気分No.:評定毎にインクリメント'
    , mood_id TINYINT(2) NOT NULL COMMENT '気分ID'
    , intensity TINYINT(1) DEFAULT 0 COMMENT '強度:1~6'
    , PRIMARY KEY (monitor_id, mood_number, line_user_id)
    , FOREIGN KEY (monitor_id, line_user_id) REFERENCES monitors(monitor_id, line_user_id)
    , FOREIGN KEY (line_user_id) REFERENCES users(line_user_id)
    , FOREIGN KEY (mood_id) REFERENCES moods(mood_id)
); 

-- 初期データの挿入
-- 気分データ
INSERT 
INTO moods(mood_id, mood_name, valence, sort_order) 
VALUES (1, '落ち込む', 2, 1)
, (2, '不安だ', 2, 2)
, (3, '孤独感がある', 2, 3)
, (4, 'おびえている', 2, 4)
, (5, '怪しんでいる', 2, 5)
, (6, 'うしろめたい', 2, 6)
, (7, 'いらいらする', 2, 7)
, (8, 'なし', 99, 8)
, (9, '---', 88, 9)  -- セパレータ
, (10, 'リラックス', 1, 10)
, (11, '満足している', 1, 11)
, (12, '熱意がある', 1, 12)
, (13, '楽しい', 1, 13); 

-- スケール範囲
INSERT 
INTO scale_ranges(min_value, max_value) 
VALUES (1, 6); 

-- メッセージテンプレート
INSERT 
INTO message_templates(target_group, message_content, is_disabled) 
VALUES ( 
    0
    , 'この度は、実験にご参加いただき、ありがとうございます！\nあなたは、Bグループ（LINEから通知が送信されないグループ）に割り当てられました。\n\n次回、3週間後にアンケートにご協力いただければ幸いです。\n回答者様の中から、抽選で若干名に、QUOカード1000円分を進呈させていただきます。\n\nなお、3週間後のアンケート時にご希望の方には、Aグループ（1日約3回の通知に、3週間回答するグループ）を体験して頂くこともできます。\nでは、引き続きどうぞよろしくお願いいたします。'
    , 0
) 
, ( 
    1
    , 'この度は、「気分モニタリング」アカウントにご登録いただき、ありがとうございます！\nあなたは、Aグループ（1日約3回の通知に回答するグループ）に割り当てられました。\n\n当アカウントでは、10:00~22:00のランダムな時間に、1日約3回通知を発信します。\n通知では、①現在の気分・感情やその強さ ②現在の気分・感情に影響した状況（例：先生に怒られた、発表の準備がなかなか終わらない、温かい布団に包まれている、など）③現在の気分・感情にともなう、からだの反応や行動（例：お腹が痛くなる、胸がドキドキする、ため息を吐く、うろうろ動き回る、げらげら笑っている、など）をお尋ねします（②と③はいずれかひとつをお尋ねします）。\n①では、どの気分にも当てはまらないときでも、最も近い気分を最低ひとつお選びください。\n\nまた、①で選ばれた選択肢のデータは匿名で収集させていただきますが、②と③で入力頂いたテキストデータは、こちらから収集することはありません。どうぞ安心してご自由にお書きください。\nアカウントを一定以上ご利用頂いた方で、ご希望の方には、研究終了後に、謝礼に加えて個人の振り返り結果をフィードバックさせていただきます。\nご利用頻度が高ければ高いほど、正確なフィードバックを提供できます。\n自己理解や自己分析、就職活動等にどうぞご活用ください。\nなお、フィードバックのご希望は、3週間後のアンケート時にお尋ねします。\n\nでは3週間、引き続きどうぞよろしくお願い致します。'
    , 0
) 
, ( 
    1
    , '【リマインド】\nいつもご協力いただき、本当にありがとうございます。\n恐れ入りますが、最近のご利用が減っているようです。\nもし仮に1日2回以上ご利用頂いていない日が一定日数連続した場合、通知の配信は停止され、参加登録も解除されます。\nその場合、データが使用できなくなり、謝礼やフィードバックもご提供できなくなってしまいます。\nお忙しいところ大変申し訳ありません。\nなお、「以上で完了です！」というメッセージが表示されて、1回ご利用とカウントされます。\nもし、使用に関するお問い合わせ等ございましたら、以下のアドレスまでお送りください。\nxxxxx@gmail.com\nどうぞよろしくお願いいたします。'
    , 1
); 

-- モニタリングビュー
CREATE VIEW monitor_view AS 
SELECT
    md.monitor_id -- モニタリングID
    , u.participant_id -- 参加者ID
    , md.mood_number -- 気分No.
    , m.mood_name -- 気分名
    , md.intensity -- 強度
    , mo.sending_datetime -- 送信日時
    , mo.responding_datetime -- 反応開始日時
    , mo.finished_datetime -- 完了日時
FROM
    monitor_details md 
    INNER JOIN monitors mo 
        ON md.monitor_id = mo.monitor_id 
        AND md.line_user_id = mo.line_user_id 
    INNER JOIN moods m 
        ON md.mood_id = m.mood_id 
    INNER JOIN users u 
        ON md.line_user_id = u.line_user_id;
