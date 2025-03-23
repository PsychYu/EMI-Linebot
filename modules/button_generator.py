from constants import BUTTON_TYPE_INITIAL_MOOD, VALENCE_NONE, VALENCE_SEPARATOR


def generate_mood_buttons(mood_words, button_type):
    """感情語ボタンを生成する"""
    buttons = []
    for mood in mood_words:
        mood_id, mood_name, valence = mood
        
        # valenceを整数型に変換
        valence = int(valence) if valence is not None else 0
        
        # initial_mood_buttonの場合は「なし」を空白に置き換える
        if button_type == BUTTON_TYPE_INITIAL_MOOD and valence == VALENCE_NONE:
            # 「なし」ボタンの代わりにフィラー要素を追加
            filler = {
                "type": "filler"
            }
            buttons.append(filler)
            continue
            
        # セパレータの場合
        if valence == VALENCE_SEPARATOR:
            separator = {
                "type": "separator"
            }
            buttons.append(separator)
            continue
            
        button = {
            "type": "button",
            "action": {
                "type": "postback",
                "label": mood_name,
                "text": mood_name,
                "data": f"{button_type} {mood_id}"
            }
        }
        if valence == VALENCE_NONE:  # 「なし」ボタンの場合
            button["color"] = "#C0A074"
        
        buttons.append(button)
    return buttons

def generate_mood_carousel(mood_words, button_type):
    """感情語カルーセルを生成する"""
    buttons = generate_mood_buttons(mood_words, button_type)
    carousel = {
        "type": "bubble",
        "direction": "ltr",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#FFFFFFFF",
            "contents": []
        }
    }

    # ボタンを2列に配置
    current_box = None
    for button in buttons:
        if button["type"] == "separator":
            # セパレータの場合は、現在のboxを追加（存在する場合）し、セパレータを追加
            if current_box:
                # セパレータ前の最後のboxが1つのボタンしかない場合、fillerを追加
                if len(current_box["contents"]) == 1:
                    current_box["contents"].append({"type": "filler"})
                carousel["header"]["contents"].append(current_box)
                current_box = None
            carousel["header"]["contents"].append(button)
            continue
            
        # 新しいboxの作成
        if current_box is None:
            current_box = {
                "type": "box",
                "layout": "horizontal",
                "contents": []
            }
            
        # ボタンをboxに追加
        current_box["contents"].append(button)
        
        # boxが2つのボタンを持っている場合、boxを追加して新しいboxを準備
        if len(current_box["contents"]) == 2:
            carousel["header"]["contents"].append(current_box)
            current_box = None
    
    # 最後の未完成のboxがある場合は、fillerを追加して完成させる
    if current_box:
        if len(current_box["contents"]) == 1:
            current_box["contents"].append({"type": "filler"})
        carousel["header"]["contents"].append(current_box)

    return carousel

def generate_scale_buttons(min_scale, max_scale):
    """リッカート尺度のボタンを生成する

    Args:
        min_scale (int): 最小値
        max_scale (int): 最大値
    """
    scale_buttons = {
        "type": "bubble",
        "direction": "ltr",
        "body": {
            "type": "box",
            "layout": "horizontal",
            "position": "default",
            "contents": [
                {
                    "type": "text",
                    "text": "少し感じる",
                    "align": "start",
                    "contents": []
                },
                {
                    "type": "text",
                    "text": "強く感じる",
                    "align": "end",
                    "contents": []
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": []
        }
    }

    # スケールボタンの生成
    scale_buttons["footer"]["contents"] = [
        {
            "type": "button",
            "action": {
                "type": "postback",
                "label": str(i),
                "text": str(i),
                "data": f"scale_button {i}"
            }
        }
        for i in range(min_scale, max_scale + 1)
    ]

    return scale_buttons