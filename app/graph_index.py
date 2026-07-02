from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from .catalog import CatalogItem


TYPE_LABELS = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgment",
    "C": "Competencies",
    "D": "Development & 360",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
    "E": "Assessment Exercises",
}


FAMILY_RULES = {
    "OPQ": ["opq", "occupational personality questionnaire"],
    "GSA": ["global skills assessment", "global skills development report"],
    "Verify": ["verify"],
    "SVAR": ["svar", "spoken english"],
    "Contact Center / Customer Service": [
        "contact center",
        "contact centre",
        "customer service phone",
        "entry level customer serv",
        "retail & contact center",
    ],
    "Microsoft Office": [
        "ms excel",
        "ms word",
        "microsoft excel",
        "microsoft word",
    ],
    "Software Engineering": [
        "core java",
        "spring",
        "sql",
        "restful web services",
        "amazon web services",
        "aws",
        "docker",
        "angular",
        "linux programming",
        "networking and implementation",
        "smart interview live coding",
        "automata",
    ],
    "Safety": [
        "dependability and safety",
        "safety & dependability",
        "workplace health and safety",
    ],
    "Healthcare Admin": ["hipaa", "medical terminology", "microsoft word 365 - essentials"],
    "Sales": ["sales transformation", "opq mq sales report"],
}

FAMILY_INCLUDES = {
    "Healthcare Admin": [],
    "Sales": [],
}

SKILL_KEYWORDS = [
    "java",
    "core java",
    "spring",
    "sql",
    "rest",
    "restful",
    "aws",
    "amazon web services",
    "cloud",
    "docker",
    "container",
    "angular",
    "linux",
    "networking",
    "excel",
    "word",
    "hipaa",
    "medical terminology",
    "sales",
    "safety",
    "customer service",
    "contact center",
    "contact centre",
    "finance",
    "accounting",
    "statistics",
    "graduate",
    "leadership",
    "personality",
    "cognitive",
    "reasoning",
    "simulation",
    "live coding",
]


@dataclass
class CatalogGraph:
    assessments: Dict[str, CatalogItem]
    edges: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)
    families: Dict[str, str] = field(default_factory=dict)

    def graph_boost(self, item: CatalogItem, context) -> float:
        if _removed(item, context):
            return 0.0

        text = context.user_text.lower()
        score = 0.0
        type_codes = set(item.test_type.split(","))
        family = self.find_family(item.name)

        if _has_any(text, ["personality", "behavior", "behaviour", "fit", "opq"]) and "P" in type_codes:
            score += 0.30
        if _has_any(text, ["cognitive", "ability", "reasoning", "numerical", "deductive", "inductive"]) and "A" in type_codes:
            score += 0.30
        if _has_any(text, ["sjt", "scenario", "scenarios", "judgement", "judgment", "work-context"]) and "B" in type_codes:
            score += 0.30
        if _has_any(text, ["simulation", "hands-on", "live coding", "practical capability"]) and "S" in type_codes:
            score += 0.30
        if _has_any(text, ["skills", "knowledge", "tools", "domain knowledge"]) and "K" in type_codes:
            score += 0.25

        if _has_any(text, ["leadership", "cxo", "director", "executive", "senior leadership"]):
            score += _family_score(family, "OPQ", item.name, ["opq32r", "leadership report"])
        if _has_any(text, ["sales audit", "reskilling", "re-skilling", "talent audit", "sales organization", "sales organisation"]):
            score += 0.35 if family in {"Sales", "GSA"} or item.name in {"Occupational Personality Questionnaire OPQ32r", "OPQ MQ Sales Report"} else 0.0
        if _has_any(text, ["contact center", "contact centre", "call center", "customer service", "inbound calls"]):
            score += 0.35 if family in {"SVAR", "Contact Center / Customer Service"} else 0.0
        if _has_any(text, ["healthcare", "hipaa", "patient records", "medical admin"]):
            score += 0.35 if family == "Healthcare Admin" or item.name in {"Dependability and Safety Instrument (DSI)", "Occupational Personality Questionnaire OPQ32r", "Microsoft Word 365 - Essentials (New)"} else 0.0
        if _has_any(text, ["safety", "plant", "chemical", "industrial", "procedure compliance", "reliability"]):
            score += 0.35 if family == "Safety" else 0.0
        if _has_any(text, ["graduate", "final-year", "management trainee"]):
            score += 0.30 if item.name in {"SHL Verify Interactive G+", "Graduate Scenarios"} or "Graduate" in item.job_levels else 0.0
        if _has_any(text, ["java", "spring", "sql", "aws", "docker", "backend", "full-stack"]):
            score += 0.25 if family == "Software Engineering" else 0.0
            score += 0.30 * _exact_skill_overlap(item, context)
        if _has_any(text, ["spanish", "english", "accent", "language"]):
            score += 0.20 * _language_overlap(item, context)

        return max(0.0, min(1.0, score))

    def related_items(self, item_name: str) -> List[str]:
        family = self.find_family(item_name)
        related = set(self.edges.get(item_name, {}).get("RELATED_TO", set()))
        if family:
            related.update(name for name, fam in self.families.items() if fam == family and name != item_name)
        return sorted(related)

    def find_family(self, item_name: str) -> Optional[str]:
        return self.families.get(item_name)

    def explain_matches(self, item: CatalogItem, context) -> List[str]:
        reasons: List[str] = []
        text = context.user_text.lower()
        item_text = item.searchable_text
        for skill in sorted(set(getattr(context, "skills", []) + getattr(context, "add_terms", []))):
            if skill and skill in item_text:
                reasons.append(f"matches requested skill: {skill.title()}")
        for code in item.test_type.split(","):
            label = TYPE_LABELS.get(code)
            if label and _type_requested(label, text):
                reasons.append(f"matches test type: {label}")
        family = self.find_family(item.name)
        if family and family.lower() in text:
            reasons.append(f"matches product family: {family}")
        if context.seniority and any(context.seniority in level.lower() for level in item.job_levels):
            reasons.append(f"matches job level: {context.seniority.title()}")
        for language in item.languages:
            if language and language.lower().split()[0] in text:
                reasons.append(f"matches language: {language}")
                break
        return reasons[:5]


