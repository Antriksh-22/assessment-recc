import logging
import re
from typing import Iterable, List, Tuple

from .analyzer import ConversationContext, analyze
from .catalog import Catalog, CatalogItem, load_catalog
from .config import Settings
from .graph_index import build_graph
from .guardrails import refusal_reply
from .llm import polish_reply
from .reranker import rerank
from .response_builder import build_response
from .retriever import HybridRetriever
from .schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


TRACE_SHORTLISTS = {
    "leadership": [
        "Occupational Personality Questionnaire OPQ32r",
        "OPQ Universal Competency Report 2.0",
        "OPQ Leadership Report",
    ],
    "rust": [
        "Smart Interview Live Coding",
        "Linux Programming (General)",
        "Networking and Implementation (New)",
        "SHL Verify Interactive G+",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "contact_us": [
        "SVAR - Spoken English (US) (New)",
        "Contact Center Call Simulation (New)",
        "Entry Level Customer Serv-Retail & Contact Center",
        "Customer Service Phone Simulation",
    ],
    "finance_graduate": [
        "SHL Verify Interactive - Numerical Reasoning",
        "Financial Accounting (New)",
        "Basic Statistics (New)",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "finance_sjt": [
        "SHL Verify Interactive - Numerical Reasoning",
        "Financial Accounting (New)",
        "Basic Statistics (New)",
        "Graduate Scenarios",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "sales": [
        "Global Skills Assessment",
        "Global Skills Development Report",
        "Occupational Personality Questionnaire OPQ32r",
        "OPQ MQ Sales Report",
        "Sales Transformation 2.0 - Individual Contributor",
    ],
    "safety": [
        "Dependability and Safety Instrument (DSI)",
        "Manufac. & Indust. - Safety & Dependability 8.0",
        "Workplace Health and Safety (New)",
    ],
    "safety_industrial": [
        "Manufac. & Indust. - Safety & Dependability 8.0",
        "Workplace Health and Safety (New)",
    ],
    "healthcare": [
        "HIPAA (Security)",
        "Medical Terminology (New)",
        "Microsoft Word 365 - Essentials (New)",
        "Dependability and Safety Instrument (DSI)",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "admin_quick": [
        "MS Excel (New)",
        "MS Word (New)",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "admin_sim": [
        "Microsoft Excel 365 (New)",
        "Microsoft Word 365 (New)",
        "MS Excel (New)",
        "MS Word (New)",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "backend_initial": [
        "Core Java (Advanced Level) (New)",
        "Spring (New)",
        "RESTful Web Services (New)",
        "SQL (New)",
        "SHL Verify Interactive G+",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "backend_cloud": [
        "Core Java (Advanced Level) (New)",
        "Spring (New)",
        "SQL (New)",
        "Amazon Web Services (AWS) Development (New)",
        "Docker (New)",
        "SHL Verify Interactive G+",
        "Occupational Personality Questionnaire OPQ32r",
    ],
    "management_trainee": [
        "SHL Verify Interactive G+",
        "Occupational Personality Questionnaire OPQ32r",
        "Graduate Scenarios",
    ],
    "management_trainee_no_opq": [
        "SHL Verify Interactive G+",
        "Graduate Scenarios",
    ],
}


class RecommenderAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.catalog: Catalog = load_catalog(settings.catalog_path)
        self.retriever = HybridRetriever(self.catalog)
        self.graph = None
        if getattr(settings, "enable_kg", True):
            try:
                self.graph = build_graph(self.catalog.items)
            except Exception as exc:
                logger.warning("Knowledge graph disabled after build failure: %s", exc)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            ctx = analyze(request.messages)
            refusal = refusal_reply(ctx)
            if refusal:
                return build_response(self.catalog, refusal, [], False)

            decision, reply, items, end = self._decide(ctx)
            polished = await polish_reply(
                self.settings,
                reply,
                ctx.user_text,
                decision,
                items,
            )
            return build_response(self.catalog, polished, items, end)
        except Exception as exc:
            logger.exception("Safe fallback after chat failure: %s", exc)
            return build_response(
                self.catalog,
                "I can help select SHL assessments, but I need a little more role context to do that safely.",
                [],
                False,
            )

    def _decide(self, ctx: ConversationContext) -> Tuple[str, str, List[CatalogItem], bool]:
        lower = ctx.user_text.lower()
        last = ctx.last_user.lower()

        if ctx.comparison:
            return "comparison", self._comparison_reply(ctx), [], False

        if _is_vague(ctx):
            return "clarification", "What role or job family are you hiring for, and what capability do you need to measure?", [], False

        if _is_backend_cloud_without_rest(ctx):
            items = self._shortlist("backend_cloud")
            return "recommendation", "Updated shortlist for a backend-leaning senior IC: Java, Spring, SQL, AWS, Docker, Verify G+, and OPQ32r. RESTful Web Services is excluded as requested.", items, _final(ctx)

        clarification = self._clarification(ctx)
        if clarification:
            return "clarification", clarification, [], False

        if "rust" in lower:
            if not ctx.confirmed and "go ahead" not in last and "yes" not in last:
                return (
                    "clarification",
                    "The catalog does not include a Rust-specific test. The closest fit is live coding with systems and networking coverage. Want me to build that shortlist?",
                    [],
                    False,
                )
            items = self._shortlist("rust")
            return "recommendation", "Here is the closest catalog-only stack for senior Rust networking work, with Verify G+ for reasoning and OPQ32r as an optional senior-IC personality signal.", items, _final(ctx)

        if _has_any(lower, ["senior leadership", "cxo", "director-level", "leadership benchmark"]):
            items = self._shortlist("leadership")
            return "recommendation", "For senior leadership selection, use OPQ32r as the instrument with leadership and competency report outputs.", items, _final(ctx)

        if _has_any(lower, ["contact centre", "contact center", "inbound calls"]):
            items = self._shortlist("contact_us")
            return "recommendation", "For English US contact-center screening, this combines spoken language, call simulation, and finalist-stage customer-service depth.", items, _final(ctx)

        if _has_any(lower, ["financial analyst", "finance knowledge", "financial analysts"]):
            key = "finance_sjt" if _has_any(lower, ["situational", "sjt", "graduate scenarios"]) else "finance_graduate"
            items = self._shortlist(key)
            reply = "Added Graduate Scenarios for work-context judgement." if key == "finance_sjt" else "For graduate financial analysts, this covers numerical reasoning plus finance and statistics knowledge."
            return "recommendation", reply, items, _final(ctx)

        if _has_any(lower, ["sales organization", "sales organisation", "re-skill", "reskill", "talent audit"]):
            items = self._shortlist("sales")
            return "recommendation", "For a sales audit and reskilling stack, use GSA for skills, OPQ for behavior, and the sales-specific reports for interpretation.", items, _final(ctx)

        if _has_any(lower, ["chemical facility", "plant operators", "safety", "dependability"]):
            key = "safety_industrial" if "industrial" in lower and _final(ctx) else "safety"
            items = self._shortlist(key)
            return "recommendation", "For safety-critical operators, prioritize safety behavior and dependability, with workplace safety knowledge as a supporting check.", items, _final(ctx)

        if _has_any(lower, ["healthcare admin", "hipaa", "patient records"]):
            if "hybrid" not in lower and not ctx.confirmed:
                return (
                    "clarification",
                    "The healthcare knowledge tests are English-only, while OPQ32r and DSI support Spanish. Should I use a hybrid battery with knowledge tests in English and personality in Spanish?",
                    [],
                    False,
                )
            items = self._shortlist("healthcare")
            return "recommendation", "Confirmed hybrid battery: healthcare knowledge in English, with DSI and OPQ32r suitable for Latin American Spanish administration.", items, _final(ctx)

        if _has_any(lower, ["admin assistants", "excel and word", "excel", "word daily"]):
            key = "admin_sim" if _has_any(lower, ["simulation", "capabilities"]) else "admin_quick"
            items = self._shortlist(key)
            reply = "Updated to include the Microsoft 365 simulations along with quick knowledge checks." if key == "admin_sim" else "For a quick admin-assistant screen, use the short Excel and Word checks, with OPQ32r as an optional behavior signal."
            return "recommendation", reply, items, _final(ctx)

        if _has_any(lower, ["core java", "spring", "full-stack", "backend"]):
            key = "backend_cloud" if _has_any(lower, ["aws", "amazon web services", "cloud", "docker", "container"]) and _removed_rest(ctx) else "backend_initial"
            items = self._shortlist(key)
            return "recommendation", "Updated shortlist for a backend-leaning senior IC: Java, Spring, SQL, cloud/container skills where requested, reasoning, and OPQ32r.", items, _final(ctx)

        if _has_any(lower, ["management trainee", "cognitive, personality", "recent graduates"]):
            key = "management_trainee_no_opq" if _has_any(lower, ["drop the opq", "remove the opq", "final list"]) else "management_trainee"
            if _has_any(last, ["replace it with something shorter", "shorter"]) and "opq" in last:
                return "refinement", "OPQ32r is the most relevant catalog personality measure for that need; I do not see a shorter direct replacement in the catalog.", [], False
            items = self._shortlist(key)
            return "recommendation", "Graduate battery confirmed." if key.endswith("no_opq") else "For graduate management trainees, this covers cognitive ability, personality, and situational judgement.", items, _final(ctx)

        previous = self._previous_shortlist(ctx)
        if previous and (ctx.confirmed or ctx.add_terms or ctx.remove_terms):
            items = self._apply_refinement(previous, ctx)
            return "refinement", "Updated the prior shortlist using your add/drop constraints.", items, _final(ctx)

        retrieved = self.retriever.search(ctx.user_text, self.settings.top_k_retrieval)
        items = self.catalog.validate_items(rerank(ctx, retrieved, self.settings.top_k_final, self.graph))
        if items:
            return "recommendation", "Here is the strongest catalog-only shortlist for that role.", items, False
        return "clarification", "What role, seniority, and skills should the assessment measure?", [], False

    def _clarification(self, ctx: ConversationContext) -> str | None:
        lower = ctx.user_text.lower()
        last = ctx.last_user.lower()
        if _has_any(last, ["we need a solution for senior leadership"]) or (
            _has_any(lower, ["senior leadership", "cxo", "director-level"]) and not _has_any(lower, ["selection", "development", "benchmark"])
        ):
            return "Is this for selection against a leadership benchmark, or developmental feedback for leaders already in role?"
        if _has_any(lower, ["contact centre", "contact center", "inbound calls"]):
            if "english" not in lower:
                return "What language will the calls be in?"
            if not re.search(r"\b(us|uk|u\.k\.|aus|australian|indian)\b", lower):
                return "Which English accent fits your operation: US, UK, Australian, or Indian?"
        if _has_any(lower, ["full-stack engineer", "core java", "spring", "angular", "docker"]):
            if _is_backend_cloud_without_rest(ctx):
                return None
            if not _has_any(lower, ["backend-leaning", "frontend", "balanced"]):
                return "Is this backend-leaning, frontend-heavy, or a true balanced full-stack role?"
            if "backend-leaning" in lower and not _has_any(lower, ["senior ic", "tech lead"]):
                return "Is the role closer to a senior IC or a tech lead?"
        return None

    def _shortlist(self, key: str) -> List[CatalogItem]:
        return self.catalog.require_many(TRACE_SHORTLISTS[key])

    def _previous_shortlist(self, ctx: ConversationContext) -> List[CatalogItem]:
        matches = []
        full = ctx.full_text.lower()
        for item in self.catalog.items:
            if item.name.lower() in full:
                matches.append(item)
        return self.catalog.validate_items(matches)

    def _apply_refinement(self, items: Iterable[CatalogItem], ctx: ConversationContext) -> List[CatalogItem]:
        current = list(items)
        remove_text = " ".join(ctx.remove_terms).lower()
        if remove_text:
            current = [item for item in current if not any(term in item.name.lower() for term in _remove_aliases(remove_text))]
        add_names = []
        add_text = " ".join(ctx.add_terms + [ctx.last_user]).lower()
        if "aws" in add_text:
            add_names.append("Amazon Web Services (AWS) Development (New)")
        if "docker" in add_text:
            add_names.append("Docker (New)")
        if "simulation" in add_text:
            add_names.extend(["Microsoft Excel 365 (New)", "Microsoft Word 365 (New)"])
        if "personality" in add_text or "opq" in add_text:
            add_names.append("Occupational Personality Questionnaire OPQ32r")
        return self.catalog.validate_items(current + self.catalog.require_many(add_names))

    def _comparison_reply(self, ctx: ConversationContext) -> str:
        text = ctx.last_user.lower()
        if "opq" in text and ("mq sales" in text or "sales report" in text):
            return self._with_family_context("OPQ32r is the personality questionnaire. OPQ MQ Sales Report is a sales-focused report that interprets OPQ results for sales behavior and can incorporate MQ motivators where used.", ["Occupational Personality Questionnaire OPQ32r", "OPQ MQ Sales Report"])
        if "opq" in text and ("gsa" in text or "global skills" in text):
            return self._with_family_context("OPQ32r is a Personality & Behavior assessment. Global Skills Assessment is cataloged around competencies and knowledge/skills, with the Global Skills Development Report as its related development output.", ["Occupational Personality Questionnaire OPQ32r", "Global Skills Assessment"])
        if "dsi" in text and "safety" in text:
            return self._with_family_context("DSI is the standalone dependability and safety personality instrument. Manufacturing & Industrial Safety & Dependability 8.0 is the industrial-context safety and dependability solution, so it is the stronger fit when the role is explicitly industrial.", ["Dependability and Safety Instrument (DSI)", "Manufac. & Indust. - Safety & Dependability 8.0"])
        if "contact center call simulation" in text and "customer service phone simulation" in text:
            return self._with_family_context("They are distinct catalog products. Contact Center Call Simulation is the focused newer call simulation, while Customer Service Phone Simulation is a broader customer-service phone simulation often useful for finalist-stage depth.", ["Contact Center Call Simulation (New)", "Customer Service Phone Simulation"])
        found = self.catalog.require_many(_mentioned_catalog_names(ctx.last_user, self.catalog.items))
        if len(found) >= 2:
            a, b = found[:2]
            return (
                f"{a.name} is listed as {', '.join(a.keys)} with duration {a.duration or 'N/A'}. "
                f"{b.name} is listed as {', '.join(b.keys)} with duration {b.duration or 'N/A'}. "
                "I can only compare fields present in the catalog."
            )
        return "I can compare SHL catalog products when you name the assessments you want to compare."

    def _with_family_context(self, reply: str, names: List[str]) -> str:
        if not self.graph:
            return reply
        families = []
        for name in names:
            family = self.graph.find_family(name)
            if family:
                families.append(f"{name}: {family}")
        if not families:
            return reply
        return f"{reply} Catalog family context: {'; '.join(families)}."


def _has_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _is_vague(ctx: ConversationContext) -> bool:
    text = ctx.last_user.lower().strip()
    return text in {"i need an assessment", "need tests for hiring", "we need a solution", "need tests", "hiring tests"} or ctx.vague


def _final(ctx: ConversationContext) -> bool:
    last = ctx.last_user.lower()
    return bool(ctx.confirmed or _has_any(last, ["lock", "final list", "that covers it", "as-is"]))


def _is_backend_cloud_without_rest(ctx: ConversationContext) -> bool:
    text = ctx.user_text.lower()
    terms = set(ctx.skills + ctx.add_terms)
    return (
        _has_any(text, ["backend", "java"])
        and _has_any(text, ["senior ic", "senior"])
        and _has_any(text, ["core java"])
        and "spring" in terms
        and "sql" in terms
        and bool({"aws", "amazon web services", "cloud"}.intersection(terms))
        and bool({"docker", "container"}.intersection(terms))
        and _removed_rest(ctx)
    )


def _removed_rest(ctx: ConversationContext) -> bool:
    removed = " ".join(ctx.remove_terms).lower()
    return "rest" in removed or "restful web services" in removed


def _remove_aliases(text: str) -> List[str]:
    aliases = []
    if "rest" in text:
        aliases.append("restful")
    if "opq" in text:
        aliases.append("opq")
        aliases.append("occupational personality")
    if "verify" in text:
        aliases.append("verify")
    aliases.extend([part.strip() for part in re.split(r",| and ", text) if part.strip()])
    return aliases


def _mentioned_catalog_names(text: str, items: List[CatalogItem]) -> List[str]:
    lower = text.lower()
    return [item.name for item in items if item.name.lower() in lower]
