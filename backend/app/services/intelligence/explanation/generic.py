from typing import List

from app.schemas.intelligence import InsightItem
from app.services.intelligence.explanation.base import BaseExplanationTemplate


class GenericExplanationTemplate(BaseExplanationTemplate):
    """
    Fallback explanation template for general intelligence insights.
    """

    def generate_facts(self, insight: InsightItem) -> List[str]:
        facts: List[str] = []
        ev = insight.evidence

        if ev.current_volume is not None:
            facts.append(f"Recorded activity volume is {ev.current_volume} posts.")
        if ev.growth_rate is not None:
            facts.append(f"Observed growth rate is {ev.growth_rate:+.1f}%.")
        if ev.z_score is not None:
            facts.append(f"Statistical deviation is {ev.z_score:.2f} standard deviations.")
        if ev.platforms:
            facts.append(f"Observed on platforms: {', '.join(ev.platforms)}.")
        if ev.dominant_sentiment is not None:
            facts.append(f"Dominant sentiment classification is {ev.dominant_sentiment}.")
        if ev.post_ids:
            facts.append(f"Grounded in {len(ev.post_ids)} database records.")

        if not facts:
            facts.append("Signal synthesized from current telemetry parameters.")

        return facts

    def generate_interpretation(self, insight: InsightItem) -> str:
        return (
            f"Insight '{insight.title}' highlights an operational signal detected during telemetry analysis. "
            "Reviewing associated metric indicators is recommended to determine appropriate follow-up actions."
        )
