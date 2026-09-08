from typing import List

from app.schemas.intelligence import InsightItem
from app.services.intelligence.explanation.base import BaseExplanationTemplate


class EmergingTrendExplanationTemplate(BaseExplanationTemplate):
    """
    Explanation generator specialized for Emerging Trend insights.
    """

    def generate_facts(self, insight: InsightItem) -> List[str]:
        facts: List[str] = []
        ev = insight.evidence

        # Fact 1: Volume & Growth
        if ev.current_volume is not None and ev.baseline_volume is not None and ev.growth_rate is not None:
            facts.append(
                f"Current activity is {ev.current_volume} posts compared with a baseline of {ev.baseline_volume} posts, "
                f"representing {ev.growth_rate:+.1f}% growth."
            )
        elif ev.current_volume is not None and ev.growth_rate is not None:
            facts.append(f"Current activity is {ev.current_volume} posts with a growth rate of {ev.growth_rate:+.1f}%.")
        elif ev.current_volume is not None:
            facts.append(f"Current activity reached {ev.current_volume} posts in the observation window.")

        # Fact 2: Statistical anomaly indicator if present
        if ev.z_score is not None:
            facts.append(f"Activity is {ev.z_score:.2f} standard deviations above the historical baseline mean.")

        # Fact 3: Platform distribution if present
        if ev.platforms:
            plat_str = ", ".join(ev.platforms)
            facts.append(f"Activity was detected across {len(ev.platforms)} platforms: {plat_str}.")

        # Fact 4: Traceable records if present
        if ev.post_ids:
            facts.append(f"Analysis is directly grounded in {len(ev.post_ids)} traceable database post records.")

        return facts

    def generate_interpretation(self, insight: InsightItem) -> str:
        topic_name = insight.affected_topic or "This topic"
        return (
            f"Activity for '{topic_name}' is accelerating substantially relative to historical baselines. "
            "This indicates emerging narrative momentum that warrants continuous monitoring for potential escalation."
        )
