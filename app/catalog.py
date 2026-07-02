from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Iterable, List, Optional

from rapidfuzz import fuzz, process


KEY_CODES = {
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
    "Assessment Exercises": "E",
}


@dataclass(frozen=True)
class CatalogItem:
    name: str
    url: str
    test_type: str
    keys: List[str]
    description: str
    duration: str
    job_levels: List[str]
    languages: List[str]
    remote: str
    adaptive: str

    @property
    def searchable_text(self) -> str:
        parts = [
            self.name,
            self.description,
            " ".join(self.keys),
            " ".join(self.job_levels),
            " ".join(self.languages),
            self.duration,
        ]
        return " ".join(p for p in parts if p).lower()


class Catalog:
    def __init__(self, items: List[CatalogItem]):
        self.items = items
        self.by_name = {item.name.lower(): item for item in items}
        self.by_url = {item.url: item for item in items}
        self.valid_names = {item.name for item in items}
        self.valid_urls = set(self.by_url)
        self._names = [item.name for item in items]

    def get(self, name: str) -> Optional[CatalogItem]:
        return self.by_name.get(name.lower())

    def find(self, name: str, score_cutoff: int = 70) -> Optional[CatalogItem]:
        direct = self.get(name)
        if direct:
            return direct
        result = process.extractOne(name, self._names, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
        if not result:
            return None
        return self.get(result[0])

    def require_many(self, names: Iterable[str]) -> List[CatalogItem]:
        found: List[CatalogItem] = []
        seen = set()
        for name in names:
            item = self.find(name)
            if item and item.url not in seen:
                found.append(item)
                seen.add(item.url)
        return found

    def validate_items(self, items: Iterable[CatalogItem]) -> List[CatalogItem]:
        valid: List[CatalogItem] = []
        seen = set()
        for item in items:
            if item.url in self.valid_urls and item.name in self.valid_names and item.url not in seen:
                valid.append(item)
                seen.add(item.url)
        return valid[:10]


def _as_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _clean_text(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _test_type(keys: List[str]) -> str:
    codes = [KEY_CODES[k] for k in keys if k in KEY_CODES]
    return ",".join(dict.fromkeys(codes)) or "K"


def load_catalog(path: Path) -> Catalog:
    text = path.read_text(encoding="utf-8-sig")
    raw_items = json.loads(text, strict=False)
    items: List[CatalogItem] = []
    for raw in raw_items:
        name = _clean_text(raw.get("name"))
        url = _clean_text(raw.get("url") or raw.get("link"))
        if not name or not url:
            continue
        keys = _as_list(raw.get("keys"))
        items.append(
            CatalogItem(
                name=name,
                url=url,
                test_type=_test_type(keys),
                keys=keys,
                description=_clean_text(raw.get("description")),
                duration=_clean_text(raw.get("duration") or raw.get("duration_raw")),
                job_levels=_as_list(raw.get("job_levels") or raw.get("job_levels_raw")),
                languages=_as_list(raw.get("languages") or raw.get("languages_raw")),
                remote=_clean_text(raw.get("remote")),
                adaptive=_clean_text(raw.get("adaptive")),
            )
        )
    return Catalog(items)

