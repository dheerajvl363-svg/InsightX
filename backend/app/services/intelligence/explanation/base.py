from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.intelligence import (
    InsightEvidence,
    InsightEvidenceReferences,
    InsightExplanation,
    InsightItem,
)


class BaseExplanationTemplate(ABC):
    """
    Abstract base template for generating structured, evidence-grounded insight explanations.
    """

    @abstractmethod
    def generate_facts(self, insight: InsightItem) -> List[str]:
        """Extracts strictly factual statements directly supported by evidence."""
        pass

    @abstractmethod
    def generate_interpretation(self, insight: InsightItem) -> str:
        """Produces a cautious, evidence-grounded assessment of why the signal matters."""
        pass

    def generate_rationales(self, insight: InsightItem) -> Tuple[str, str]:
        """
        Generates human-readable rationales explaining the confidence score and severity priority.
        Returns (confidence_rationale, severity_rationale).
        """
        conf_pct = int(round(insight.confidence * 100))
        ev = insight.evidence

        # Confidence rationale
        signals: List[str] = []
        if ev.current_volume is not None:
            signals.append(f"{ev.current_volume} recorded posts")
        if ev.z_score is not None:
            signals.append(f"z-score of {ev.z_score:.2f}")
        if ev.growth_rate is not None:
            signals.append(f"{ev.growth_rate:+.1f}% growth rate")
        if ev.platforms and len(ev.platforms) > 1:
            signals.append(f"corroboration across {len(ev.platforms)} platforms")

        if signals:
            conf_rationale = f"Confidence of {conf_pct}% is supported by {', '.join(signals)}."
        else:
            conf_rationale = f"Confidence of {conf_pct}% is derived from available analytical signals."

        # Severity rationale
        sev_str = insight.severity.value.upper()
        if insight.severity.value in ("critical", "high"):
            sev_rationale = f"Classified as {sev_str} based on high statistical deviation and measured activity acceleration."
        elif insight.severity.value == "medium":
            sev_rationale = f"Classified as {sev_str} indicating moderate measured activity acceleration."
        else:
            sev_rationale = f"Classified as {sev_str} providing baseline informational telemetry."

        return conf_rationale, sev_rationale

    def build_evidence_references(self, insight: InsightItem) -> InsightEvidenceReferences:
        """Constructs traceable references linking the explanation back to data records."""
        ev = insight.evidence
        key_metrics: Dict[str, Any] = {}
        if ev.current_volume is not None:
            key_metrics["current_volume"] = ev.current_volume
        if ev.baseline_volume is not None:
            key_metrics["baseline_volume"] = ev.baseline_volume
        if ev.growth_rate is not None:
            key_metrics["growth_rate"] = ev.growth_rate
        if ev.z_score is not None:
            key_metrics["z_score"] = ev.z_score
        if ev.sentiment_score is not None:
            key_metrics["sentiment_score"] = ev.sentiment_score

        return InsightEvidenceReferences(
            topic_id=ev.topic_id,
            topic_label=ev.topic_label or insight.affected_topic,
            post_ids=list(ev.post_ids or []),
            external_post_ids=list(ev.external_post_ids or []),
            platforms=list(ev.platforms or insight.affected_platforms or []),
            time_window=ev.time_window,
            key_metrics=key_metrics,
        )

    def explain(self, insight: InsightItem) -> InsightExplanation:
        """Assembles the full structured explanation for an insight."""
        facts = self.generate_facts(insight)
        interpretation = self.generate_interpretation(insight)
        conf_rationale, sev_rationale = self.generate_rationales(insight)
        references = self.build_evidence_references(insight)

        return InsightExplanation(
            insight_id=insight.id,
            type=insight.type,
            title=insight.title,
            summary=insight.summary,
            severity=insight.severity,
            confidence=insight.confidence,
            confidence_rationale=conf_rationale,
            severity_rationale=sev_rationale,
            facts=facts,
            interpretation=interpretation,
            recommended_action=insight.recommended_action,
            action_items=list(insight.action_items or []),
            evidence_references=references,
        )
