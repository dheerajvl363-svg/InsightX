from typing import List

from app.schemas.intelligence import InsightItem
from app.services.intelligence.explanation.base import BaseExplanationTemplate


class SentimentShiftExplanationTemplate(BaseExplanationTemplate):
    """
    Explanation generator specialized for Polarized Sentiment Shift insights.
    """

    def generate_facts(self, insight: InsightItem) -> List[str]:
        facts: List[str] = []
        ev = insight.evidence
        raw = ev.raw_signals or {}

        # Fact 1: Sentiment polarity and dominant classification
        if ev.sentiment_score is not None and ev.dominant_sentiment is not None:
            facts.append(
                f"Discourse exhibits a dominant {ev.dominant_sentiment} polarity "
                f"with an average sentiment score of {ev.sentiment_score:+.2f} (scale: -1.0 to +1.0)."
            )
        elif ev.dominant_sentiment is not None:
            facts.append(f"Discourse is predominantly categorized as {ev.dominant_sentiment}.")
        elif ev.sentiment_score is not None:
            facts.append(f"Average sentiment polarity score is {ev.sentiment_score:+.2f}.")

        # Fact 2: Breakdown counts if present in raw signals
        pos_cnt = raw.get("positive_count")
        neg_cnt = raw.get("negative_count")
        total_cnt = ev.current_volume or raw.get("total_analyzed")

        if pos_cnt is not None and neg_cnt is not None and total_cnt is not None:
            facts.append(
                f"Evaluated {total_cnt} posts: {neg_cnt} negative ({round(neg_cnt/total_cnt*100, 1)}%), "
                f"{pos_cnt} positive ({round(pos_cnt/total_cnt*100, 1)}%)."
            )

        # Fact 3: Platform distribution
        if ev.platforms:
            facts.append(f"Sentiment concentration was recorded across platforms: {', '.join(ev.platforms)}.")

        return facts

    def generate_interpretation(self, insight: InsightItem) -> str:
        dom = (insight.evidence.dominant_sentiment or "").lower()
        if dom == "negative":
            return (
                "The analyzed dataset demonstrates high negative polarity concentration. "
                "This indicates a high proportion of negative sentiment which warrants root-cause review."
            )
        elif dom == "positive":
            return (
                "The analyzed dataset demonstrates strong positive sentiment alignment. "
                "This indicates a high proportion of positive sentiment across the monitored discourse."
            )
        return (
            "A notable shift in sentiment distribution has been recorded. "
            "Monitoring sentiment trajectories will help identify whether polarity stabilizes or diverges further."
        )
