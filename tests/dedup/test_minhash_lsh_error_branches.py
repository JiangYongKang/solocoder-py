import pytest

from solocoder_py.dedup import (
    InvalidConfigError,
    MinHash,
    MinHashLSH,
    REP_STRATEGY_CUSTOM,
    REP_STRATEGY_FIRST,
    TextDedupEngine,
    UnknownStrategyError,
    compute_band_config,
    ngram_tokens,
)


class TestNgramTokensErrors:
    def test_n_zero(self):
        with pytest.raises(InvalidConfigError):
            ngram_tokens("hello", n=0)

    def test_n_negative(self):
        with pytest.raises(InvalidConfigError):
            ngram_tokens("hello", n=-1)


class TestMinHashErrors:
    def test_invalid_num_perm_zero(self):
        with pytest.raises(InvalidConfigError):
            MinHash(num_perm=0, n=3)

    def test_invalid_num_perm_negative(self):
        with pytest.raises(InvalidConfigError):
            MinHash(num_perm=-1, n=3)

    def test_invalid_n_zero(self):
        with pytest.raises(InvalidConfigError):
            MinHash(num_perm=128, n=0)

    def test_invalid_n_negative(self):
        with pytest.raises(InvalidConfigError):
            MinHash(num_perm=128, n=-2)

    def test_jaccard_from_signatures_mismatched_length(self):
        sig_a = [1, 2, 3]
        sig_b = [1, 2]
        with pytest.raises(ValueError, match="signatures must have the same length"):
            MinHash.jaccard_from_signatures(sig_a, sig_b)

    def test_jaccard_from_signatures_empty(self):
        result = MinHash.jaccard_from_signatures([], [])
        assert result == 0.0


class TestMinHashLSHErrors:
    def test_invalid_num_perm_zero(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=0, threshold=0.5)

    def test_invalid_num_perm_negative(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=-1, threshold=0.5)

    def test_no_num_bands_no_threshold(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=128, num_bands=None, threshold=None)

    def test_insert_signature_length_mismatch(self):
        lsh = MinHashLSH(num_perm=64, threshold=0.5)
        bad_sig = [0] * 32
        with pytest.raises(ValueError, match="signature length mismatch"):
            lsh.insert(0, bad_sig)

    def test_query_signature_length_mismatch(self):
        lsh = MinHashLSH(num_perm=64, threshold=0.5)
        bad_sig = [0] * 128
        with pytest.raises(ValueError, match="signature length mismatch"):
            lsh.query(bad_sig)

    def test_num_bands_zero(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=128, num_bands=0)

    def test_num_bands_negative(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=128, num_bands=-1)

    def test_num_bands_greater_than_num_perm(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=10, num_bands=20)

    def test_threshold_zero(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=128, threshold=0)

    def test_threshold_one(self):
        lsh = MinHashLSH(num_perm=128, threshold=1.0)
        assert lsh.band_config.num_bands == 128
        assert lsh.band_config.rows_per_band == 1

    def test_threshold_negative(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=128, threshold=-0.5)

    def test_threshold_over_one(self):
        with pytest.raises(InvalidConfigError):
            MinHashLSH(num_perm=128, threshold=1.5)


class TestComputeBandConfigErrors:
    def test_num_bands_zero(self):
        with pytest.raises(InvalidConfigError):
            compute_band_config(128, num_bands=0)

    def test_num_bands_negative(self):
        with pytest.raises(InvalidConfigError):
            compute_band_config(128, num_bands=-5)

    def test_num_bands_greater_than_num_perm(self):
        with pytest.raises(InvalidConfigError):
            compute_band_config(10, num_bands=20)

    def test_threshold_zero(self):
        with pytest.raises(InvalidConfigError):
            compute_band_config(128, threshold=0)

    def test_threshold_one(self):
        config = compute_band_config(128, threshold=1.0)
        assert config.num_bands == 128
        assert config.rows_per_band == 1
        assert config.total_rows_used == 128

    def test_no_params(self):
        with pytest.raises(InvalidConfigError):
            compute_band_config(128)


