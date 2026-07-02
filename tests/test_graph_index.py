from pathlib import Path

from app.analyzer import analyze
from app.catalog import load_catalog
from app.graph_index import build_graph
from app.schemas import Message


def _catalog_and_graph():
    catalog = load_catalog(Path("data/shl_catalog.json"))
    return catalog, build_graph(catalog.items)


def _ctx(text: str):
    return analyze([Message(role="user", content=text)])


def test_opq_family_links_opq32r_and_leadership_report():
    _, graph = _catalog_and_graph()
    assert graph.find_family("Occupational Personality Questionnaire OPQ32r") == "OPQ"
    assert graph.find_family("OPQ Leadership Report") == "OPQ"
    assert "OPQ Leadership Report" in graph.related_items("Occupational Personality Questionnaire OPQ32r")


def test_gsa_family_links_assessment_and_development_report():
    _, graph = _catalog_and_graph()
    assert graph.find_family("Global Skills Assessment") == "GSA"
    assert graph.find_family("Global Skills Development Report") == "GSA"
    assert "Global Skills Development Report" in graph.related_items("Global Skills Assessment")


def test_microsoft_office_family_links_knowledge_and_simulation_variants():
    _, graph = _catalog_and_graph()
    related = set(graph.related_items("MS Excel (New)"))
    assert graph.find_family("MS Excel (New)") == "Microsoft Office"
    assert "MS Word (New)" in related
    assert "Microsoft Excel 365 - Essentials (New)" in related
    assert "Microsoft Word 365 (New)" in related


def test_graph_boost_personality_request_boosts_personality_items():
    catalog, graph = _catalog_and_graph()
    ctx = _ctx("We want a personality and behavioral fit assessment.")
    opq = catalog.find("Occupational Personality Questionnaire OPQ32r")
    spring = catalog.find("Spring (New)")
    assert graph.graph_boost(opq, ctx) > graph.graph_boost(spring, ctx)


def test_graph_boost_backend_context_boosts_software_engineering_items():
    catalog, graph = _catalog_and_graph()
    ctx = _ctx("Senior backend engineer with Core Java, Spring, SQL, AWS, and Docker.")
    aws = catalog.find("Amazon Web Services (AWS) Development (New)")
    docker = catalog.find("Docker (New)")
    java = catalog.find("Core Java (Advanced Level) (New)")
    opq = catalog.find("Occupational Personality Questionnaire OPQ32r")
    assert graph.graph_boost(aws, ctx) > graph.graph_boost(opq, ctx)
    assert graph.graph_boost(docker, ctx) > graph.graph_boost(opq, ctx)
    assert graph.graph_boost(java, ctx) > graph.graph_boost(opq, ctx)
