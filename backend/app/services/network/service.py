"""
Phase 5.3 — Network & Link Analysis Service.

Computes graph interactions, node degrees, influence rankings, hashtag co-occurrence,
and external domain sharing across social media posts.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urlparse

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.network import (
    BatchNetworkResult,
    NetworkEdge,
    NetworkNode,
)


class NetworkAnalysisService:
    """Service for computing network graph structure, node degrees, domain sharing, and author influence."""

    def analyze_batch(self, posts: List[AnalyticsReadyPost]) -> BatchNetworkResult:
        if not posts:
            return BatchNetworkResult(
                total_nodes=0,
                total_edges=0,
                nodes=[],
                edges=[],
                top_influencers=[],
                top_domains=[],
                analyzed_at=datetime.now(timezone.utc),
            )

        nodes_map: Dict[str, Dict[str, Any]] = {}
        edges_map: Dict[Tuple[str, str, str], int] = {}
        domain_counts: Dict[str, int] = {}

        def add_node(node_id: str, label: str, node_type: str, bonus_score: float = 0.0):
            if node_id not in nodes_map:
                nodes_map[node_id] = {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "degree": 0,
                    "raw_score": bonus_score,
                }
            else:
                nodes_map[node_id]["raw_score"] += bonus_score

        def add_edge(src: str, tgt: str, rel: str):
            if src == tgt:
                return
            key = (src, tgt, rel)
            edges_map[key] = edges_map.get(key, 0) + 1

        mention_regex = re.compile(r"@([a-zA-Z0-9_]+)")
        hashtag_regex = re.compile(r"#([a-zA-Z0-9_]+)")
        url_regex = re.compile(r"https?://[^\s]+")

        for post in posts:
            raw_author = (post.author_username or "anonymous").strip()
            author_clean = raw_author.lstrip("@").lower()
            author_id = f"author:{author_clean}"

            likes = post.metrics.likes if post.metrics else 0
            shares = post.metrics.shares if post.metrics else 0
            comments = post.metrics.comments if post.metrics else 0
            post_engagement = likes * 1.0 + comments * 2.0 + shares * 3.0

            add_node(
                author_id,
                f"@{author_clean}",
                "author",
                bonus_score=1.0 + post_engagement * 0.01,
            )

            plat = post.platform
            if plat:
                plat_id = f"platform:{plat.lower()}"
                add_node(plat_id, plat, "platform")
                add_edge(author_id, plat_id, "posts_on")

            text = post.text or ""

            # Extract mentions (@username)
            mentions = set(mention_regex.findall(text))
            for m in mentions:
                m_clean = m.strip().lower()
                m_id = f"author:{m_clean}"
                add_node(m_id, f"@{m_clean}", "author", bonus_score=0.5)
                add_edge(author_id, m_id, "author_mention")

            # Extract hashtags (#hashtag)
            hashtags = set(hashtag_regex.findall(text))
            for h in hashtags:
                h_clean = h.strip().lower()
                h_id = f"hashtag:{h_clean}"
                add_node(h_id, f"#{h_clean}", "hashtag")
                add_edge(author_id, h_id, "uses_hashtag")

            # Extract URLs and Domains
            urls = set(url_regex.findall(text))
            if post.url:
                urls.add(post.url)
            for u in urls:
                try:
                    parsed = urlparse(u)
                    domain = parsed.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                        d_id = f"domain:{domain}"
                        add_node(d_id, domain, "domain")
                        add_edge(author_id, d_id, "posts_domain")
                except Exception:
                    pass

        # Compute degrees from edges
        for (src, tgt, rel), w in edges_map.items():
            if src in nodes_map:
                nodes_map[src]["degree"] += w
            if tgt in nodes_map:
                nodes_map[tgt]["degree"] += w

        nodes_list: List[NetworkNode] = []
        for n_id, n_data in nodes_map.items():
            inf_score = round(n_data["raw_score"] + n_data["degree"] * 0.5, 2)
            nodes_list.append(
                NetworkNode(
                    id=n_data["id"],
                    label=n_data["label"],
                    node_type=n_data["type"],
                    degree=n_data["degree"],
                    influence_score=inf_score,
                )
            )

        edges_list: List[NetworkEdge] = []
        for (src, tgt, rel), w in edges_map.items():
            edges_list.append(
                NetworkEdge(
                    source=src,
                    target=tgt,
                    weight=w,
                    relation_type=rel,
                )
            )

        top_influencers = sorted(nodes_list, key=lambda x: x.influence_score, reverse=True)[:10]

        top_domains = [
            {"domain": dom, "share_count": count}
            for dom, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return BatchNetworkResult(
            total_nodes=len(nodes_list),
            total_edges=len(edges_list),
            nodes=nodes_list,
            edges=edges_list,
            top_influencers=top_influencers,
            top_domains=top_domains,
            analyzed_at=datetime.now(timezone.utc),
        )


def get_network_analyzer() -> NetworkAnalysisService:
    return NetworkAnalysisService()
