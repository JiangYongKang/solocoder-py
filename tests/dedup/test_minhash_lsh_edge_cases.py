import pytest

from solocoder_py.dedup import (
    MinHash,
    MinHashLSH,
    TextDedupEngine,
    jaccard_similarity,
    ngram_tokens,
)


class TestMinHashEdgeCases:
    def test_single_ngram_short_text(self):
        text = "abc"
        tokens = ngram_tokens(text, n=3)
        assert len(tokens) == 1
        assert "abc" in tokens

        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature(text)
        assert len(sig) == 64
        assert all(isinstance(v, int) for v in sig)

    def test_single_ngram_signature_consistent(self):
        mh = MinHash(num_perm=64, n=3)
        sig1 = mh.compute_signature("abc")
        sig2 = mh.compute_signature("abc")
        assert sig1 == sig2

    def test_two_char_text_with_n3(self):
        tokens = ngram_tokens("ab", n=3)
        assert tokens == {"ab"}

        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature("ab")
        assert len(sig) == 64

    def test_one_char_text_with_n3(self):
        tokens = ngram_tokens("a", n=3)
        assert tokens == {"a"}

        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature("a")
        assert len(sig) == 64

    def test_n_equals_1(self):
        tokens = ngram_tokens("hello", n=1)
        assert tokens == {"h", "e", "l", "o"}

    def test_large_n_value(self):
        text = "test"
        tokens = ngram_tokens(text, n=10)
        assert tokens == {text}


class TestJaccardEdgeCases:
    def test_similarity_exactly_one(self):
        s = {"a", "b", "c"}
        assert jaccard_similarity(s, s) == 1.0

    def test_similarity_exactly_zero(self):
        assert jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_single_element_sets(self):
        assert jaccard_similarity({"x"}, {"x"}) == 1.0
        assert jaccard_similarity({"x"}, {"y"}) == 0.0

    def test_large_sets(self):
        s1 = set(range(1000))
        s2 = set(range(500, 1500))
        sim = jaccard_similarity(s1, s2)
        assert 0.0 < sim < 1.0


class TestLSHEdgeCases:
    def test_single_element(self):
        mh = MinHash(num_perm=128, n=3)
        lsh = MinHashLSH(num_perm=128, threshold=0.5)
        sig = mh.compute_signature("test")
        lsh.insert(0, sig)
        pairs = lsh.get_candidate_pairs()
        assert pairs == []

    def test_all_identical(self):
        mh = MinHash(num_perm=128, n=3)
        lsh = MinHashLSH(num_perm=128, threshold=0.5)
        text = "the quick brown fox"

        for i in range(5):
            sig = mh.compute_signature(text)
            lsh.insert(i, sig)

        pairs = lsh.get_candidate_pairs()
        assert len(pairs) == 10

    def test_all_distinct(self):
        mh = MinHash(num_perm=256, n=3)
        lsh = MinHashLSH(num_perm=256, num_bands=8)

        distinct_texts = [
            "alpha beta gamma delta epsilon zeta eta theta",
            "apple banana cherry date elderberry fig grape",
            "mercury venus earth mars jupiter saturn neptune",
            "monday tuesday wednesday thursday friday saturday",
            "gold silver bronze platinum copper iron zinc",
        ]

        for i, text in enumerate(distinct_texts):
            sig = mh.compute_signature(text)
            lsh.insert(i, sig)

        pairs = lsh.get_candidate_pairs()
        assert len(pairs) <= 4

    def test_num_bands_equals_num_perm(self):
        lsh = MinHashLSH(num_perm=32, num_bands=32)
        assert lsh.band_config.num_bands == 32
        assert lsh.band_config.rows_per_band == 1

    def test_num_bands_one(self):
        lsh = MinHashLSH(num_perm=128, num_bands=1)
        assert lsh.band_config.num_bands == 1
        assert lsh.band_config.rows_per_band == 128


