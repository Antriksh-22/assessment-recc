import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent import RecommenderAgent
from app.config import get_settings
from app.schemas import ChatRequest, Message


FINAL_PROMPTS = {
    "C1": "Selection - comparing candidates against a leadership benchmark.",
    "C2": "Yes, go ahead. Should I also add a cognitive test for this level?",
    "C3": "English US contact center agents, inbound customer service. Confirm final stack.",
    "C4": "Hiring graduate financial analysts. Need numerical reasoning, finance knowledge, statistics, and graduate SJT.",
    "C5": "Sales organization talent audit and reskilling. Keep GSA, development report, OPQ, OPQ MQ Sales Report, and Sales Transformation.",
    "C6": "Industrial chemical plant operators. Safety and dependability are top priority. Confirm the industrial shortlist.",
    "C7": "Bilingual healthcare admin staff, South Texas, Spanish support, functionally bilingual. Use the hybrid HIPAA/admin shortlist.",
    "C8": "Admin assistants need Excel and Word daily, and we are OK adding simulations to capture capability.",
    "C9": "Senior IC backend engineer: Core Java, Spring, SQL. Add AWS and Docker. Drop REST. Keep Verify G+.",
    "C10": "Graduate management trainee final list: Verify G+ and Graduate Scenarios. Drop OPQ.",
}


async def main():
    agent = RecommenderAgent(get_settings())
    expected = json.loads((ROOT / "eval" / "expected_shortlists.json").read_text())
    total = 0
    passed = 0
    recalls = {}
    for trace_id, prompt in FINAL_PROMPTS.items():
        req = ChatRequest(messages=[Message(role="user", content=prompt)])
        resp = await agent.chat(req)
        total += 1
        names = [r.name for r in resp.recommendations]
        urls_ok = all(r.url in agent.catalog.valid_urls for r in resp.recommendations)
        schema_ok = isinstance(resp.reply, str) and isinstance(resp.end_of_conversation, bool) and len(resp.recommendations) <= 10
        exp = set(expected[trace_id])
        recall = len(exp.intersection(names)) / len(exp)
        recalls[trace_id] = recall
        ok = urls_ok and schema_ok and recall >= 0.6
        passed += int(ok)
        print(f"{trace_id}: {'PASS' if ok else 'FAIL'} recall@10={recall:.2f} names={names}")
    mean_recall = sum(recalls.values()) / len(recalls)
    print(f"total tests: {total}")
    print(f"pass/fail: {passed}/{total - passed}")
    print(f"mean Recall@10: {mean_recall:.2f}")


if __name__ == "__main__":
    asyncio.run(main())

