"""混合检索：BM25 + BGE-M3 向量召回，RRF 融合，BGE reranker 重排。"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any

import jieba
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

from app.config import settings

logger = logging.getLogger(__name__)

RRF_K = 60
RECALL_K = settings.retrieval_recall_k


@dataclass
class RetrievedChunk:
    content: str
    source: str
    heading: str
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in jieba.lcut(text.lower()):
        token = token.strip()
        if token and re.search(r"[\w一-鿿]", token):
            tokens.append(token)
    return tokens


class HybridRetriever:
    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self.by_id: dict[str, dict[str, Any]] = {}
        self.bm25: BM25Okapi | None = None
        self.vectorstore: Chroma | None = None
        self._reranker = None
        self._reranker_failed = False

        self._load_chunks()
        if self.chunks:
            self._build_bm25()
            self._build_vectorstore()

    def _load_chunks(self) -> None:
        path = settings.chunks_path
        if not path.exists():
            logger.warning("chunks 文件不存在：%s（请先运行 python -m app.rag.ingest）", path)
            return
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                metadata = item.get("metadata", {})
                chunk_id = metadata.get("chunk_id")
                if not chunk_id:
                    continue
                record = {"content": item["content"], "metadata": metadata}
                self.chunks.append(record)
                self.by_id[chunk_id] = record

    def _build_bm25(self) -> None:
        corpus = [tokenize(item["content"]) for item in self.chunks]
        self.bm25 = BM25Okapi(corpus)

    def _build_vectorstore(self) -> None:
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.embed_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True, "batch_size": 8},
            )
            self.vectorstore = Chroma(
                collection_name="hr_docs",
                persist_directory=str(settings.chroma_path),
                embedding_function=embeddings,
            )
        except Exception:  # noqa: BLE001
            logger.exception("加载向量库失败，本次降级为 BM25-only")
            self.vectorstore = None

    def _get_reranker(self):
        if self._reranker is not None or self._reranker_failed:
            return self._reranker
        try:
            from FlagEmbedding import FlagReranker

            self._reranker = FlagReranker(
                settings.rerank_model,
                use_fp16=False,
                max_length=settings.rerank_max_length,
            )
        except Exception:  # noqa: BLE001
            logger.exception("加载 reranker 失败，本次按 RRF 分数排序")
            self._reranker_failed = True
            self._reranker = None
        return self._reranker

    def _dense_search(self, query: str, k: int = RECALL_K) -> list[tuple[str, float]]:
        if self.vectorstore is None:
            return []
        try:
            hits = self.vectorstore.similarity_search_with_score(query, k=k)
        except Exception:  # noqa: BLE001
            logger.exception("向量检索失败，本次跳过 dense 召回")
            return []
        results: list[tuple[str, float]] = []
        for doc, distance in hits:
            chunk_id = doc.metadata.get("chunk_id")
            if not chunk_id or chunk_id not in self.by_id:
                continue
            # 归一化向量的 squared L2 距离，转成 0~1 的相似度。
            results.append((chunk_id, 1.0 / (1.0 + float(distance))))
        return results

    def _sparse_search(self, query: str, k: int = RECALL_K) -> list[tuple[str, float]]:
        if self.bm25 is None:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [
            (self.chunks[i]["metadata"]["chunk_id"], float(scores[i]))
            for i in order
            if scores[i] > 0
        ]

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not self.chunks:
            return []

        dense = self._dense_search(query)
        sparse = self._sparse_search(query)

        fused: dict[str, float] = {}
        for rank, (chunk_id, _) in enumerate(dense, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
        for rank, (chunk_id, _) in enumerate(sparse, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)

        if not fused:
            return []

        candidates = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:RECALL_K]
        dense_map = dict(dense)
        sparse_map = dict(sparse)

        reranker = self._get_reranker()
        rerank_scores: list[float] | None = None
        if reranker is not None:
            pairs = [[query, self.by_id[chunk_id]["content"]] for chunk_id, _ in candidates]
            try:
                raw = reranker.compute_score(
                    pairs,
                    normalize=True,
                    batch_size=settings.rerank_batch_size,
                )
                if isinstance(raw, (int, float)):
                    rerank_scores = [float(raw)]
                else:
                    rerank_scores = [float(x) for x in raw]
            except Exception:  # noqa: BLE001
                logger.exception("rerank 失败，本次按 RRF 分数排序")
                rerank_scores = None

        results: list[RetrievedChunk] = []
        for index, (chunk_id, rrf_score) in enumerate(candidates):
            record = self.by_id[chunk_id]
            metadata = record["metadata"]
            rerank_score = rerank_scores[index] if rerank_scores is not None else None
            results.append(
                RetrievedChunk(
                    content=record["content"],
                    source=metadata.get("source", ""),
                    heading=metadata.get("heading", ""),
                    score=rerank_score if rerank_score is not None else rrf_score,
                    dense_score=dense_map.get(chunk_id, 0.0),
                    sparse_score=sparse_map.get(chunk_id, 0.0),
                    rerank_score=rerank_score,
                    metadata=metadata,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def is_confident(results: list[RetrievedChunk], threshold: float = 0.2) -> bool:
        if not results:
            return False
        if results[0].rerank_score is None:
            return True
        return results[0].rerank_score >= threshold

    @staticmethod
    def format_context(results: list[RetrievedChunk]) -> str:
        blocks = []
        for index, item in enumerate(results, start=1):
            blocks.append(
                f"[资料{index}] 来源：{item.source} / {item.heading}\n{item.content}"
            )
        return "\n\n".join(blocks)


_retriever: HybridRetriever | None = None
_retriever_lock = threading.Lock()


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        with _retriever_lock:
            if _retriever is None:
                _retriever = HybridRetriever()
    return _retriever