class TestTextDedupEngineErrors:
    def test_invalid_threshold_zero(self):
        with pytest.raises(InvalidConfigError):
            TextDedupEngine(threshold=0)

    def test_invalid_threshold_negative(self):
        with pytest.raises(InvalidConfigError):
            TextDedupEngine(threshold=-0.5)

    def test_invalid_threshold_over_one(self):
        with pytest.raises(InvalidConfigError):
            TextDedupEngine(threshold=1.5)

    def test_unknown_strategy(self):
        with pytest.raises(UnknownStrategyError):
            TextDedupEngine(representative_strategy="nonexistent_strategy")

    def test_custom_strategy_without_fn(self):
        with pytest.raises(InvalidConfigError):
            TextDedupEngine(representative_strategy=REP_STRATEGY_CUSTOM)

    def test_invalid_num_perm(self):
        with pytest.raises(InvalidConfigError):
            TextDedupEngine(num_perm=0)

    def test_invalid_n_value(self):
        with pytest.raises(InvalidConfigError):
            TextDedupEngine(n=0)


class TestEmptyTextHandling:
    def test_empty_text_signature(self):
        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature("")
        assert len(sig) == 64
        assert all(v == 0 for v in sig)

    def test_empty_text_dedup_single(self):
        engine = TextDedupEngine(num_perm=64, n=3, threshold=0.5)
        engine.add_text("")
        result = engine.dedup()
        assert result.total_input == 1
        assert result.total_clusters == 1

    def test_multiple_empty_texts_clustered(self):
        engine = TextDedupEngine(num_perm=64, n=3, threshold=0.5)
        engine.add_texts(["", "", ""])
        result = engine.dedup()
        assert result.total_input == 3
        assert result.total_clusters == 1
        assert len(result.clusters[0].members) == 3

    def test_empty_and_nonempty_texts(self):
        engine = TextDedupEngine(num_perm=128, n=3, threshold=0.5)
        texts = ["", "hello", "", "world"]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 4
        empty_cluster = None
        for cluster in result.clusters:
            if cluster.representative == "":
                empty_cluster = cluster
                break
        assert empty_cluster is not None
        assert len(empty_cluster.members) == 2

    def test_empty_text_tokens(self):
        tokens = ngram_tokens("", n=3)
        assert isinstance(tokens, set)
        assert len(tokens) == 0

    def test_empty_text_jaccard(self):
        from solocoder_py.dedup import jaccard_similarity

        sim = jaccard_similarity(set(), set())
        assert sim == 1.0


class TestSingleNgramShortTextErrors:
    def test_short_text_signature_computation(self):
        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature("ab")
        assert len(sig) == 64
        assert all(isinstance(v, int) for v in sig)

    def test_single_char_text(self):
        mh = MinHash(num_perm=64, n=3)
        sig = mh.compute_signature("x")
        assert len(sig) == 64

    def test_single_char_dedup(self):
        engine = TextDedupEngine(num_perm=64, n=3, threshold=0.5)
        engine.add_texts(["a", "a", "b"])
        result = engine.dedup()
        assert result.total_input == 3
        assert result.total_clusters == 2


class TestLargeVolumeBucketHandling:
    def test_many_texts_all_similar(self):
        engine = TextDedupEngine(num_perm=32, n=3, threshold=0.7)
        base_text = "the quick brown fox jumps over the lazy dog"
        texts = [base_text + str(i) for i in range(50)]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 50
        assert result.total_clusters >= 1

    def test_many_texts_all_unique(self):
        engine = TextDedupEngine(num_perm=64, n=3, threshold=0.9)
        texts = [f"text number {i} with unique content" + "x" * i for i in range(50)]
        engine.add_texts(texts)
        result = engine.dedup()

        assert result.total_input == 50
        assert result.total_clusters <= 50
