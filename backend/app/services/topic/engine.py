from sqlalchemy.dialects.postgresql import Any
from collections import Counter
import re
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.topic import ExtractedTopic, SinglePostTopicResult
from app.services.topic.base import BaseTopicEngine


# Comprehensive stopwords list for social media text
DEFAULT_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "due", "during", "each", "etc", "few", "for", "from",
    "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've",
    "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "just",
    "let's", "me", "more", "most", "much", "must", "mustn't", "my", "myself",
    "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "re", "same",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd",
    "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "via", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom",
    "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    "will", "shall", "may", "might", "like", "get", "got", "going", "make",
    "know", "see", "think", "take", "come", "want", "look", "use", "tell",
    "today", "yesterday", "tomorrow",
}

# Short meaningful acronyms allowed even if len < 3
ALLOWED_SHORT_ACRONYMS: Set[str] = {
    "ai", "ml", "ui", "ux", "db", "ev", "vr", "ar", "os", "ip", "id", "pr", "hr", "qa",
}


class RuleBasedTopicEngine(BaseTopicEngine):
    """
    Lightweight, deterministic social-media topic extraction and clustering engine.
    Extracts keywords, multi-word phrases, and hashtags from individual posts,
    and clusters related posts into cohesive topic groups using token/phrase overlap.
    """

    def __init__(
        self,
        stopwords: Optional[Set[str]] = None,
        min_cluster_similarity: float = 0.20,
    ):
        self._stopwords = set(DEFAULT_STOPWORDS if stopwords is None else stopwords)
        self._min_similarity = min_cluster_similarity

    @property
    def model_name(self) -> str:
        return "insightx-topic-rule-v1"

    def _extract_tokens_and_hashtags(self, text: str) -> Tuple[List[str], List[str]]:
        """Extracts cleaned word tokens and hashtags."""
        hashtags = [h.lower() for h in re.findall(r"#(\w+)", text)]

        # Replace URLs and special characters with spaces
        clean_text = re.sub(r"https?://\S+", " ", text)
        clean_text = re.sub(r"[^\w\s]", " ", clean_text)

        words = [w.strip().lower() for w in clean_text.split() if w.strip()]
        return words, hashtags

    def _get_meaningful_unigrams(self, words: List[str]) -> List[str]:
        """Filters words down to meaningful candidate keywords."""
        unigrams = []
        for w in words:
            if w in self._stopwords:
                continue
            if w.isdigit():
                continue
            if len(w) < 3 and w not in ALLOWED_SHORT_ACRONYMS:
                continue
            unigrams.append(w)
        return unigrams

    def _get_phrases(self, words: List[str]) -> List[str]:
        """Extracts 2-word (bigram) and 3-word (trigram) candidate phrases."""
        phrases: List[str] = []
        n = len(words)
        # Bigrams
        for i in range(n - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 not in self._stopwords and w2 not in self._stopwords:
                if not w1.isdigit() and not w2.isdigit():
                    phrases.append(f"{w1} {w2}")

        # Trigrams
        for i in range(n - 2):
            w1, w2, w3 = words[i], words[i + 1], words[i + 2]
            # Trigram where start and end are non-stopwords
            if w1 not in self._stopwords and w3 not in self._stopwords:
                if not w1.isdigit() and not w3.isdigit():
                    phrases.append(f"{w1} {w2} {w3}")

        return phrases

    def extract_post_topics(self, post: AnalyticsReadyPost) -> SinglePostTopicResult:
        """
        Extracts key terms, phrases, and suggested topic label for a single post.
        """
        words, hashtags = self._extract_tokens_and_hashtags(post.text)
        unigrams = self._get_meaningful_unigrams(words)
        phrases = self._get_phrases(words)

        # Count frequencies
        unigram_counts = Counter(unigrams)
        phrase_counts = Counter(phrases)
        hashtag_counts = Counter(hashtags)

        # Ranked keywords (combines unigrams and hashtags)
        ranked_keywords = [item[0] for item in unigram_counts.most_common(10)]
        for h, _ in hashtag_counts.most_common(5):
            if h not in ranked_keywords:
                ranked_keywords.append(h)

        ranked_phrases = [item[0] for item in phrase_counts.most_common(5)]

        # Determine suggested label
        suggested_label = None
        if ranked_phrases:
            suggested_label = ranked_phrases[0].title()
        elif ranked_keywords:
            suggested_label = ranked_keywords[0].title()

        return SinglePostTopicResult(
            post_id=post.id,
            external_post_id=post.external_post_id,
            keywords=ranked_keywords[:8],
            keyphrases=ranked_phrases[:5],
            hashtags=hashtags,
            suggested_label=suggested_label,
        )

    def extract_batch_topics(self, posts: List[AnalyticsReadyPost]) -> List[ExtractedTopic]:
        """
        Clusters a collection of posts into coherent topic groups using token overlap
        and connected component analysis.
        """
        if not posts:
            return []

        # 1. Extract feature sets for each post
        post_features: List[Dict[str, Any]] = []
        for p in posts:
            words, hashtags = self._extract_tokens_and_hashtags(p.text)
            unigrams = self._get_meaningful_unigrams(words)
            phrases = self._get_phrases(words)

            feature_set = set(unigrams).union(phrases).union(hashtags)
            post_features.append({
                "post": p,
                "unigrams": unigrams,
                "phrases": phrases,
                "hashtags": hashtags,
                "terms": feature_set,
            })

        n = len(post_features)

        # 2. Union-Find Disjoint Set for connected components
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_j] = root_i

        for i in range(n):
            for j in range(i + 1, n):
                feat_i = post_features[i]
                feat_j = post_features[j]

                terms_i = feat_i["terms"]
                terms_j = feat_j["terms"]

                if not terms_i or not terms_j:
                    continue

                intersection = len(terms_i.intersection(terms_j))
                union_len = len(terms_i.union(terms_j))
                sim = (intersection / union_len) if union_len > 0 else 0.0

                # Check for shared multi-word phrase
                shared_phrases = set(feat_i["phrases"]).intersection(feat_j["phrases"])
                # Check for shared hashtags
                shared_hashtags = set(feat_i["hashtags"]).intersection(feat_j["hashtags"])
                # Check for shared meaningful unigrams
                shared_unigrams = set(feat_i["unigrams"]).intersection(feat_j["unigrams"])

                if (
                    sim >= self._min_similarity
                    or shared_phrases
                    or shared_hashtags
                    or (len(shared_unigrams) >= 2)
                    or (len(shared_unigrams) == 1 and (len(terms_i) <= 2 or len(terms_j) <= 2))
                ):
                    union(i, j)

        # 3. Group features into clusters by root
        cluster_groups: Dict[int, List[Dict[str, Any]]] = {}
        for i in range(n):
            root = find(i)
            if root not in cluster_groups:
                cluster_groups[root] = []
            cluster_groups[root].append(post_features[i])

        # 4. Build ExtractedTopic objects from clusters
        extracted_topics: List[ExtractedTopic] = []

        for cluster in cluster_groups.values():
            all_unigrams: List[str] = []
            all_phrases: List[str] = []
            all_hashtags: List[str] = []
            member_post_ids: List[int] = []
            member_ext_ids: List[str] = []

            for member in cluster:
                post = member["post"]
                if post.id is not None:
                    member_post_ids.append(post.id)
                if post.external_post_id:
                    member_ext_ids.append(post.external_post_id)

                all_unigrams.extend(member["unigrams"])
                all_phrases.extend(member["phrases"])
                all_hashtags.extend(member["hashtags"])

            if not all_unigrams and not all_phrases and not all_hashtags:
                continue

            phrase_counts = Counter(all_phrases)
            unigram_counts = Counter(all_unigrams)
            hashtag_counts = Counter(all_hashtags)

            # Determine dominant label
            if phrase_counts:
                dominant_label = phrase_counts.most_common(1)[0][0].title()
            elif hashtag_counts:
                dominant_label = f"#{hashtag_counts.most_common(1)[0][0]}"
            elif unigram_counts:
                top_words = [w.title() for w, _ in unigram_counts.most_common(2)]
                dominant_label = " ".join(top_words)
            else:
                dominant_label = "General Topic"

            # Ranked keywords
            top_keywords = [w for w, _ in unigram_counts.most_common(8)]
            for h, _ in hashtag_counts.most_common(4):
                if h not in top_keywords:
                    top_keywords.append(h)

            top_phrases = [p for p, _ in phrase_counts.most_common(5)]

            # Deterministic topic ID
            clean_id_slug = re.sub(r"[^a-z0-9]+", "_", dominant_label.lower()).strip("_")
            topic_id = f"topic_{clean_id_slug}" if clean_id_slug else "topic_general"

            # Cohesion confidence score
            confidence = min(1.0, 0.5 + (len(cluster) * 0.1))

            extracted_topics.append(
                ExtractedTopic(
                    topic_id=topic_id,
                    label=dominant_label,
                    keywords=top_keywords,
                    keyphrases=top_phrases,
                    post_count=len(cluster),
                    post_ids=member_post_ids,
                    external_post_ids=member_ext_ids,
                    confidence=round(confidence, 4),
                )
            )

        # Sort topics by post volume descending
        extracted_topics.sort(key=lambda t: t.post_count, reverse=True)

        return extracted_topics
