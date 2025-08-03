def insert_notification_plans(c, date, time1, time2, time3):
    c.execute("""
        INSERT INTO `notification_plans` (`sending_date`, `sending_number`, `sending_time`) 
        VALUES 
        (%s, %s, %s),
        (%s, %s, %s),
        (%s, %s, %s);
    """, (date, 1, time1, date, 2, time2, date, 3, time3))

def insert_monitor(c, line_user_id, datetime_now):
    c.execute("INSERT INTO `monitors` (`line_user_id`, `sending_datetime`) VALUES (%s, %s);", (line_user_id, datetime_now))

def update_notification_plan_sent_time(c, datetime_now, date, sending_number):
    c.execute("UPDATE `notification_plans` SET `sent_time` = %s WHERE `sending_date` = %s AND `sending_number` = %s;", (datetime_now, date, sending_number))

def update_user_input_mode(c, line_user_id, mode):
    c.execute("UPDATE `users` SET `input_mode`= %s WHERE line_user_id=%s;", (mode, line_user_id))

def insert_user(c, line_user_id):
    c.execute("INSERT INTO `users` (`line_user_id`) VALUES (%s);", (line_user_id,))

def update_user_participant_id(c, participant_id, line_user_id):
    c.execute("UPDATE `users` SET `participant_id` = %s WHERE `line_user_id` = %s;", (participant_id, line_user_id))

def insert_monitor_detail(c, monitor_id, line_user_id, mood_number, mood_id):
    c.execute(
        "INSERT INTO monitor_details (monitor_id, line_user_id, mood_number, mood_id) VALUES (%s, %s, %s, %s);",
        (monitor_id, line_user_id, mood_number, mood_id)
    )

def update_monitor_detail_intensity(c, intensity, monitor_id):
    c.execute(
        "UPDATE monitor_details SET intensity = %s WHERE monitor_id = %s ORDER BY mood_number DESC LIMIT 1;",
        (int(intensity), monitor_id)
    )

def update_monitor_finished_datetime(c, finished_datetime, line_user_id):
    c.execute(
        "UPDATE monitors SET finished_datetime = %s WHERE line_user_id = %s ORDER BY monitor_id DESC LIMIT 1;",
        (finished_datetime, line_user_id)
    )

def update_monitor_responding_datetime(c, responding_datetime, monitor_id):
    c.execute(
        "UPDATE monitors SET responding_datetime = %s WHERE monitor_id = %s;",
        (responding_datetime, monitor_id)
    )
