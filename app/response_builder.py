from typing import Iterable, List

from .catalog import Catalog, CatalogItem
from .schemas import ChatResponse, Recommendation


def build_response(
    catalog: Catalog,
    reply: str,
    items: Iterable[CatalogItem] | None = None,
    end: bool = False,
) -> ChatResponse:
    valid = catalog.validate_items(items or [])
    recs: List[Recommendation] = [
        Recommendation(name=item.name, url=item.url, test_type=item.test_type)
        for item in valid[:10]
    ]
    return ChatResponse(reply=reply.strip() or "Here is the best catalog-only shortlist.", recommendations=recs, end_of_conversation=bool(end))


def catalog_snippets(items: Iterable[CatalogItem]) -> str:
    lines = []
    for item in items:
        lines.append(
            f"- {item.name}: type={item.test_type}; keys={', '.join(item.keys)}; "
            f"duration={item.duration or 'N/A'}; languages={', '.join(item.languages) or 'N/A'}"
        )
    return "\n".join(lines)

