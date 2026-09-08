import math
import re
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.sentiment import SentimentLabel, SentimentProbabilities
from app.services.sentiment.base import BaseSentimentEngine, SentimentInferenceResult


# Standard social-media valence dictionary (term -> base valence weight)
DEFAULT_VALENCE_LEXICON: Dict[str, float] = {
    # Strong positive terms (+2.0 to +3.0)
    "amazing": 3.0,
    "excellent": 3.0,
    "outstanding": 3.0,
    "awesome": 3.0,
    "brilliant": 3.0,
    "breakthrough": 2.8,
    "victory": 2.8,
    "love": 3.0,
    "loved": 2.8,
    "loving": 2.8,
    "thrilled": 3.0,
    "fantastic": 3.0,
    "superb": 3.0,
    "great": 2.2,
    "good": 1.5,
    "beautiful": 2.0,
    "operational": 1.5,
    "successful": 2.5,
    "success": 2.5,
    "triumph": 2.5,
    "innovative": 2.2,
    "innovation": 2.0,
    "improve": 1.8,
    "improved": 1.8,
    "improvement": 1.8,
    "proud": 2.2,
    "excited": 2.5,
    "exciting": 2.5,
    "wonderful": 2.8,
    "best": 3.0,
    "happy": 2.5,
    "glad": 1.8,
    "joy": 2.5,
    "support": 1.5,
    "supported": 1.5,
    "win": 2.5,
    "winner": 2.5,
    "winning": 2.5,
    "perfect": 3.0,
    "nice": 1.5,
    "fast": 1.2,
    "secure": 1.8,
    "safe": 1.5,
    "reliable": 2.0,
    "wow": 2.0,
    "kudos": 2.5,
    "goat": 2.5,
    "helpful": 1.8,
    "clean": 1.2,
    "cleanest": 2.0,
    "seamless": 2.0,
    "recommend": 2.0,
    "recommended": 2.0,
    "positive": 1.8,
    "efficient": 2.0,
    "promising": 2.0,
    "congratulations": 2.5,
    "congrats": 2.5,

    # Strong negative terms (-1.5 to -3.5)
    "terrible": -3.0,
    "awful": -3.0,
    "horrible": -3.0,
    "worst": -3.0,
    "hate": -3.0,
    "hated": -2.8,
    "hating": -2.8,
    "disaster": -3.0,
    "failure": -2.8,
    "fail": -2.5,
    "failed": -2.5,
    "failing": -2.5,
    "bad": -2.0,
    "poor": -1.8,
    "crash": -2.5,
    "crashed": -2.5,
    "crashing": -2.5,
    "bug": -2.0,
    "buggy": -2.2,
    "bugs": -2.0,
    "broken": -2.5,
    "scam": -3.0,
    "scammer": -3.0,
    "fraud": -3.0,
    "corrupt": -2.8,
    "corruption": -2.8,
    "lag": -1.8,
    "laggy": -2.0,
    "delay": -1.5,
    "delayed": -1.5,
    "delays": -1.5,
    "angry": -2.5,
    "anger": -2.5,
    "furious": -3.0,
    "disappointed": -2.5,
    "disappointing": -2.5,
    "disappointment": -2.5,
    "useless": -2.8,
    "trash": -3.0,
    "garbage": -3.0,
    "suck": -2.8,
    "sucks": -2.8,
    "slow": -1.5,
    "risk": -1.8,
    "dangerous": -2.5,
    "threat": -2.5,
    "crisis": -2.8,
    "lose": -2.2,
    "loss": -2.2,
    "losing": -2.2,
    "loser": -2.5,
    "pain": -2.0,
    "painful": -2.2,
    "waste": -2.2,
    "wasted": -2.2,
    "warning": -1.2,
    "fault": -2.0,
    "faulty": -2.2,
    "flaw": -2.0,
    "flawed": -2.2,
    "vulnerable": -2.2,
    "vulnerability": -2.2,
    "negative": -1.8,
    "frustrating": -2.5,
    "frustrated": -2.5,
    "frustration": -2.5,
    "annoying": -2.0,
    "annoyed": -2.0,
    "abysmal": -3.0,
    "dreadful": -3.0,
}

