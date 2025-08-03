def get_latest_notification_plan(c):
    c.execute("SELECT `sending_date` FROM `notification_plans` ORDER BY `sending_date` DESC LIMIT 1;")
    return c.fetchone()

def get_notification_plans_for_today(c, date):
    c.execute("SELECT `sending_date`, `sending_time`, `sent_time` FROM `notification_plans` WHERE `sending_date` = %s ORDER BY `sending_number`;", (date,))
    return c.fetchall()

def get_experiment_group_users(c):
    c.execute("SELECT `line_user_id`, `participant_id` FROM `users` WHERE `group_id` = 1;")
    return c.fetchall()

def get_user_input_mode(c, line_user_id):
    c.execute("SELECT `input_mode` FROM `users` WHERE `line_user_id` = %s;", (line_user_id,))
    result = c.fetchone()
    return result[0] if result else None

def get_participant_id(c, line_user_id):
    c.execute("SELECT `participant_id` FROM `users` WHERE `line_user_id` = %s;", (line_user_id,))
    result = c.fetchone()
    return result[0] if result else None

def get_latest_monitor(c, line_user_id):
    c.execute("SELECT `monitor_id`, `finished_datetime` FROM `monitors` WHERE `line_user_id` = %s ORDER BY `monitor_id` DESC LIMIT 1;", (line_user_id,))
    return c.fetchone()

def get_sending_datetime(c, monitor_id):
    c.execute("SELECT `sending_datetime` FROM `monitors` WHERE `monitor_id` = %s;", (monitor_id,))
    result = c.fetchone()
    return result[0] if result else None

def get_mood_name(c, mood_id):
    c.execute("SELECT `mood_name` FROM `moods` WHERE `mood_id` = %s;", (mood_id,))
    result = c.fetchone()
    return result[0] if result else None

def get_max_mood_number(c, monitor_id):
    c.execute("SELECT MAX(`mood_number`) FROM `monitor_details` WHERE `monitor_id` = %s;", (monitor_id,))
    result = c.fetchone()
    return result[0] if result else None

def get_latest_moods_with_intensities(c, line_user_id):
    c.execute("""
        SELECT m.mood_name, md.intensity
        FROM monitor_details md
        INNER JOIN moods m ON md.mood_id = m.mood_id
        WHERE md.line_user_id = %s AND md.monitor_id = (
            SELECT MAX(monitor_id) FROM monitor_details WHERE line_user_id = %s
        )
        ORDER BY md.mood_number;
    """, (line_user_id, line_user_id))
    return c.fetchall()

def get_all_mood_names(c):
    c.execute("SELECT mood_id, mood_name, valence FROM moods ORDER BY sort_order;")
    return c.fetchall()

def get_scale_range_values(c):
    """
    スケールの選択肢を取得する
    
    Returns:
        list: スケールの選択肢のリスト（例：["1", "2", "3", "4", "5", "6"]）
    """
    c.execute("SELECT min_value, max_value FROM scale_ranges;")
    result = c.fetchone()
    return [str(i) for i in range(result[0], result[1] + 1)]

def get_active_message_templates(c):
    """すべての有効なメッセージテンプレートを取得する"""
    c.execute("""
        SELECT `target_group`, `message_content` 
        FROM `message_templates` 
        WHERE `is_disabled` = 0;
    """)
    return c.fetchall()

def get_users_for_message(c, group_id):
    c.execute("""
        SELECT `line_user_id`, `participant_id`, `is_temporary_send`, `group_id` 
        FROM `users` 
        WHERE `is_temporary_send` = 1 
        AND `group_id` = %s;
    """, (group_id,))
    return c.fetchall()

def get_valence(c, mood_id):
    c.execute("SELECT `valence` FROM `moods` WHERE `mood_id` = %s;", (mood_id,))
    result = c.fetchone()
    return result[0] if result else None

def get_participant_id_lock_status(c, line_user_id):
    """
    参加者IDのロック状態を取得する
    Returns:
        int: 1=ロック有効、0=ロック無効
    """
    c.execute("SELECT is_participant_id_locked FROM users WHERE line_user_id = %s", (line_user_id,))
    result = c.fetchone()
    return result[0] if result else 0  # 結果がNoneの場合は0（ロック無効）を返す
