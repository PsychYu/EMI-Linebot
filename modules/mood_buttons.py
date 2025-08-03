from linebot.models import BubbleContainer, FlexSendMessage, TextSendMessage

from constants import BUTTON_TYPE_ADDITIONAL_MOOD, BUTTON_TYPE_INITIAL_MOOD
from modules.button_generator import generate_mood_carousel


class MoodButtons:
    @staticmethod
    def get_initial_mood_buttons(c, mood_words):
        """最初に提示する気分ボタンを生成"""
        carousel = generate_mood_carousel(mood_words, BUTTON_TYPE_INITIAL_MOOD)
        return FlexSendMessage(
            alt_text="いまの気分は、次のうちどれに最も近いですか？（以下のボタンは90分間有効です）",
            contents=BubbleContainer.new_from_json_dict(carousel)
        )

    @staticmethod
    def get_additional_mood_buttons(c, mood_words):
        """追加の気分ボタンを生成"""
        carousel = generate_mood_carousel(mood_words, BUTTON_TYPE_ADDITIONAL_MOOD)
        return FlexSendMessage(
            alt_text="他に感じた気分や感情はありますか？",
            contents=BubbleContainer.new_from_json_dict(carousel)
        )

    @staticmethod
    def get_initial_message(c, mood_words):
        return [
            TextSendMessage(text="いまの気分や感情は、次のうちどれに最も近いですか？（以下のボタンは90分間有効です）"),
            MoodButtons.get_initial_mood_buttons(c, mood_words)
        ]

    @staticmethod
    def get_additional_message(c, mood_words):
        return MoodButtons.get_additional_mood_buttons(c, mood_words)