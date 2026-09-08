from typing import List

from app.schemas.intelligence import InsightItem
from app.services.intelligence.explanation.base import BaseExplanationTemplate


class AnomalousSpikeExplanationTemplate(BaseExplanationTemplate):
    """
    Explanation generator specialized for Anomalous Activity Spike insights.
    """

    def generate_facts(self, insight: InsightItem) -> List[str]:
        facts: List[str] = []
        ev = insight.evidence

        # Fact 1: Z-score & Volume Surge
        if ev.z_score is not None and ev.current_volume is not None:
            baseline_str = f" (baseline: {ev.baseline_volume})" if ev.baseline_volume is not None else ""
            facts.append(
                f"Activity is {ev.z_score:.2f} standard deviations above the historical baseline, "
                f"reaching {ev.current_volume} posts{baseline_str}."
            )
        elif ev.z_score is not None:
            facts.append(f"Volume is {ev.z_score:.2f} standard deviations above the historical baseline.")
        elif ev.current_volume is not None:
            facts.append(f"Current volume surged to {ev.current_volume} posts in the observation window.")

        # Fact 2: Growth rate if present
        if ev.growth_rate is not None:
            facts.append(f"Surge represents a growth rate of {ev.growth_rate:+.1f}% over the reference period.")

        # Fact 3: Platform distribution
        if ev.platforms:
            facts.append(f"Spike activity was observed across {len(ev.platforms)} platforms: {', '.join(ev.platforms)}.")

        # Fact 4: Traceable database post records
        if ev.post_ids:
            facts.append(f"Evidence is backed by {len(ev.post_ids)} verifiable database post records.")

        return facts

    def generate_interpretation(self, insight: InsightItem) -> str:
        topic_name = insight.affected_topic or "This topic"
        return (
            f"Activity for '{topic_name}' exhibits an acute statistical surge. "
            "Such sudden elevation typically signals breaking developments, rapid discussion escalation, or concentrated posting activity that requires immediate source inspection."
        )
