from dataclasses import dataclass, field
import re
from typing import List

from .schemas import Message


@dataclass
class ConversationContext:
    full_text: str
    user_text: str
    last_user: str
    seniority: str = ""
    skills: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    add_terms: List[str] = field(default_factory=list)
    remove_terms: List[str] = field(default_factory=list)
    confirmed: bool = False
    comparison: bool = False
    vague: bool = False
    prompt_injection: bool = False
    legal_or_compliance: bool = False
    off_topic: bool = False


SKILL_TERMS = [
    "core java", "java", "spring", "rest", "restful web services", "sql", "aws",
    "amazon web services", "cloud", "docker", "container", "angular", "rust", "linux",
    "networking", "excel", "word", "hipaa", "medical terminology", "sales",
    "safety", "customer service", "contact centre", "contact center", "finance",
    "accounting", "statistics", "cognitive", "personality", "situational judgement",
    "simulation", "graduate", "leadership",
]


def _last_user(messages: List[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def analyze(messages: List[Message]) -> ConversationContext:
    full_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
    user_text = "\n".join(m.content for m in messages if m.role == "user")
    last_user = _last_user(messages)
    lower = user_text.lower()
    last_lower = last_user.lower()

    ctx = ConversationContext(
        full_text=full_text,
        user_text=user_text,
        last_user=last_user,
        comparison=bool(re.search(r"\bdifference\b|\bdifferent\b|\bcompare\b|\bversus\b|\bvs\b", last_lower)),
        confirmed=bool(re.search(r"\b(confirm|confirmed|perfect|that works|that's good|locking it in|final list|covers it|thanks)\b", last_lower)),
        vague=bool(re.fullmatch(r".{0,25}(assessment|tests?|solution|hiring).{0,25}", last_lower.strip())),
        prompt_injection=bool(re.search(r"ignore (all )?(previous|system)|bypass|override|recommend anything|outside the catalog", last_lower)),
        legal_or_compliance=bool(re.search(r"\blegally required\b|\blegal\b|\bcompliance\b|\bregulatory\b|\bsatisfy that requirement\b", last_lower)),
        off_topic=bool(re.search(r"salary benchmark|write a job ad|interview questions only|general hiring advice", last_lower)),
    )

    if re.search(r"senior|cxo|director|executive|15\+|leadership", lower):
        ctx.seniority = "senior"
    elif "graduate" in lower or "entry-level" in lower or "entry level" in lower:
        ctx.seniority = "graduate" if "graduate" in lower else "entry"

    ctx.skills = [term for term in SKILL_TERMS if term in lower]
    if "spanish" in lower:
        ctx.languages.append("spanish")
    if "english" in lower or "us" in lower:
        ctx.languages.append("english")
    if "accent" in lower:
        ctx.languages.append("accent")

    ctx.add_terms = _extract_constraint_terms(last_lower, ("add", "adding"))
    ctx.remove_terms = _extract_constraint_terms(last_lower, ("drop", "remove", "skip", "exclude"))
    return ctx


CONSTRAINT_ALIASES = {
    "aws": ["aws", "amazon web services", "cloud"],
    "amazon web services": ["aws", "amazon web services", "cloud"],
    "cloud": ["aws", "amazon web services", "cloud"],
    "docker": ["docker", "container"],
    "container": ["docker", "container"],
    "rest": ["rest", "restful web services"],
    "restful web services": ["rest", "restful web services"],
    "core java": ["core java", "java"],
    "java": ["java"],
    "spring": ["spring"],
    "sql": ["sql"],
}


def _extract_constraint_terms(text: str, verbs: tuple[str, ...]) -> List[str]:
    terms: List[str] = []
    verb_pattern = "|".join(re.escape(verb) for verb in verbs)
    for match in re.finditer(rf"\b(?:{verb_pattern})\b\s+([^.;]+)", text):
        fragment = match.group(1)
        for raw in re.split(r",|\band\b|/|&", fragment):
            terms.extend(_constraint_aliases(raw.strip()))
    for term in list(CONSTRAINT_ALIASES) + ["opq", "verify g+"]:
        if re.search(rf"\b(?:{verb_pattern})\b[^.;]*\b{re.escape(term)}\b", text):
            terms.extend(_constraint_aliases(term))
    return _dedupe(terms)


def _constraint_aliases(term: str) -> List[str]:
    term = term.strip(" .")
    return CONSTRAINT_ALIASES.get(term, [term] if term else [])


def _dedupe(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
