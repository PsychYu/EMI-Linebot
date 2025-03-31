import logging

from constants import INTENSITY_HIGH, INTENSITY_LOW, INTENSITY_MEDIUM
from infra.query import get_latest_moods_with_intensities


class MoodSummarizer:
    def __init__(self, c, line_user_id):
        self.c = c
        self.line_user_id = line_user_id

    # 保存された気分と強度を取得
    def get_summarized_moods(self):
        """
        モニタリング結果を程度+気分のリストに変換する
        例：["少し「落ち込む」", "かなり「不安だ」"]
        """
        try:
            latest_moods_with_intensities = get_latest_moods_with_intensities(self.c, self.line_user_id)
        except Exception as e:
            logging.error(f"気分と強度取得エラー: {e}")
            return []

        # 気分のリスト
        mood_names = [mood[0] for mood in latest_moods_with_intensities]
        # 強度のリスト
        intensities = [mood[1] for mood in latest_moods_with_intensities]

        # 強度を程度に変換したリスト
        intensity_descriptions = []
        for intensity in intensities:
            if intensity <= INTENSITY_LOW:
                intensity_descriptions.append("少し")
            elif intensity <= INTENSITY_MEDIUM:
                intensity_descriptions.append("やや")
            elif intensity <= INTENSITY_HIGH:
                intensity_descriptions.append("かなり")
            else:
                intensity_descriptions.append("強く")

        mood_summaries = []
        for mood_name, intensity_description in zip(mood_names, intensity_descriptions):
            mood_summaries.append(intensity_description + "「" + str(mood_name) + "」")
        return mood_summaries