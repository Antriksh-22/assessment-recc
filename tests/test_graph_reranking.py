import asyncio

from app.analyzer import analyze
from app.agent import RecommenderAgent
from app.config import Settings
from app.graph_index import build_graph
from app.reranker import rerank
from app.retriever import RetrievedItem
from app.schemas import ChatRequest, Message


def _settings(enable_kg=True):
    settings = Settings()
    settings.enable_kg = enable_kg
    return settings


def test_drop_rest_excludes_restful_web_services_with_kg_enabled():
    agent = RecommenderAgent(_settings(enable_kg=True))
    response = asyncio.run(
        agent.chat(
            ChatRequest(
                messages=[
                    Message(
                        role="user",
                        content="Senior IC backend engineer. Core Java and Spring are day-one priorities; SQL is constant. Add AWS and Docker. Drop REST.",
                    )
                ]
            )
        )
    )
    names = [item.name for item in response.recommendations]
    assert "Amazon Web Services (AWS) Development (New)" in names
    assert "Docker (New)" in names
    assert "RESTful Web Services (New)" not in names


def test_reranker_graph_boost_does_not_rescue_removed_rest():
    agent = RecommenderAgent(_settings(enable_kg=True))
    ctx = analyze([Message(role="user", content="Backend Java role with Spring and SQL. Drop REST.")])
    graph = build_graph(agent.catalog.items)
    rest = agent.catalog.find("RESTful Web Services (New)")
    java = agent.catalog.find("Core Java (Advanced Level) (New)")
    retrieved = [
        RetrievedItem(item=rest, semantic_score=1.0, keyword_score=1.0, fuzzy_score=1.0),
        RetrievedItem(item=java, semantic_score=0.5, keyword_score=0.5, fuzzy_score=0.5),
    ]
    names = [item.name for item in rerank(ctx, retrieved, top_k=2, graph=graph)]
    assert names.index("RESTful Web Services (New)") > names.index("Core Java (Advanced Level) (New)")
    assert graph.graph_boost(rest, ctx) == 0.0


def test_enable_kg_false_existing_behavior_still_works():
    agent = RecommenderAgent(_settings(enable_kg=False))
    assert agent.graph is None
    response = asyncio.run(
        agent.chat(
            ChatRequest(messages=[Message(role="user", content="Hiring graduate financial analysts with numerical reasoning and finance knowledge.")])
        )
    )
    names = [item.name for item in response.recommendations]
    assert "Financial Accounting (New)" in names
    assert "Basic Statistics (New)" in names


def test_graph_build_failure_falls_back_safely(monkeypatch):
    import app.agent as agent_module

    def broken_build_graph(_items):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent_module, "build_graph", broken_build_graph)
    agent = agent_module.RecommenderAgent(_settings(enable_kg=True))
    assert agent.graph is None
    response = asyncio.run(
        agent.chat(
            ChatRequest(messages=[Message(role="user", content="Hiring graduate financial analysts with numerical reasoning and finance knowledge.")])
        )
    )
    assert response.reply
    assert response.recommendations
