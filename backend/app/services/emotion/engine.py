import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.emotion import EmotionLabel, EmotionProbabilities
from app.services.emotion.base import BaseEmotionEngine, EmotionInferenceResult


# Comprehensive emotion lexicons for 6 active emotions
JOY_LEXICON: Dict[str, float] = {
    "happy": 2.5, "happiness": 2.5, "joy": 2.8, "joyful": 2.8, "thrilled": 3.0,
    "excited": 2.8, "excitement": 2.8, "delighted": 2.8, "delight": 2.8, "love": 3.0,
    "loved": 2.8, "loving": 2.8, "awesome": 2.5, "great": 2.0, "wonderful": 2.8,
    "fantastic": 3.0, "amazing": 2.8, "blessed": 2.5, "congrats": 2.5,
    "congratulations": 2.8, "proud": 2.5, "triumph": 2.8, "victory": 2.8,
    "celebrating": 2.8, "celebration": 2.8, "superb": 3.0, "brilliant": 2.8,
    "cheers": 2.2, "hurray": 2.5, "smile": 2.0, "smiling": 2.0, "laugh": 2.0,
    "laughing": 2.0, "glad": 2.0, "ecstatic": 3.2, "enjoy": 2.2, "enjoying": 2.2,
    "enjoyed": 2.0, "best": 2.5, "promising": 2.0, "perfect": 2.8, "good": 1.5,
    "nice": 1.5, "goat": 2.5, "win": 2.5, "winner": 2.5, "winning": 2.5,
    "cheerful": 2.5, "glee": 2.5, "jubilant": 3.0, "elated": 3.0, "pleased": 1.8,
    "yay": 2.5,
}

SADNESS_LEXICON: Dict[str, float] = {
    "sad": 2.5, "sadness": 2.5, "depressed": 3.0, "depression": 3.0,
    "heartbroken": 3.2, "heartbreak": 3.2, "grief": 3.2, "grieving": 3.2,
    "mourning": 3.0, "mourn": 3.0, "unhappy": 2.2, "lonely": 2.5, "loneliness": 2.5,
    "miserable": 2.8, "misery": 2.8, "crying": 2.8, "tears": 2.5, "tear": 2.2,
    "cry": 2.5, "disappointed": 2.5, "disappointment": 2.5, "disappointing": 2.5,
    "hopeless": 3.0, "devastated": 3.2, "devastating": 3.2, "tragic": 3.0,
    "tragedy": 3.0, "loss": 2.5, "lost": 2.0, "losing": 2.0, "sorry": 1.8,
    "pity": 2.0, "pain": 2.2, "painful": 2.5, "hurt": 2.2, "hurting": 2.2,
    "down": 1.5, "sorrow": 2.8, "regret": 2.2, "regretting": 2.2, "miss": 1.8,
    "missing": 1.8, "gloomy": 2.2, "heartache": 3.0, "despair": 3.2,
}

ANGER_LEXICON: Dict[str, float] = {
    "angry": 2.8, "anger": 2.8, "furious": 3.2, "fury": 3.2, "mad": 2.5,
    "outraged": 3.2, "outrage": 3.2, "enraged": 3.2, "irritated": 2.2,
    "irritating": 2.2, "irritation": 2.2, "pissed": 2.8, "infuriating": 3.0,
    "hate": 3.0, "hated": 2.8, "hating": 2.8, "scam": 2.8, "scammer": 2.8,
    "trash": 2.5, "garbage": 2.5, "annoyed": 2.2, "annoying": 2.2, "ridiculous": 2.2,
    "disgrace": 2.8, "corrupt": 2.8, "corruption": 2.8, "bullshit": 3.0, "rage": 3.0,
    "raging": 3.0, "frustrated": 2.5, "frustrating": 2.5, "frustration": 2.5,
    "offensive": 2.5, "cheat": 2.8, "cheating": 2.8, "cheated": 2.8, "liar": 2.8,
    "lies": 2.5, "lied": 2.5, "abuse": 3.0, "abusive": 3.0, "hostile": 2.8,
    "screwed": 2.5, "suck": 2.5, "sucks": 2.5, "infuriated": 3.2, "wrath": 3.0,
}

