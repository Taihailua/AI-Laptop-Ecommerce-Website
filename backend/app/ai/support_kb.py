"""Knowledge base and retrieval utilities for CSKH chatbot."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

KB_FILE = os.path.join(os.path.dirname(__file__), "support_kb.json")
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "../../chroma_db")
SUPPORT_KB_COLLECTION = "support_kb_articles"

embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def _default_kb() -> dict[str, Any]:
    return {
        "version": "2026.03.30",
        "source": "TechShop CSKH policy baseline",
        "policy_notes": "Review and adjust policy values to match real shop operation.",
        "updated_at": None,
        "policies": {},
        "articles": [],
    }


def _normalize_kb_shape(data: Any) -> dict[str, Any]:
    base = _default_kb()

    # Backward compatibility for old format: list of entries only.
    if isinstance(data, list):
        base["articles"] = data
        return base

    if not isinstance(data, dict):
        return base

    base["version"] = str(data.get("version") or base["version"])
    base["source"] = str(data.get("source") or base["source"])
    base["policy_notes"] = str(data.get("policy_notes") or base["policy_notes"])
    base["updated_at"] = data.get("updated_at")

    policies = data.get("policies")
    if isinstance(policies, dict):
        base["policies"] = policies

    articles = data.get("articles")
    if isinstance(articles, list):
        base["articles"] = articles

    return base


def _normalize_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> set[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return set()
    return {t for t in normalized.split(" ") if len(t) > 1}


@lru_cache(maxsize=1)
def load_support_kb() -> dict[str, Any]:
    try:
        with open(KB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_kb_shape(data)
    except Exception:
        return _default_kb()


def save_support_kb(data: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_kb_shape(data)
    os.makedirs(os.path.dirname(KB_FILE), exist_ok=True)
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    load_support_kb.cache_clear()
    return normalized


def _get_articles(data: dict[str, Any]) -> list[dict[str, Any]]:
    articles = data.get("articles", [])
    if isinstance(articles, list):
        return [a for a in articles if isinstance(a, dict)]
    return []


def _build_article_text(entry: dict[str, Any], policies: dict[str, Any]) -> str:
    policy_lines = []
    for key, value in policies.items():
        if isinstance(value, dict):
            compact = ", ".join(f"{k}: {v}" for k, v in value.items())
            policy_lines.append(f"{key}: {compact}")

    guidance = entry.get("guidance", [])
    required_fields = ", ".join(entry.get("required_fields", []))
    intents = ", ".join(entry.get("intents", []))
    keywords = ", ".join(entry.get("keywords", []))
    handoff_when = ", ".join(entry.get("handoff_when", []))

    text_parts = [
        f"Title: {entry.get('title', '')}",
        f"Category: {entry.get('category', 'OTHER')}",
        f"Intents: {intents}",
        f"Keywords: {keywords}",
        "Guidance:",
        *[f"- {item}" for item in guidance],
        f"Required fields: {required_fields}",
        f"SLA target hours: {entry.get('sla_target_hours', '')}",
        f"Escalation rule: {entry.get('escalation_rule', '')}",
        f"Handoff when: {handoff_when}",
        f"Customer template: {entry.get('customer_message_template', '')}",
    ]

    if policy_lines:
        text_parts.append("Policy summary:")
        text_parts.extend(f"- {line}" for line in policy_lines)

    return "\n".join(str(p) for p in text_parts if p)


def create_support_kb_vector_store() -> Chroma:
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    return Chroma(
        collection_name=SUPPORT_KB_COLLECTION,
        embedding_function=embedding_function,
        persist_directory=CHROMA_DB_PATH,
    )


def rebuild_support_kb_index() -> int:
    data = load_support_kb()
    articles = _get_articles(data)
    policies = data.get("policies", {}) if isinstance(data.get("policies"), dict) else {}

    vector_store = create_support_kb_vector_store()
    try:
        vector_store.delete_collection()
    except Exception:
        pass

    vector_store = create_support_kb_vector_store()
    if not articles:
        return 0

    documents: list[Document] = []
    ids: list[str] = []
    for idx, entry in enumerate(articles, 1):
        article_id = str(entry.get("id") or f"kb_{idx}")
        ids.append(article_id)
        documents.append(
            Document(
                page_content=_build_article_text(entry, policies),
                metadata={
                    "article_id": article_id,
                    "title": str(entry.get("title", "")),
                    "category": str(entry.get("category", "OTHER")),
                },
            )
        )

    vector_store.add_documents(documents=documents, ids=ids)
    return len(documents)


def _similarity_retrieve(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    data = load_support_kb()
    articles = _get_articles(data)
    if not articles:
        return []

    by_id = {str(a.get("id")): a for a in articles if a.get("id")}
    vector_store = create_support_kb_vector_store()

    try:
        if vector_store._collection.count() == 0:
            rebuild_support_kb_index()
            vector_store = create_support_kb_vector_store()
    except Exception:
        pass

    try:
        results = vector_store.similarity_search_with_score(query, k=max(top_k, 1))
    except Exception:
        return []

    matched: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for doc, _score in results:
        article_id = str(doc.metadata.get("article_id", ""))
        if not article_id or article_id in seen_ids:
            continue
        entry = by_id.get(article_id)
        if entry:
            matched.append(entry)
            seen_ids.add(article_id)

    return matched[:top_k]


def _score_entry(query: str, query_tokens: set[str], entry: dict[str, Any]) -> float:
    score = 0.0
    normalized_query = _normalize_text(query)

    for intent in entry.get("intents", []):
        intent_norm = _normalize_text(intent)
        if intent_norm and intent_norm in normalized_query:
            score += 4.0

    keyword_hits = 0
    for keyword in entry.get("keywords", []):
        kw_tokens = _tokenize(keyword)
        if kw_tokens and kw_tokens.issubset(query_tokens):
            keyword_hits += 1
        elif kw_tokens and (kw_tokens & query_tokens):
            keyword_hits += 0.5
    score += float(keyword_hits)

    title_tokens = _tokenize(str(entry.get("title", "")))
    category_tokens = _tokenize(str(entry.get("category", "")))
    if title_tokens & query_tokens:
        score += 1.0
    if category_tokens & query_tokens:
        score += 1.0

    return score


def retrieve_support_knowledge(query: str, top_k: int = 3, min_score: float = 1.0) -> list[dict[str, Any]]:
    # Prefer vector search when the KB index is available.
    vector_results = _similarity_retrieve(query=query, top_k=top_k)
    if vector_results:
        return vector_results

    entries = _get_articles(load_support_kb())
    if not entries:
        return []

    query_tokens = _tokenize(query)
    scored: list[tuple[float, dict[str, Any]]] = []

    for entry in entries:
        score = _score_entry(query, query_tokens, entry)
        if score >= min_score:
            scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


def build_support_kb_context(query: str, top_k: int = 3) -> str:
    entries = retrieve_support_knowledge(query, top_k=top_k)
    if not entries:
        return "Không tìm thấy mục KB phù hợp. Nếu thiếu thông tin, hãy xin khách bổ sung và chuyển nhân viên CSKH."

    blocks: list[str] = []
    for idx, entry in enumerate(entries, 1):
        guidance = entry.get("guidance", [])
        required_fields = ", ".join(entry.get("required_fields", [])) or "không bắt buộc"
        escalation_rule = entry.get("escalation_rule", "không có")

        line = [
            f"[{idx}] {entry.get('title', 'KB item')} ({entry.get('category', 'OTHER')})",
            "Hướng dẫn:",
        ]
        for item in guidance[:3]:
            line.append(f"- {item}")
        line.append(f"Thông tin cần thu: {required_fields}")
        line.append(f"Escalation: {escalation_rule}")

        blocks.append("\n".join(line))

    return "\n\n".join(blocks)
