from linebot.models import BubbleContainer, FlexSendMessage

from modules.button_generator import generate_scale_buttons


class ScaleButtons:
    @staticmethod
    def get_scale_buttons(min_scale, max_scale):
        """リッカート尺度のボタンを取得する
        
        Args:
            min_scale (int): 最小値
            max_scale (int): 最大値
        """
        scale_buttons = generate_scale_buttons(min_scale, max_scale)
        return FlexSendMessage(
            alt_text="どの程度感じていますか？",
            contents=BubbleContainer.new_from_json_dict(scale_buttons)
        )