from pathlib import Path

from app.catalog import load_catalog
from app.response_builder import build_response


def test_catalog_loads_and_validates_urls():
    catalog = load_catalog(Path("data/shl_catalog.json"))
    assert len(catalog.items) > 100
    item = catalog.find("OPQ32r")
    assert item is not None
    response = build_response(catalog, "ok", [item])
    assert response.recommendations[0].url in catalog.valid_urls

