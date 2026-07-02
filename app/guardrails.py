from .analyzer import ConversationContext


def refusal_reply(ctx: ConversationContext) -> str | None:
    if ctx.prompt_injection:
        return "I can only recommend assessments from the provided SHL catalog and must follow the catalog-only selection rules."
    if ctx.legal_or_compliance:
        return (
            "I can help select SHL assessments, but I cannot interpret legal or regulatory obligations. "
            "Please involve your legal or compliance team for that decision."
        )
    if ctx.off_topic:
        return "I can help with SHL assessment selection, but that request is outside the assessment recommender scope."
    return None

