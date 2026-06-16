from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .exceptions import InvalidConfigError, UnknownStrategyError
from .lsh import MinHashLSH
from .min_hash import MinHash, jaccard_similarity, ngram_tokens


STRATEGY_FIRST = "first"
STRATEGY_LONGEST = "longest"
STRATEGY_SHORTEST = "shortest"
STRATEGY_MIDDLE_LENGTH = "middle_length"
STRATEGY_CUSTOM = "custom"

ALL_REPRESENTATIVE_STRATEGIES = [
    STRATEGY_FIRST,
    STRATEGY_LONGEST,
    STRATEGY_SHORTEST,
    STRATEGY_MIDDLE_LENGTH,
    STRATEGY_CUSTOM,
]


@dataclass
class TextDedupCluster:
    representative: str
    rep_index: int
    members: list[str]
    member_indices: list[int]
    similarities: dict[tuple[int, int], float] = field(default_factory=dict)
    avg_similarity: float = 0.0


@dataclass
class TextDedupResult:
    clusters: list[TextDedupCluster]
    total_input: int
    total_clusters: int
    total_duplicates: int
    unique_texts: list[str]
    unique_indices: list[int]


class TextDedupEngine:
    def __init__(
        self,
        num_perm: int = 128,
        n: int = 3,
        threshold: float = 0.8,
        num_bands: int | None = None,
        representative_strategy: str = STRATEGY_FIRST,
        custom_score_fn: Callable[[str, int], float] | None = None,
        seed: int = 42,
    ) -> None:
        if threshold <= 0 or threshold > 1:
            raise InvalidConfigError("threshold must be in (0, 1]")
        if representative_strategy not in ALL_REPRESENTATIVE_STRATEGIES:
            raise UnknownStrategyError(
                f"Unknown representative strategy: {representative_strategy}"
            )
        if representative_strategy == STRATEGY_CUSTOM and custom_score_fn is None:
            raise InvalidConfigError(
                "custom_score_fn must be provided when using custom strategy"
            )

        self.num_perm = num_perm
        self.n = n
        self.threshold = threshold
        self.representative_strategy = representative_strategy
        self.custom_score_fn = custom_score_fn
        self.seed = seed

        self.minhash = MinHash(num_perm=num_perm, n=n, seed=seed)
        self.lsh = MinHashLSH(num_perm=num_perm, num_bands=num_bands, threshold=threshold)
        self.signature_rows_discarded = self.lsh.signature_rows_discarded

        self._texts: list[str] = []
        self._signatures: list[list[int]] = []
        self._tokens: list[set[str]] = []

    def add_text(self, text: str) -> int:
        idx = len(self._texts)
        self._texts.append(text)
        tokens = ngram_tokens(text, self.n)
        self._tokens.append(tokens)
        signature = self.minhash.compute_signature_from_tokens(tokens)
        self._signatures.append(signature)
        self.lsh.insert(idx, signature)
        return idx

    def add_texts(self, texts: list[str]) -> list[int]:
        indices = []
        for text in texts:
            idx = self.add_text(text)
            indices.append(idx)
        return indices

    def dedup(self) -> TextDedupResult:
        if not self._texts:
            return TextDedupResult(
                clusters=[],
                total_input=0,
                total_clusters=0,
                total_duplicates=0,
                unique_texts=[],
                unique_indices=[],
            )

        candidate_pairs = self.lsh.get_candidate_pairs()

        similarity_map: dict[tuple[int, int], float] = {}
        for i, j in candidate_pairs:
            sim = jaccard_similarity(self._tokens[i], self._tokens[j])
            if sim >= self.threshold:
                key = (min(i, j), max(i, j))
                similarity_map[key] = sim

        clusters = self._build_clusters(similarity_map)

        unique_texts = [c.representative for c in clusters]
        unique_indices = [c.rep_index for c in clusters]
        total_duplicates = len(self._texts) - len(clusters)

        return TextDedupResult(
            clusters=clusters,
            total_input=len(self._texts),
            total_clusters=len(clusters),
            total_duplicates=total_duplicates,
            unique_texts=unique_texts,
            unique_indices=unique_indices,
        )

    def _build_clusters(
        self, similarity_map: dict[tuple[int, int], float]
    ) -> list[TextDedupCluster]:
        n = len(self._texts)
        parent = list(range(n))
        rank = [0] * n

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                parent[px] = py
            elif rank[px] > rank[py]:
                parent[py] = px
            else:
                parent[py] = px
                rank[px] += 1

        for (i, j) in similarity_map:
            union(i, j)

        groups: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(i)

        clusters: list[TextDedupCluster] = []
        for root, indices in groups.items():
            indices_sorted = sorted(indices)
            members = [self._texts[i] for i in indices_sorted]

            cluster_sims: dict[tuple[int, int], float] = {}
            sim_values: list[float] = []
            for i_idx in range(len(indices_sorted)):
                for j_idx in range(i_idx + 1, len(indices_sorted)):
                    a, b = indices_sorted[i_idx], indices_sorted[j_idx]
                    key = (min(a, b), max(a, b))
                    if key in similarity_map:
                        sim = similarity_map[key]
                    else:
                        sim = jaccard_similarity(self._tokens[a], self._tokens[b])
                    cluster_sims[key] = sim
                    sim_values.append(sim)

            avg_sim = sum(sim_values) / len(sim_values) if sim_values else 1.0

            rep_index = self._select_representative(indices_sorted)
            representative = self._texts[rep_index]

            clusters.append(
                TextDedupCluster(
                    representative=representative,
                    rep_index=rep_index,
                    members=members,
                    member_indices=indices_sorted,
                    similarities=cluster_sims,
                    avg_similarity=avg_sim,
                )
            )

        return clusters

    def _select_representative(self, indices: list[int]) -> int:
        if len(indices) == 1:
            return indices[0]

        strategy = self.representative_strategy

        if strategy == STRATEGY_FIRST:
            return indices[0]

        if strategy == STRATEGY_LONGEST:
            best_idx = indices[0]
            best_len = len(self._texts[best_idx])
            for idx in indices[1:]:
                text_len = len(self._texts[idx])
                if text_len > best_len:
                    best_len = text_len
                    best_idx = idx
            return best_idx

        if strategy == STRATEGY_SHORTEST:
            best_idx = indices[0]
            best_len = len(self._texts[best_idx])
            for idx in indices[1:]:
                text_len = len(self._texts[idx])
                if text_len < best_len:
                    best_len = text_len
                    best_idx = idx
            return best_idx

        if strategy == STRATEGY_MIDDLE_LENGTH:
            lengths = [(idx, len(self._texts[idx])) for idx in indices]
            lengths.sort(key=lambda x: x[1])
            mid = len(lengths) // 2
            return lengths[mid][0]

        if strategy == STRATEGY_CUSTOM and self.custom_score_fn is not None:
            best_idx = indices[0]
            best_score = self.custom_score_fn(self._texts[best_idx], best_idx)
            for idx in indices[1:]:
                score = self.custom_score_fn(self._texts[idx], idx)
                if score > best_score:
                    best_score = score
                    best_idx = idx
            return best_idx

        return indices[0]

    def clear(self) -> None:
        self._texts.clear()
        self._signatures.clear()
        self._tokens.clear()
        self.lsh.clear()

    def __len__(self) -> int:
        return len(self._texts)