FEAR_LEXICON: Dict[str, float] = {
    "scared": 2.8, "scary": 2.5, "terrified": 3.2, "terror": 3.2, "afraid": 2.5,
    "frightened": 2.8, "frightening": 2.8, "anxious": 2.5, "anxiety": 2.8,
    "panic": 3.0, "panicked": 3.0, "panicking": 3.0, "dread": 2.8, "dreading": 2.8,
    "nervous": 2.2, "nervousness": 2.2, "warning": 2.0, "warn": 1.8, "threat": 2.8,
    "threatening": 2.8, "threatened": 2.8, "danger": 2.8, "dangerous": 2.8,
    "crisis": 2.8, "fear": 2.8, "fearful": 2.8, "feared": 2.5, "worried": 2.5,
    "worrying": 2.5, "worry": 2.2, "worries": 2.2, "alarm": 2.5, "alarming": 2.8,
    "horror": 3.0, "horrific": 3.0, "vulnerable": 2.2, "vulnerability": 2.5,
    "risk": 2.0, "risky": 2.2, "unsafe": 2.5, "insecure": 2.2, "paralyzed": 2.8,
    "trembling": 2.5, "phobia": 2.8, "dreadful": 2.8, "spooked": 2.2,
}

SURPRISE_LEXICON: Dict[str, float] = {
    "shocked": 3.0, "shocking": 3.0, "shock": 2.8, "stunned": 3.0, "stunning": 2.8,
    "astonished": 3.0, "astonishing": 3.0, "astonishment": 3.0, "unbelievable": 2.8,
    "unexpected": 2.5, "unexpectedly": 2.5, "whoa": 2.5, "wow": 2.5,
    "mindblown": 3.0, "speechless": 2.8, "surprised": 2.8, "surprising": 2.8,
    "surprise": 2.5, "incredible": 2.5, "amazed": 2.8, "unreal": 2.5, "omg": 2.8,
    "sudden": 2.0, "suddenly": 2.0, "unanticipated": 2.5, "breathtaking": 2.8,
    "unforeseen": 2.5, "jawdropping": 3.0, "wild": 2.0, "insane": 2.2,
    "astounded": 3.0, "startled": 2.5, "flabbergasted": 3.2,
}

DISGUST_LEXICON: Dict[str, float] = {
    "disgusted": 3.0, "disgusting": 3.2, "disgust": 3.0, "gross": 2.8,
    "nasty": 2.8, "repulsive": 3.2, "repulsion": 3.0, "revolting": 3.2,
    "vile": 3.0, "sickening": 3.0, "nauseating": 3.0, "nauseous": 2.8,
    "yuck": 2.8, "eww": 2.8, "cringe": 2.5, "cringey": 2.5, "horrible": 2.5,
    "awful": 2.5, "filthy": 2.8, "dirty": 2.0, "repellent": 2.8, "abhorrent": 3.2,
    "distasteful": 2.5, "rotten": 2.5, "foul": 2.8, "repugnant": 3.2,
    "hideous": 2.8, "slimy": 2.2, "poison": 2.5, "toxic": 2.5, "stink": 2.2,
    "stinks": 2.2, "smelly": 2.0, "loathsome": 3.2, "detestable": 3.0,
}

