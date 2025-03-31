import json

from linebot.models import BubbleContainer, FlexSendMessage

from constants import (BUTTON_TEXT_CANCEL, BUTTON_TEXT_START,
                       ID_REGISTRATION_ACCEPT, ID_REGISTRATION_REJECT)


class IDRegistration:
    # ID登録のコンファーム
    registration_buttons = """{
    "type": "bubble",
    "direction": "ltr",
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
        {
            "type": "text",
            "text": "ID登録を開始しますか？",
            "align": "center",
            "contents": []
        }
        ]
    },
    "footer": {
        "type": "box",
        "layout": "horizontal",
        "contents": [
        {
            "type": "button",
            "action": {
            "type": "postback",
            "label": \"""" + BUTTON_TEXT_START + """\",
            "text": \"""" + BUTTON_TEXT_START + """\",
            "data": \"""" + ID_REGISTRATION_ACCEPT + """\"
            }
        },
        {
            "type": "button",
            "action": {
            "type": "postback",
            "label": \"""" + BUTTON_TEXT_CANCEL + """\",
            "text": \"""" + BUTTON_TEXT_CANCEL + """\",
            "data": \"""" + ID_REGISTRATION_REJECT + """\"
            }
        }
        ]
    }
    }"""
    
    registration_message = FlexSendMessage(alt_text="ID登録を開始しますか？",
            contents=BubbleContainer.new_from_json_dict(json.loads(registration_buttons))
            )