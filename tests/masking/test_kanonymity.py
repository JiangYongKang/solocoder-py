from __future__ import annotations

import pytest

from src.solocoder_py.masking import (
    DataRecord,
    KAnonymityChecker,
    KAnonymityError,
    KAnonymityReport,
    check_k_anonymity,
)


class TestKAnonymityChecker:
    def test_satisfies_k_anonymity(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="4", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="5", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="6", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.violating_count == 0
        assert report.total_classes == 2

    def test_violates_k_anonymity(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is False
        assert report.violating_count == 2

    def test_exactly_k_records_per_class(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="4", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.violating_count == 0

        class_sizes = [len(records) for records in report.equivalence_classes.values()]
        assert all(size == 2 for size in class_sizes)

    def test_single_quasi_identifier(self):
        records = [
            DataRecord(id="1", data={"age": "25-34"}),
            DataRecord(id="2", data={"age": "25-34"}),
            DataRecord(id="3", data={"age": "25-34"}),
            DataRecord(id="4", data={"age": "35-44"}),
            DataRecord(id="5", data={"age": "35-44"}),
        ]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age"])
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.total_classes == 2

    def test_multiple_quasi_identifiers(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**", "gender": "male"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**", "gender": "male"}),
            DataRecord(id="3", data={"age": "25-34", "zipcode": "1000**", "gender": "female"}),
            DataRecord(id="4", data={"age": "25-34", "zipcode": "1000**", "gender": "female"}),
        ]

        checker = KAnonymityChecker(
            k=2, quasi_identifiers=["age", "zipcode", "gender"]
        )
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.total_classes == 2

    def test_empty_dataset(self):
        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        report = checker.check([])

        assert report.is_anonymous is True
        assert report.total_records == 0
        assert report.violating_count == 0

    def test_single_record_dataset(self):
        records = [DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"})]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is False
        assert report.violating_count == 1

    def test_equivalence_class_grouping(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="4", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="5", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert len(report.equivalence_classes) == 2

        class_keys = list(report.equivalence_classes.keys())
        class_sizes = sorted(
            [len(records) for records in report.equivalence_classes.values()]
        )
        assert class_sizes == [2, 3]

    def test_k_equals_1(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="3", data={"age": "45-54", "zipcode": "3000**"}),
        ]

        checker = KAnonymityChecker(k=1, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.violating_count == 0

    def test_invalid_k_value(self):
        with pytest.raises(KAnonymityError, match="k must be at least 1"):
            KAnonymityChecker(k=0, quasi_identifiers=["age"])

        with pytest.raises(KAnonymityError, match="k must be at least 1"):
            KAnonymityChecker(k=-1, quasi_identifiers=["age"])

    def test_empty_quasi_identifiers(self):
        with pytest.raises(
            KAnonymityError, match="At least one quasi-identifier must be specified"
        ):
            KAnonymityChecker(k=3, quasi_identifiers=[])

    def test_is_anonymous_method(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "25-34", "zipcode": "1000**"}),
        ]

        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        assert checker.is_anonymous(records) is True

        checker2 = KAnonymityChecker(k=4, quasi_identifiers=["age", "zipcode"])
        assert checker2.is_anonymous(records) is False

    def test_callable_interface(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
        ]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
        report = checker(records)

        assert isinstance(report, KAnonymityReport)
        assert report.is_anonymous is True

    def test_report_to_dict(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)
        report_dict = report.to_dict()

        assert report_dict["k"] == 2
        assert report_dict["total_records"] == 3
        assert report_dict["is_anonymous"] is False
        assert report_dict["violating_classes_count"] == 1
        assert "violating_classes" in report_dict

    def test_missing_quasi_identifier_field(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="4", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(
            k=2, quasi_identifiers=["age", "zipcode"]
        )
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.total_classes == 2

    def test_null_values_in_quasi_identifiers(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": None}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": None}),
            DataRecord(id="3", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="4", data={"age": "25-34", "zipcode": "1000**"}),
        ]

        checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.total_classes == 2

    def test_large_dataset_performance(self, large_dataset_for_kanonymity):
        checker = KAnonymityChecker(
            k=5, quasi_identifiers=["age_range", "zipcode"]
        )
        report = checker.check(large_dataset_for_kanonymity)

        assert report.total_records == 20

    def test_check_k_anonymity_function(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "25-34", "zipcode": "1000**"}),
        ]

        report = check_k_anonymity(
            records=records, k=3, quasi_identifiers=["age", "zipcode"]
        )

        assert report.is_anonymous is True
        assert isinstance(report, KAnonymityReport)

    def test_violating_class_details(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert len(report.violating_classes) == 2

        report_dict = report.to_dict()
        violating = report_dict["violating_classes"]
        assert len(violating) == 2

        for violation in violating:
            assert "quasi_values" in violation
            assert "size" in violation
            assert violation["size"] < 3

    def test_quasi_identifiers_property(self):
        quasi_ids = ["age", "zipcode", "gender"]
        checker = KAnonymityChecker(k=3, quasi_identifiers=quasi_ids)

        assert checker.quasi_identifiers == quasi_ids
        assert checker.quasi_identifiers is not quasi_ids

    def test_k_property(self):
        checker = KAnonymityChecker(k=5, quasi_identifiers=["age"])
        assert checker.k == 5

    def test_report_properties(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="4", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="5", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.k == 3
        assert report.total_records == 5
        assert report.total_classes == 2
        assert report.violating_count == 1
        assert report.quasi_identifiers == ["age", "zipcode"]
