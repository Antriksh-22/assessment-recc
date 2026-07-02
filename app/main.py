import logging

from fastapi import FastAPI

from .agent import RecommenderAgent
from .config import get_settings
from .schemas import ChatRequest, ChatResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SHL Assessment Recommender", version="1.0.0")
agent = RecommenderAgent(get_settings())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "name": "SHL Assessment Recommender",
        "version": "1.0.0",
        "health": "/health",
        "chat": "/chat",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await agent.chat(request)
