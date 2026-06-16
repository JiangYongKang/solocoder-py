import pytest

from solocoder_py.dedup import (
    ALL_REPRESENTATIVE_STRATEGIES,
    MinHash,
    MinHashLSH,
    REP_STRATEGY_CUSTOM,
    REP_STRATEGY_FIRST,
    REP_STRATEGY_LONGEST,
    REP_STRATEGY_MIDDLE_LENGTH,
    REP_STRATEGY_SHORTEST,
    TextDedupEngine,
    compute_band_config,
    jaccard_similarity,
    ngram_tokens,
)


class TestNgramTokens:
    def test_basic_3gram(self):
        tokens = ngram_tokens("hello", n=3)
        assert tokens == {"hel", "ell", "llo"}

    def test_2gram(self):
        tokens = ngram_tokens("hello", n=2)
        assert tokens == {"he", "el", "ll", "lo"}

    def test_text_shorter_than_n(self):
        tokens = ngram_tokens("hi", n=3)
        assert tokens == {"hi"}

    def test_empty_string(self):
        tokens = ngram_tokens("", n=3)
        assert tokens == set()

    def test_non_string_input(self):
        tokens = ngram_tokens(12345, n=3)
        assert tokens == {"123", "234", "345"}


class TestJaccardSimilarity:
    def test_identical_sets(self):
        s1 = {"a", "b", "c"}
        s2 = {"a", "b", "c"}
        assert jaccard_similarity(s1, s2) == 1.0

    def test_no_overlap(self):
        s1 = {"a", "b"}
        s2 = {"c", "d"}
        assert jaccard_similarity(s1, s2) == 0.0

    def test_partial_overlap(self):
        s1 = {"a", "b", "c"}
        s2 = {"b", "c", "d"}
        assert jaccard_similarity(s1, s2) == 0.5

    def test_both_empty(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert jaccard_similarity({"a"}, set()) == 0.0
        assert jaccard_similarity(set(), {"a"}) == 0.0


class TestMinHashSignature:
    def test_signature_length(self):
        mh = MinHash(num_perm=128, n=3)
        sig = mh.compute_signature("hello world")
        assert len(sig) == 128

    def test_signature_deterministic(self):
        mh = MinHash(num_perm=64, n=3, seed=42)
        sig1 = mh.compute_signature("test text")
        sig2 = mh.compute_signature("test text")
        assert sig1 == sig2

    def test_different_seeds_different_signatures(self):
        mh1 = MinHash(num_perm=64, n=3, seed=42)
        mh2 = MinHash(num_perm=64, n=3, seed=123)
        sig1 = mh1.compute_signature("test text")
        sig2 = mh2.compute_signature("test text")
        assert sig1 != sig2

    def test_identical_texts_same_signature(self):
        mh = MinHash(num_perm=128, n=3)
        sig1 = mh.compute_signature("hello world")
        sig2 = mh.compute_signature("hello world")
        assert sig1 == sig2
        assert MinHash.jaccard_from_signatures(sig1, sig2) == 1.0

    def test_similar_texts_high_signature_similarity(self):
        mh = MinHash(num_perm=256, n=3)
        sig1 = mh.compute_signature("this is a test sentence for minhash")
        sig2 = mh.compute_signature("this is a test sentence for minhash!")
        est_sim = MinHash.jaccard_from_signatures(sig1, sig2)
        assert est_sim > 0.7

    def test_different_texts_low_signature_similarity(self):
        mh = MinHash(num_perm=256, n=3)
        sig1 = mh.compute_signature("hello world")
        sig2 = mh.compute_signature("完全不同的内容")
        est_sim = MinHash.jaccard_from_signatures(sig1, sig2)
        assert est_sim < 0.3

    def test_compute_signature_from_tokens(self):
        mh = MinHash(num_perm=64, n=3)
        tokens = ngram_tokens("hello", n=3)
        sig1 = mh.compute_signature_from_tokens(tokens)
        sig2 = mh.compute_signature("hello")
        assert sig1 == sig2

    def test_empty_text_signature(self):
        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature("")
        assert len(sig) == 64
        assert all(v == 0 for v in sig)


class TestMinHashLSH:
    def test_insert_and_query(self):
        mh = MinHash(num_perm=128, n=3)
        lsh = MinHashLSH(num_perm=128, threshold=0.5)

        sig1 = mh.compute_signature("hello world test")
        sig2 = mh.compute_signature("hello world test!")
        sig3 = mh.compute_signature("completely different text")

        lsh.insert(0, sig1)
        lsh.insert(1, sig2)
        lsh.insert(2, sig3)

        candidates = lsh.query(sig1)
        assert 0 in candidates
        assert 1 in candidates

    def test_get_candidate_pairs(self):
        mh = MinHash(num_perm=128, n=3)
        lsh = MinHashLSH(num_perm=128, threshold=0.5)

        sig1 = mh.compute_signature("text alpha")
        sig2 = mh.compute_signature("text alpha beta")
        sig3 = mh.compute_signature("totally unrelated")

        lsh.insert(0, sig1)
        lsh.insert(1, sig2)
        lsh.insert(2, sig3)

        pairs = lsh.get_candidate_pairs()
        assert isinstance(pairs, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in pairs)

    def test_len(self):
        mh = MinHash(num_perm=64, n=3)
        lsh = MinHashLSH(num_perm=64, threshold=0.5)
        assert len(lsh) == 0

        sig = mh.compute_signature("test")
        lsh.insert(0, sig)
        assert len(lsh) == 1

    def test_clear(self):
        mh = MinHash(num_perm=64, n=3)
        lsh = MinHashLSH(num_perm=64, threshold=0.5)
        lsh.insert(0, mh.compute_signature("test"))
        lsh.clear()
        assert len(lsh) == 0
        assert lsh.get_candidate_pairs() == []

    def test_get_signature(self):
        mh = MinHash(num_perm=64, n=3)
        lsh = MinHashLSH(num_perm=64, threshold=0.5)
        sig = mh.compute_signature("test")
        lsh.insert(42, sig)
        assert lsh.get_signature(42) == sig
        assert lsh.get_signature(99) is None

    def test_signature_rows_discarded_exposed(self):
        lsh_divisible = MinHashLSH(num_perm=128, num_bands=16)
        assert lsh_divisible.signature_rows_discarded == 0
        assert lsh_divisible.band_config.total_rows_used == 128

        lsh_truncated = MinHashLSH(num_perm=100, num_bands=7)
        assert lsh_truncated.signature_rows_discarded > 0
        assert lsh_truncated.band_config.total_rows_used + lsh_truncated.signature_rows_discarded == 100

    def test_threshold_one_exact_match(self):
        mh = MinHash(num_perm=64, n=3)
        lsh = MinHashLSH(num_perm=64, threshold=1.0)
        assert lsh.band_config.num_bands == 64
        assert lsh.band_config.rows_per_band == 1
        assert lsh.signature_rows_discarded == 0

        text = "exact match test string for threshold 1.0"
        sig1 = mh.compute_signature(text)
        sig2 = mh.compute_signature(text)
        sig3 = [(x + 1) % (2**64 - 1) for x in sig1]

        lsh.insert(0, sig1)
        lsh.insert(1, sig2)
        lsh.insert(2, sig3)

        pairs = lsh.get_candidate_pairs()
        assert (0, 1) in pairs
        assert (0, 2) not in pairs
        assert (1, 2) not in pairs

    def test_similar_texts_hit_same_bucket(self):
        mh = MinHash(num_perm=256, n=3)
        lsh = MinHashLSH(num_perm=256, num_bands=32)

        text1 = "the quick brown fox jumps over the lazy dog"
        text2 = "the quick brown fox jumps over the lazy dog!"
        text3 = "completely different content here"

        sig1 = mh.compute_signature(text1)
        sig2 = mh.compute_signature(text2)
        sig3 = mh.compute_signature(text3)

        lsh.insert(0, sig1)
        lsh.insert(1, sig2)
        lsh.insert(2, sig3)

        pairs = lsh.get_candidate_pairs()
        assert (0, 1) in pairs
        pair_02 = (0, 2) in pairs
        pair_12 = (1, 2) in pairs
        assert not pair_02, f"unrelated pair (0, 2) should not be in candidate pairs, but got pairs: {pairs}"
        assert not pair_12, f"unrelated pair (1, 2) should not be in candidate pairs, but got pairs: {pairs}"


class TestComputeBandConfig:
    def test_with_num_bands(self):
        config = compute_band_config(128, num_bands=16)
        assert config.num_bands == 16
        assert config.rows_per_band == 8
        assert config.total_rows_used == 128

    def test_with_threshold(self):
        config = compute_band_config(128, threshold=0.8)
        assert config.num_bands > 0
        assert config.rows_per_band > 0
        assert config.num_bands * config.rows_per_band <= 128
        assert config.total_rows_used == config.num_bands * config.rows_per_band

    def test_band_config_less_than_num_perm(self):
        config = compute_band_config(100, num_bands=7)
        assert config.num_bands > 0
        assert config.rows_per_band > 0
        assert config.total_rows_used <= 100
        assert config.total_rows_used == config.num_bands * config.rows_per_band

    def test_total_rows_used_reveals_truncation(self):
        config = compute_band_config(100, num_bands=7)
        assert config.total_rows_used < 100
        discarded = 100 - config.total_rows_used
        assert discarded > 0


class TestTextDedupEngineNormalFlows:
    def test_highly_similar_texts_clustered(self):
        engine = TextDedupEngine(num_perm=256, n=3, threshold=0.7)
        texts = [
            "the quick brown fox jumps over the lazy dog",
            "the quick brown fox jumps over the lazy dog!",
            "the quick brown fox jumps over the lazy dog.",
            "completely different text content",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 4
        assert result.total_clusters <= 3
        assert result.total_duplicates >= 1

        cluster_sizes = sorted([len(c.members) for c in result.clusters], reverse=True)
        assert cluster_sizes[0] >= 2

    def test_representative_strategy_first(self):
        engine = TextDedupEngine(
            num_perm=256,
            n=3,
            threshold=0.7,
            representative_strategy=REP_STRATEGY_FIRST,
        )
        texts = [
            "short text first",
            "a much longer text that is similar",
            "short text first!",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        first_cluster = next(c for c in result.clusters if len(c.members) >= 2)
        assert first_cluster.rep_index == first_cluster.member_indices[0]

    def test_representative_strategy_longest(self):
        engine = TextDedupEngine(
            num_perm=256,
            n=3,
            threshold=0.7,
            representative_strategy=REP_STRATEGY_LONGEST,
        )
        texts = [
            "short",
            "this is a much longer text example",
            "short!",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        short_cluster = next(c for c in result.clusters if len(c.members) >= 2)
        assert len(short_cluster.representative) == max(
            len(m) for m in short_cluster.members
        )

    def test_representative_strategy_shortest(self):
        base = "abcdefghijklmnopqrstuvwxyz" * 5
        engine = TextDedupEngine(
            num_perm=128,
            n=3,
            threshold=0.7,
            num_bands=32,
            representative_strategy=REP_STRATEGY_SHORTEST,
        )
        texts = [
            base + "1234567890",
            base,
            base + "12345",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        cluster = next(c for c in result.clusters if len(c.members) >= 2)
        assert len(cluster.representative) == min(len(m) for m in cluster.members)

    def test_representative_strategy_middle_length(self):
        engine = TextDedupEngine(
            num_perm=256,
            n=3,
            threshold=0.6,
            representative_strategy=REP_STRATEGY_MIDDLE_LENGTH,
        )
        texts = [
            "a",
            "ab",
            "abc similar",
            "abcd also similar",
            "abcde even longer similar",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        for cluster in result.clusters:
            if len(cluster.members) >= 3:
                lengths = sorted([len(m) for m in cluster.members])
                mid_len = lengths[len(lengths) // 2]
                assert len(cluster.representative) == mid_len

    def test_representative_strategy_custom(self):
        def score_fn(text, idx):
            return len(text) * 10 - idx

        engine = TextDedupEngine(
            num_perm=128,
            n=3,
            threshold=0.8,
            num_bands=32,
            representative_strategy=REP_STRATEGY_CUSTOM,
            custom_score_fn=score_fn,
        )
        base = "the quick brown fox jumps over the lazy dog"
        texts = [
            base,
            base + " additional words to make it longer",
            base + " variant",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        cluster = next(c for c in result.clusters if len(c.members) >= 2)
        best_score = max(score_fn(text, idx) for text, idx in zip(cluster.members, cluster.member_indices))
        assert score_fn(cluster.representative, cluster.rep_index) == best_score

    def test_unique_texts_and_indices(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.7)
        texts = ["text a", "text b", "text c"]
        engine.add_texts(texts)
        result = engine.dedup()

        assert len(result.unique_texts) == result.total_clusters
        assert len(result.unique_indices) == result.total_clusters
        for text, idx in zip(result.unique_texts, result.unique_indices):
            assert text == texts[idx]

    def test_cluster_avg_similarity(self):
        engine = TextDedupEngine(num_perm=256, n=3, threshold=0.6)
        texts = [
            "hello world test",
            "hello world test!",
            "hello world test?",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        cluster = next(c for c in result.clusters if len(c.members) >= 3)
        assert 0.0 < cluster.avg_similarity <= 1.0

    def test_add_text_returns_index(self):
        engine = TextDedupEngine()
        idx1 = engine.add_text("first")
        idx2 = engine.add_text("second")
        assert idx1 == 0
        assert idx2 == 1

    def test_add_texts_returns_indices(self):
        engine = TextDedupEngine()
        indices = engine.add_texts(["a", "b", "c"])
        assert indices == [0, 1, 2]

    def test_engine_len(self):
        engine = TextDedupEngine()
        assert len(engine) == 0
        engine.add_texts(["a", "b"])
        assert len(engine) == 2

    def test_engine_clear(self):
        engine = TextDedupEngine()
        engine.add_texts(["test1", "test2"])
        assert len(engine) == 2
        engine.clear()
        assert len(engine) == 0
        result = engine.dedup()
        assert result.total_input == 0