def build_graph(catalog_items: Iterable[CatalogItem]) -> CatalogGraph:
    items = list(catalog_items)
    graph = CatalogGraph(assessments={item.name: item for item in items})
    for item in items:
        graph.edges[item.name] = {
            "HAS_SKILL": _skills_for(item),
            "HAS_TYPE": set(item.test_type.split(",")),
            "SUITABLE_FOR": set(item.job_levels),
            "AVAILABLE_IN": set(item.languages),
            "IN_FAMILY": set(),
            "RELATED_TO": set(),
        }
        family = _detect_family(item)
        if family:
            graph.families[item.name] = family
            graph.edges[item.name]["IN_FAMILY"].add(family)

    for family in set(graph.families.values()):
        names = [name for name, fam in graph.families.items() if fam == family]
        for name in names:
            graph.edges[name]["RELATED_TO"].update(other for other in names if other != name)
    return graph


def _detect_family(item: CatalogItem) -> Optional[str]:
    haystack = f"{item.name} {item.description}".lower()
    for family, names in FAMILY_INCLUDES.items():
        if item.name in names:
            return family
    for family, markers in FAMILY_RULES.items():
        if any(marker in haystack for marker in markers):
            return family
    return None


def _skills_for(item: CatalogItem) -> Set[str]:
    text = item.searchable_text
    return {keyword for keyword in SKILL_KEYWORDS if keyword in text}


def _removed(item: CatalogItem, context) -> bool:
    text = item.searchable_text
    name = item.name.lower()
    for term in getattr(context, "remove_terms", []):
        for alias in _aliases(term):
            if alias and (alias in name or alias in text):
                return True
    return False


def _aliases(term: str) -> List[str]:
    aliases = {
        "rest": ["rest", "restful web services"],
        "restful web services": ["rest", "restful web services"],
        "aws": ["aws", "amazon web services"],
        "docker": ["docker", "container"],
        "opq": ["opq", "occupational personality"],
    }
    return aliases.get(term.lower(), [term.lower()])


def _has_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _family_score(family: Optional[str], wanted: str, item_name: str, priority_terms: List[str]) -> float:
    if family != wanted:
        return 0.0
    return 0.45 if any(term in item_name.lower() for term in priority_terms) else 0.30


def _exact_skill_overlap(item: CatalogItem, context) -> float:
    skills = set(getattr(context, "skills", []) + getattr(context, "add_terms", []))
    text = item.searchable_text
    matched = 0
    requested = 0
    for group in [
        {"java", "core java"},
        {"spring"},
        {"sql"},
        {"aws", "amazon web services", "cloud"},
        {"docker", "container"},
    ]:
        if skills.intersection(group):
            requested += 1
            if any(term in text for term in group):
                matched += 1
    if requested == 0:
        return 0.0
    return matched / requested


def _language_overlap(item: CatalogItem, context) -> float:
    text = " ".join(item.languages).lower()
    languages = getattr(context, "languages", [])
    if "spanish" in languages and "spanish" in text:
        return 1.0
    if "english" in languages and "english" in text:
        return 1.0
    return 0.0


def _type_requested(label: str, text: str) -> bool:
    label_lower = label.lower()
    if label_lower in text:
        return True
    return (
        ("personality" in text and label == "Personality & Behavior")
        or ("reasoning" in text and label == "Ability & Aptitude")
        or ("sjt" in text and label == "Biodata & Situational Judgment")
        or ("simulation" in text and label == "Simulations")
        or ("knowledge" in text and label == "Knowledge & Skills")
    )