# Emoji valence dictionary
DEFAULT_EMOJI_LEXICON: Dict[str, float] = {
    # Positive emojis
    "🚀": 2.5,
    "🔥": 2.0,
    "🌟": 2.2,
    "⭐": 1.8,
    "❤️": 2.8,
    "💖": 2.8,
    "😊": 2.0,
    "😃": 2.2,
    "😄": 2.2,
    "👍": 1.8,
    "👏": 2.0,
    "🎉": 2.5,
    "🥳": 2.5,
    "💯": 2.5,
    "✨": 1.8,
    "🙌": 2.0,
    "🤩": 2.5,
    "🥰": 2.5,
    "💪": 2.0,
    "🏆": 2.5,
    "🥂": 2.0,
    "😍": 2.8,
    "😎": 2.0,
    "🤝": 1.5,

    # Negative emojis
    "💩": -2.5,
    "😡": -3.0,
    "🤬": -3.5,
    "💔": -2.8,
    "👎": -2.0,
    "😢": -2.2,
    "😭": -2.5,
    "🤮": -3.0,
    "🤢": -2.5,
    "🗑️": -2.5,
    "💀": -1.5,
    "🤦‍♂️": -1.8,
    "🤦‍♀️": -1.8,
    "🤦": -1.8,
    "😞": -2.0,
    "😠": -2.5,
    "👿": -2.5,
    "📉": -1.8,
    "❌": -1.5,
    "⚠️": -1.2,
}

# Intensifier/Booster words (boosts preceding or subsequent valence by +0.35)
INTENSIFIERS: Set[str] = {
    "very", "extremely", "incredibly", "super", "highly", "so", "really",
    "absolutely", "totally", "deeply", "immensely", "exceptionally", "ultra",
    "massively", "wildly", "truly",
}

# Diminisher words (reduces valence magnitude by -0.30)
DIMINISHERS: Set[str] = {
    "barely", "hardly", "slightly", "somewhat", "little", "marginally",
    "scarcely", "kind", "kinda", "sorta",
}

# Negation words (flips polarity of subsequent words)
NEGATIONS: Set[str] = {
    "not", "never", "no", "isnt", "isn't", "wasnt", "wasn't", "arent", "aren't",
    "werent", "weren't", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't",
    "cant", "can't", "cannot", "wont", "won't", "wouldnt", "wouldn't", "shouldnt",
    "shouldn't", "havent", "haven't", "hasnt", "hasn't", "hadnt", "hadn't",
    "neither", "nor", "none", "without", "hardly", "barely",
}