class TestTextDedupEdgeCases:
    def test_exact_same_texts_one_cluster(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.8)
        texts = [
            "hello world",
            "hello world",
            "hello world",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_clusters == 1
        assert result.total_duplicates == 2
        assert len(result.clusters[0].members) == 3

    def test_all_unique_texts_all_independent(self):
        engine = TextDedupEngine(num_perm=256, n=3, threshold=0.9)
        texts = [
            "abcdefghijklmnopqrstuvwxyz one",
            "abcdefghijklmnopqrstuvwxyz two",
            "abcdefghijklmnopqrstuvwxyz three",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_clusters == 3
        assert result.total_duplicates == 0

    def test_similarity_at_threshold_boundary(self):
        tokens_a = {"a", "b", "c", "d"}
        tokens_b = {"a", "b", "c", "d"}
        sim = jaccard_similarity(tokens_a, tokens_b)
        assert sim == 1.0

        tokens_c = {"a", "b", "c", "d"}
        tokens_d = {"e", "f", "g", "h"}
        sim2 = jaccard_similarity(tokens_c, tokens_d)
        assert sim2 == 0.0

        tokens_e = {"a", "b", "c", "d", "e"}
        tokens_f = {"a", "b", "c", "f", "g"}
        sim3 = jaccard_similarity(tokens_e, tokens_f)
        assert sim3 == pytest.approx(3 / 7)

    def test_identical_texts_always_clustered(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.99)
        texts = [
            "exactly the same text content",
            "exactly the same text content",
        ]
        engine.add_texts(texts)
        result = engine.dedup()
        assert result.total_clusters == 1
        assert len(result.clusters[0].members) == 2

    def test_empty_text_list(self):
        engine = TextDedupEngine()
        result = engine.dedup()
        assert result.total_input == 0
        assert result.total_clusters == 0
        assert result.total_duplicates == 0
        assert result.unique_texts == []
        assert result.unique_indices == []
        assert result.clusters == []

    def test_single_text(self):
        engine = TextDedupEngine()
        engine.add_text("only one text")
        result = engine.dedup()

        assert result.total_input == 1
        assert result.total_clusters == 1
        assert result.total_duplicates == 0
        assert len(result.clusters) == 1
        assert result.clusters[0].representative == "only one text"

    def test_two_identical_texts(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.8)
        engine.add_texts(["same text", "same text"])
        result = engine.dedup()

        assert result.total_input == 2
        assert result.total_clusters == 1
        assert result.total_duplicates == 1
        assert len(result.clusters[0].members) == 2

    def test_transitive_clustering(self):
        engine = TextDedupEngine(num_perm=256, n=2, threshold=0.5)
        texts = [
            "aaaaa bbbbb ccccc ddddd eeeee",
            "aaaaa bbbbb ccccc ddddd xxxxx",
            "aaaaa bbbbb ccccc yyyyy xxxxx",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        cluster_lens = sorted([len(c.members) for c in result.clusters], reverse=True)
        assert cluster_lens[0] >= 2

    def test_short_single_ngram_texts(self):
        engine = TextDedupEngine(num_perm=64, n=3, threshold=0.5)
        texts = ["abc", "abc", "def"]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 3
        assert result.total_clusters == 2

    def test_mixed_length_texts(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.6)
        texts = [
            "a",
            "ab",
            "abc",
            "abcd",
            "xyz",
        ]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 5
        assert result.total_clusters >= 2

    def test_large_number_of_texts(self):
        engine = TextDedupEngine(num_perm=64, n=3, threshold=0.8)
        texts = []
        for i in range(100):
            if i % 10 == 0:
                base = f"unique base text number {i}"
            texts.append(base + f" variant {i % 10}")

        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 100
        assert result.total_clusters <= 100
        assert result.total_clusters >= 1

    def test_cluster_member_indices_sorted(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.7)
        texts = ["test", "text", "test!", "other"]
        engine.add_texts(texts)
        result = engine.dedup()

        for cluster in result.clusters:
            assert cluster.member_indices == sorted(cluster.member_indices)

    def test_unique_indices_match_representatives(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.7)
        texts = ["alpha", "beta", "alpha!", "gamma", "beta?"]
        engine.add_texts(texts)
        result = engine.dedup()

        for text, idx in zip(result.unique_texts, result.unique_indices):
            assert text == texts[idx]

    def test_cluster_similarities_dict(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.7)
        texts = ["hello world", "hello world!", "hello world?"]
        engine.add_texts(texts)
        result = engine.dedup()

        for cluster in result.clusters:
            if len(cluster.members) >= 2:
                n = len(cluster.members)
                expected_pairs = n * (n - 1) // 2
                assert len(cluster.similarities) <= expected_pairs
                for sim in cluster.similarities.values():
                    assert 0.0 <= sim <= 1.0
