# Approach

## Problem Understanding

The task is to build a conversational SHL Assessment Recommender that always returns a strict JSON schema and recommends only products from the supplied SHL catalog. The service must handle vague inputs, clarification, recommendation, comparison, refinement, refusal, and final confirmation in a stateless API where every `/chat` call receives the full message history.

## Why Hybrid Retrieval Instead of Model Training

The catalog is the source of truth and the sample conversations are small behavioral examples, not enough data for model training. A hybrid retriever is more appropriate: BM25-style keyword matching catches exact skills and assessment names, fuzzy matching handles punctuation and naming variations, and semantic retrieval via `sentence-transformers/all-MiniLM-L6-v2` is attempted when locally available. If the semantic model or FAISS is unavailable, the service falls back to TF-IDF cosine similarity so deployment remains reliable.

## Catalog Processing

The loader supports both `link` and `url`, normalizes every item into a consistent internal schema, converts SHL key families into short type codes, and builds valid name and URL sets. All returned recommendations are validated against those sets before the response is built.

## Conversation Policy

The analyzer reconstructs context from the complete message list on each call. It extracts seniority, skills, language needs, add/drop constraints, comparison intent, confirmation, and guardrail signals. Clarification is used only when the request is too vague or when a known ambiguity materially changes the shortlist, such as contact-center accent or backend vs. frontend ownership.

## Retrieval and Reranking

The retriever returns up to `TOP_K_RETRIEVAL` candidates. The reranker combines semantic similarity, exact skill/name match, test type match, seniority match, language match, duration constraints, trace-rule boosts, and penalties for removed or conflicting terms. The LLM never chooses assessments.

The system also builds a lightweight in-memory catalog knowledge graph linking assessments to skills, test types, job levels, languages, and product families such as OPQ, GSA, Verify, SVAR, Microsoft Office, Safety, and Software Engineering. This graph is used only as a small reranking and explanation signal, avoiding the deployment risk of an external graph database.

## Guardrails

Deterministic guardrails refuse legal/compliance advice, prompt injection, and general hiring requests outside SHL assessment selection. Refusals still return the exact required schema with an empty recommendation list.

## Sarvam AI Usage

Sarvam AI is wrapped in `app/llm.py` and uses the required `api-subscription-key` request format. It only polishes the reply text from a grounded prompt containing the conversation summary, decision type, validated recommendations, and selected catalog snippets. If `USE_LLM=false`, the API key is missing, or the call fails, deterministic wording is returned.

## Evaluation Method

The local evaluator replays trace-inspired cases, checks schema compliance, validates every URL against the catalog, and computes Recall@10 against `eval/expected_shortlists.json`. Behavior tests cover vague queries, legal refusal, prompt-injection refusal, add/drop refinement, comparison, and catalog-only recommendation.

## What Did Not Work

Pure LLM recommendation logic was avoided because it can hallucinate product names or URLs. Strict JSON parsing of the pasted catalog also needed a tolerant loader because the source contains an embedded newline inside one product name. The loader handles this with `json.loads(..., strict=False)`.

## How Codex Was Used

I used Codex for scaffolding, refactoring, tests, and deployment setup. The architecture, ranking logic, catalog-only validation, and evaluation policy were explicitly specified and manually verified.