class RuleBasedSentimentEngine(BaseSentimentEngine):
    """
    Lightweight, deterministic social-media sentiment inference engine.
    Analyzes lexical valence, emojis, negations, intensifiers, capitalization,
    and punctuation without requiring external network dependencies or heavyweight ML runtimes.
    """

    def __init__(
        self,
        valence_lexicon: Optional[Dict[str, float]] = None,
        emoji_lexicon: Optional[Dict[str, float]] = None,
        alpha_scaling: float = 15.0,
    ):
        self._valence_lexicon = dict(DEFAULT_VALENCE_LEXICON if valence_lexicon is None else valence_lexicon)
        self._emoji_lexicon = dict(DEFAULT_EMOJI_LEXICON if emoji_lexicon is None else emoji_lexicon)
        self._alpha = alpha_scaling

    @property
    def model_name(self) -> str:
        return "insightx-rule-based-v1"

    def _tokenize(self, text: str) -> List[str]:
        """Splits text into alphanumeric tokens, hashtags, and words."""
        # Normalize punctuation spacing
        cleaned = re.sub(r"[^\w\s#@]", " ", text)
        tokens = [t.strip() for t in cleaned.split() if t.strip()]
        return tokens

    def _extract_emojis(self, text: str) -> List[str]:
        """Extracts individual emoji characters from text."""
        found = []
        for char in text:
            if char in self._emoji_lexicon:
                found.append(char)
        return found

    def analyze_text(self, text: str) -> SentimentInferenceResult:
        """
        Calculates sentiment polarity score, class label, confidence,
        and probability distribution for the given text.
        """
        if not text or not text.strip():
            # Neutral fallback for empty input
            return SentimentInferenceResult(
                label=SentimentLabel.NEUTRAL,
                score=0.0,
                confidence=1.0,
                probabilities=SentimentProbabilities(positive=0.0, neutral=1.0, negative=0.0),
                model_name=self.model_name,
                details={"reason": "empty_text", "raw_valence": 0.0},
            )

        tokens = self._tokenize(text)
        emojis = self._extract_emojis(text)

        total_valence = 0.0
        pos_words_matched: List[str] = []
        neg_words_matched: List[str] = []
        emojis_matched: List[str] = []
        negation_active = False
        intensifier_boost = 0.0

        for i, token in enumerate(tokens):
            clean_token = token.lower().lstrip("#@")
            is_all_caps = token.isupper() and len(token) > 1 and token.isalpha()

            # Check negation
            if clean_token in NEGATIONS:
                negation_active = True
                continue

            # Check intensifier / diminisher
            if clean_token in INTENSIFIERS:
                intensifier_boost = 0.35
                continue
            elif clean_token in DIMINISHERS:
                intensifier_boost = -0.30
                continue

            # Check valence lexicon
            if clean_token in self._valence_lexicon:
                base_valence = self._valence_lexicon[clean_token]

                # Apply intensifier / diminisher
                if base_valence > 0:
                    val = base_valence + intensifier_boost
                else:
                    val = base_valence - intensifier_boost

                # Apply ALL CAPS amplification
                if is_all_caps:
                    val *= 1.35

                # Apply negation flip
                if negation_active:
                    val = -0.75 * val
                    negation_active = False

                total_valence += val

                if val > 0:
                    pos_words_matched.append(token)
                elif val < 0:
                    neg_words_matched.append(token)

                # Reset single-use intensifier boost
                intensifier_boost = 0.0
            else:
                # Reset negation if token is a separator or distant
                if negation_active and i > 0 and len(clean_token) > 2:
                    # Negation wears off after 2 non-lexicon words
                    negation_active = False

        # Add emoji valence
        for emo in emojis:
            emo_val = self._emoji_lexicon.get(emo, 0.0)
            total_valence += emo_val
            emojis_matched.append(emo)
            if emo_val > 0:
                pos_words_matched.append(emo)
            elif emo_val < 0:
                neg_words_matched.append(emo)

        # Exclamation point booster
        exclamation_count = text.count("!")
        if exclamation_count > 0 and abs(total_valence) > 0.1:
            exclamation_multiplier = 1.0 + min(0.35, exclamation_count * 0.08)
            total_valence *= exclamation_multiplier

        # Normalization to [-1.0, 1.0] compound score
        if total_valence != 0.0:
            compound_score = total_valence / math.sqrt((total_valence ** 2) + self._alpha)
        else:
            compound_score = 0.0

        compound_score = max(-1.0, min(1.0, round(compound_score, 4)))

        # Determine class label based on thresholds
        if compound_score >= 0.05:
            label = SentimentLabel.POSITIVE
        elif compound_score <= -0.05:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL

        # Calculate class probabilities via calibrated softmax
        # Logits tailored to compound score
        z_pos = max(0.0, compound_score * 3.0)
        z_neg = max(0.0, -compound_score * 3.0)
        z_neu = max(0.2, 1.0 - abs(compound_score) * 1.5)

        exp_pos = math.exp(z_pos)
        exp_neg = math.exp(z_neg)
        exp_neu = math.exp(z_neu)
        denom = exp_pos + exp_neg + exp_neu

        prob_pos = round(exp_pos / denom, 4)
        prob_neg = round(exp_neg / denom, 4)
        prob_neu = round(1.0 - prob_pos - prob_neg, 4)
        # Ensure non-negative rounding
        prob_neu = max(0.0, min(1.0, prob_neu))

        probabilities = SentimentProbabilities(
            positive=prob_pos,
            neutral=prob_neu,
            negative=prob_neg,
        )

        confidence = round(max(prob_pos, prob_neu, prob_neg), 4)

        details = {
            "raw_valence": round(total_valence, 4),
            "positive_cues": pos_words_matched,
            "negative_cues": neg_words_matched,
            "emojis_detected": emojis_matched,
            "exclamations": exclamation_count,
        }

        return SentimentInferenceResult(
            label=label,
            score=compound_score,
            confidence=confidence,
            probabilities=probabilities,
            model_name=self.model_name,
            details=details,
        )
