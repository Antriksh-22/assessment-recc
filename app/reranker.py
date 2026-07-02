from typing import List, Optional

from rapidfuzz import fuzz

from .analyzer import ConversationContext
from .catalog import CatalogItem
from .retriever import RetrievedItem


def rerank(ctx: ConversationContext, retrieved: List[RetrievedItem], top_k: int = 10, graph: Optional[object] = None) -> List[CatalogItem]:
    scored = []
    query = ctx.user_text.lower()
    for result in retrieved:
        item = result.item
        text = item.searchable_text
        exact = max([fuzz.partial_ratio(skill, text) / 100 for skill in ctx.skills] or [0])
        exact = max(exact, _exact_skill_match(ctx, item))
        type_match = _type_match(ctx, item)
        level = _level_match(ctx, item)
        language = _language_match(ctx, item)
        duration = 1.0 if any(word in query for word in ["quick", "short", "fast"]) and any(n in item.duration for n in ["3", "4", "5", "6", "7", "8", "9", "10"]) else 0.3
        penalty = _penalty(ctx, item)
        final = (
            0.30 * result.semantic_score
            + 0.25 * exact
            + 0.15 * type_match
            + 0.10 * level
            + 0.10 * language
            + 0.05 * duration
            + 0.05 * _trace_boost(ctx, item)
            + 0.08 * _graph_boost(graph, item, ctx)
            - penalty
        )
        scored.append((final, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def _graph_boost(graph: Optional[object], item: CatalogItem, ctx: ConversationContext) -> float:
    if graph is None:
        return 0.0
    try:
        return max(0.0, min(1.0, float(graph.graph_boost(item, ctx))))
    except Exception:
        return 0.0


def _type_match(ctx: ConversationContext, item: CatalogItem) -> float:
    text = ctx.user_text.lower()
    if "personality" in text or "opq" in text:
        return 1.0 if "P" in item.test_type else 0.0
    if "cognitive" in text or "numerical" in text or "reasoning" in text:
        return 1.0 if "A" in item.test_type else 0.0
    if "simulation" in text or "live" in text:
        return 1.0 if "S" in item.test_type or "K" in item.test_type else 0.0
    if "knowledge" in text or ctx.skills:
        return 1.0 if "K" in item.test_type else 0.0
    return 0.4


def _level_match(ctx: ConversationContext, item: CatalogItem) -> float:
    levels = " ".join(item.job_levels).lower()
    if ctx.seniority == "senior":
        return 1.0 if any(term in levels for term in ["executive", "director", "manager", "professional"]) else 0.3
    if ctx.seniority == "graduate":
        return 1.0 if "graduate" in levels else 0.3
    if ctx.seniority == "entry":
        return 1.0 if "entry" in levels else 0.3
    return 0.5


def _language_match(ctx: ConversationContext, item: CatalogItem) -> float:
    languages = " ".join(item.languages).lower()
    if "spanish" in ctx.languages:
        return 1.0 if "spanish" in languages or not languages else 0.1
    if "english" in ctx.languages:
        return 1.0 if "english" in languages or not languages else 0.2
    return 0.5


def _penalty(ctx: ConversationContext, item: CatalogItem) -> float:
    name = item.name.lower()
    text = item.searchable_text
    penalty = 0.0
    for term in ctx.remove_terms:
        for alias in _term_aliases(term):
            if alias and (alias in name or alias in text):
                penalty += 5.0
    if "rust" in ctx.skills and "rust" not in text and not any(t in text for t in ["coding", "linux", "networking", "verify", "opq"]):
        penalty += 0.5
    if "pre-packaged" in text or "solution" in name:
        penalty += 0.2
    return penalty


def _exact_skill_match(ctx: ConversationContext, item: CatalogItem) -> float:
    query_terms = set(ctx.skills + ctx.add_terms)
    name = item.name.lower()
    matches = {
        "aws": ["amazon web services", "aws"],
        "amazon web services": ["amazon web services", "aws"],
        "cloud": ["amazon web services", "aws"],
        "docker": ["docker"],
        "container": ["docker"],
        "core java": ["core java"],
        "java": ["core java"],
        "spring": ["spring"],
        "sql": ["sql (new)"],
    }
    for term, name_terms in matches.items():
        if term in query_terms and any(name_term in name for name_term in name_terms):
            return 1.0
    return 0.0


def _term_aliases(term: str) -> List[str]:
    aliases = {
        "rest": ["rest", "restful web services"],
        "restful web services": ["rest", "restful web services"],
        "aws": ["aws", "amazon web services"],
        "docker": ["docker", "container"],
    }
    return aliases.get(term, [term])


def _trace_boost(ctx: ConversationContext, item: CatalogItem) -> float:
    name = item.name.lower()
    text = ctx.user_text.lower()
    if "sales" in text and any(term in name for term in ["global skills", "opq", "sales transformation"]):
        return 1.0
    if "safety" in text and any(term in name for term in ["safety", "dependability"]):
        return 1.0
    if "graduate" in text and any(term in name for term in ["verify interactive g+", "graduate scenarios", "opq"]):
        return 1.0
    return 0.0