EMOTION_EMOJIS: Dict[str, Tuple[EmotionLabel, float]] = {
    # Joy
    "😀": (EmotionLabel.JOY, 2.2), "😃": (EmotionLabel.JOY, 2.5),
    "😄": (EmotionLabel.JOY, 2.5), "😁": (EmotionLabel.JOY, 2.5),
    "😊": (EmotionLabel.JOY, 2.2), "🥳": (EmotionLabel.JOY, 3.0),
    "🎉": (EmotionLabel.JOY, 3.0), "🚀": (EmotionLabel.JOY, 2.5),
    "❤️": (EmotionLabel.JOY, 2.8), "💖": (EmotionLabel.JOY, 2.8),
    "🤩": (EmotionLabel.JOY, 2.8), "🥰": (EmotionLabel.JOY, 2.8),
    "👍": (EmotionLabel.JOY, 1.8), "👏": (EmotionLabel.JOY, 2.2),
    "💯": (EmotionLabel.JOY, 2.5), "✨": (EmotionLabel.JOY, 2.0),
    "🏆": (EmotionLabel.JOY, 2.8), "🥂": (EmotionLabel.JOY, 2.2),
    "😇": (EmotionLabel.JOY, 2.0), "😻": (EmotionLabel.JOY, 2.5),

    # Sadness
    "😢": (EmotionLabel.SADNESS, 2.8), "😭": (EmotionLabel.SADNESS, 3.0),
    "😞": (EmotionLabel.SADNESS, 2.5), "😔": (EmotionLabel.SADNESS, 2.5),
    "💔": (EmotionLabel.SADNESS, 3.0), "😿": (EmotionLabel.SADNESS, 2.5),
    "🥺": (EmotionLabel.SADNESS, 2.2), "🌧️": (EmotionLabel.SADNESS, 1.8),
    "🥀": (EmotionLabel.SADNESS, 2.0), "😥": (EmotionLabel.SADNESS, 2.5),
    "😪": (EmotionLabel.SADNESS, 2.0), "🖤": (EmotionLabel.SADNESS, 2.0),

    # Anger
    "😡": (EmotionLabel.ANGER, 3.2), "😠": (EmotionLabel.ANGER, 2.8),
    "🤬": (EmotionLabel.ANGER, 3.5), "👿": (EmotionLabel.ANGER, 2.8),
    "💢": (EmotionLabel.ANGER, 2.5), "🖕": (EmotionLabel.ANGER, 3.5),
    "😤": (EmotionLabel.ANGER, 2.5), "😾": (EmotionLabel.ANGER, 2.2),
    "👊": (EmotionLabel.ANGER, 2.0),

    # Fear
    "😨": (EmotionLabel.FEAR, 2.8), "😰": (EmotionLabel.FEAR, 2.8),
    "😱": (EmotionLabel.FEAR, 3.2), "🥶": (EmotionLabel.FEAR, 2.2),
    "💀": (EmotionLabel.FEAR, 2.0), "⚠️": (EmotionLabel.FEAR, 2.2),
    "🚨": (EmotionLabel.FEAR, 2.5), "🙀": (EmotionLabel.FEAR, 2.5),
    "🫣": (EmotionLabel.FEAR, 2.2), "🆘": (EmotionLabel.FEAR, 2.8),

    # Surprise
    "😲": (EmotionLabel.SURPRISE, 3.0), "😯": (EmotionLabel.SURPRISE, 2.8),
    "🤯": (EmotionLabel.SURPRISE, 3.2), "😮": (EmotionLabel.SURPRISE, 2.5),
    "‼️": (EmotionLabel.SURPRISE, 2.2), "⁉️": (EmotionLabel.SURPRISE, 2.5),
    "😳": (EmotionLabel.SURPRISE, 2.5), "🫢": (EmotionLabel.SURPRISE, 2.5),
    "⚡": (EmotionLabel.SURPRISE, 2.0),

    # Disgust
    "🤮": (EmotionLabel.DISGUST, 3.5), "🤢": (EmotionLabel.DISGUST, 3.2),
    "💩": (EmotionLabel.DISGUST, 2.8), "🗑️": (EmotionLabel.DISGUST, 2.5),
    "👎": (EmotionLabel.DISGUST, 2.2), "😖": (EmotionLabel.DISGUST, 2.5),
    "🤧": (EmotionLabel.DISGUST, 2.0),
}

