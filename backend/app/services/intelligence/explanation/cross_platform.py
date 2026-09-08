from typing import List

from app.schemas.intelligence import InsightItem
from app.services.intelligence.explanation.base import BaseExplanationTemplate


class CrossPlatformExplanationTemplate(BaseExplanationTemplate):
    """
    Explanation generator specialized for Cross-Platform Propagation insights.
    """

    def generate_facts(self, insight: InsightItem) -> List[str]:
        facts: List[str] = []
        ev = insight.evidence

        # Fact 1: Multi-platform distribution
        if ev.platforms:
            facts.append(
                f"Narrative activity is verified across {len(ev.platforms)} distinct platforms: {', '.join(ev.platforms)}."
            )

        # Fact 2: Volume
        if ev.current_volume is not None:
            facts.append(f"A total of {ev.current_volume} aggregate posts were recorded across the active channels.")

        # Fact 3: Traceable post records
        if ev.post_ids:
            facts.append(f"Ground truth evidence links to {len(ev.post_ids)} database post records.")

        return facts

    def generate_interpretation(self, insight: InsightItem) -> str:
        topic_name = insight.affected_topic or "This narrative"
        plats_str = ", ".join(insight.evidence.platforms) if insight.evidence.platforms else "multiple channels"
        return (
            f"Discussion surrounding '{topic_name}' is actively propagating across {plats_str}. "
            "Multi-channel presence demonstrates that the narrative is not isolated to an insular community, but is achieving cross-network audience reach."
        )