INTENSIFIERS: Set[str] = {
    "very", "extremely", "super", "so", "really", "deeply", "totally",
    "immensely", "incredibly", "highly", "absolutely", "exceptionally",
    "massively", "wildly", "truly", "ultra",
}

DIMINISHERS: Set[str] = {
    "slightly", "barely", "somewhat", "a bit", "little", "marginally",
    "scarcely", "kind", "kinda", "sorta",
}

NEGATIONS: Set[str] = {
    "not", "never", "no", "isnt", "isn't", "wasnt", "wasn't", "arent", "aren't",
    "werent", "weren't", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't",
    "cant", "can't", "cannot", "wont", "won't", "wouldnt", "wouldn't", "shouldnt",
    "shouldn't", "havent", "haven't", "hasnt", "hasn't", "hadnt", "hadn't",
    "neither", "nor", "none", "without", "hardly", "barely",
}


class RuleBasedEmotionEngine(BaseEmotionEngine):
    """
    Lightweight, deterministic social-media emotion detection engine.
    Classifies text into joy, sadness, anger, fear, surprise, disgust, or neutral,
    accounting for emotion phrases, negations, intensifiers, emojis, and emphasis.
    """

    def __init__(self, neutral_baseline_logit: float = 1.2):
        self._neutral_baseline = neutral_baseline_logit
        self._categories = {
            EmotionLabel.JOY: JOY_LEXICON,
            EmotionLabel.SADNESS: SADNESS_LEXICON,
            EmotionLabel.ANGER: ANGER_LEXICON,
            EmotionLabel.FEAR: FEAR_LEXICON,
            EmotionLabel.SURPRISE: SURPRISE_LEXICON,
            EmotionLabel.DISGUST: DISGUST_LEXICON,
        }

    @property
    def model_name(self) -> str:
        return "insightx-emotion-rule-v1"

    def _tokenize(self, text: str) -> List[str]:
        """Splits text into tokens, preserving hashtags and handles."""
        cleaned = re.sub(r"[^\w\s#@]", " ", text)
        return [t.strip() for t in cleaned.split() if t.strip()]

    def _extract_emojis(self, text: str) -> List[str]:
        """Extracts recognized emotion emojis from text."""
        return [char for char in text if char in EMOTION_EMOJIS]

    def analyze_text(self, text: str) -> EmotionInferenceResult:
        """
        Calculates raw emotion activations across all categories, applies contextual modifiers,
        and generates calibrated probability distribution and primary emotion.
        """
        if not text or not text.strip():
            # Neutral fallback for empty input
            return EmotionInferenceResult(
                primary_emotion=EmotionLabel.NEUTRAL,
                confidence=1.0,
                probabilities=EmotionProbabilities(neutral=1.0),
                model_name=self.model_name,
                details={"reason": "empty_input", "cues": {}},
            )

        tokens = self._tokenize(text)
        emojis = self._extract_emojis(text)

        raw_scores: Dict[EmotionLabel, float] = {
            EmotionLabel.JOY: 0.0,
            EmotionLabel.SADNESS: 0.0,
            EmotionLabel.ANGER: 0.0,
            EmotionLabel.FEAR: 0.0,
            EmotionLabel.SURPRISE: 0.0,
            EmotionLabel.DISGUST: 0.0,
        }

        detected_cues: Dict[str, List[str]] = {label.value: [] for label in EmotionLabel}
        negation_active = False
        intensifier_mult = 1.0

        for i, token in enumerate(tokens):
            clean = token.lower().lstrip("#@")
            is_all_caps = token.isupper() and len(token) > 1 and token.isalpha()

            # Negation tracking
            if clean in NEGATIONS:
                negation_active = True
                continue

            # Intensifier / diminisher tracking
            if clean in INTENSIFIERS:
                intensifier_mult = 1.45
                continue
            elif clean in DIMINISHERS:
                intensifier_mult = 0.55
                continue

            # Match against category lexicons
            matched_any = False
            for label, lexicon in self._categories.items():
                if clean in lexicon:
                    weight = lexicon[clean] * intensifier_mult
                    if is_all_caps:
                        weight *= 1.35

                    if negation_active:
                        # Negation dampens the target emotion and redistributes
                        weight *= 0.15
                        # Shift negative activation toward neutral or opposite
                        if label == EmotionLabel.JOY:
                            raw_scores[EmotionLabel.SADNESS] += 1.0
                        elif label == EmotionLabel.ANGER:
                            raw_scores[EmotionLabel.NEUTRAL] = raw_scores.get(EmotionLabel.NEUTRAL, 0.0) + 1.0
                        negation_active = False
                    else:
                        raw_scores[label] += weight
                        detected_cues[label.value].append(token)

                    matched_any = True
                    intensifier_mult = 1.0

            if not matched_any and negation_active and len(clean) > 2:
                negation_active = False

        # Add emoji weights
        for emo in emojis:
            label, weight = EMOTION_EMOJIS[emo]
            raw_scores[label] += weight
            detected_cues[label.value].append(emo)

        # Exclamation point amplifier
        exclamation_count = text.count("!")
        if exclamation_count > 0:
            top_cat = max(raw_scores, key=lambda k: raw_scores[k])
            if raw_scores[top_cat] > 0.5:
                raw_scores[top_cat] *= (1.0 + min(0.35, exclamation_count * 0.08))

        # Softmax computation over all 7 classes
        # Neutral logit is parameterized by baseline (default 1.2)
        logits: Dict[EmotionLabel, float] = {}
        for label in self._categories:
            logits[label] = raw_scores[label]

        # Neutral logit is higher when active emotions are low
        max_active = max(raw_scores.values()) if raw_scores else 0.0
        if max_active < 1.0:
            logits[EmotionLabel.NEUTRAL] = self._neutral_baseline + (1.0 - max_active)
        else:
            logits[EmotionLabel.NEUTRAL] = max(0.05, self._neutral_baseline - (max_active * 0.4))

        # Exponentiate and normalize
        exp_logits = {lbl: math.exp(val) for lbl, val in logits.items()}
        denom = sum(exp_logits.values())

        raw_probs = {lbl: exp_logits[lbl] / denom for lbl in logits}

        # Round and ensure sum == 1.0
        probs = {lbl: round(raw_probs[lbl], 4) for lbl in raw_probs}
        prob_sum = sum(probs.values())
        diff = round(1.0 - prob_sum, 4)
        if diff != 0:
            # Adjust neutral by remaining rounding epsilon
            probs[EmotionLabel.NEUTRAL] = max(0.0, round(probs[EmotionLabel.NEUTRAL] + diff, 4))

        emotion_probs = EmotionProbabilities(
            joy=probs[EmotionLabel.JOY],
            sadness=probs[EmotionLabel.SADNESS],
            anger=probs[EmotionLabel.ANGER],
            fear=probs[EmotionLabel.FEAR],
            surprise=probs[EmotionLabel.SURPRISE],
            disgust=probs[EmotionLabel.DISGUST],
            neutral=probs[EmotionLabel.NEUTRAL],
        )

        # Determine primary emotion
        primary = max(probs, key=lambda k: probs[k])
        confidence = probs[primary]

        details = {
            "cues": {k: v for k, v in detected_cues.items() if v},
            "raw_activations": {k.value: round(v, 4) for k, v in raw_scores.items()},
            "exclamations": exclamation_count,
        }

        return EmotionInferenceResult(
            primary_emotion=primary,
            confidence=confidence,
            probabilities=emotion_probs,
            model_name=self.model_name,
            details=details,
        )
