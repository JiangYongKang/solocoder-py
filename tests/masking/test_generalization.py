from __future__ import annotations

import pytest

from src.solocoder_py.masking import (
    GeneralizationStrategy,
    generalize_age,
    generalize_category,
    generalize_ip,
    generalize_numeric_range,
    generalize_zipcode,
)


class TestAgeGeneralization:
    def test_age_level_0_exact_value(self):
        assert generalize_age(27, 0) == "27"
        assert generalize_age(0, 0) == "0"
        assert generalize_age(99, 0) == "99"

    def test_age_level_1_10_year_ranges(self):
        assert generalize_age(17, 1) == "<18"
        assert generalize_age(18, 1) == "18-24"
        assert generalize_age(24, 1) == "18-24"
        assert generalize_age(25, 1) == "25-34"
        assert generalize_age(34, 1) == "25-34"
        assert generalize_age(35, 1) == "35-44"
        assert generalize_age(44, 1) == "35-44"
        assert generalize_age(45, 1) == "45-54"
        assert generalize_age(54, 1) == "45-54"
        assert generalize_age(55, 1) == "55-64"
        assert generalize_age(64, 1) == "55-64"
        assert generalize_age(65, 1) == "65+"

    def test_age_level_2_20_year_ranges(self):
        assert generalize_age(17, 2) == "<18"
        assert generalize_age(18, 2) == "18-34"
        assert generalize_age(34, 2) == "18-34"
        assert generalize_age(35, 2) == "35-54"
        assert generalize_age(54, 2) == "35-54"
        assert generalize_age(55, 2) == "55+"

    def test_age_level_3_adult_minor(self):
        assert generalize_age(17, 3) == "minor"
        assert generalize_age(18, 3) == "adult"
        assert generalize_age(99, 3) == "adult"

    def test_age_level_4_full_suppression(self):
        assert generalize_age(27, 4) == "*"
        assert generalize_age(50, 4) == "*"
        assert generalize_age(99, 4) == "*"

    def test_age_higher_levels_suppression(self):
        for level in range(4, 10):
            assert generalize_age(27, level) == "*"

    def test_age_none_value(self):
        assert generalize_age(None, 1) == ""

    def test_age_negative_value(self):
        assert generalize_age(-5, 1) == "invalid"

    def test_age_non_numeric_value(self):
        assert generalize_age("not_a_number", 1) == "not_a_number"

    def test_age_string_numeric_value(self):
        assert generalize_age("27", 1) == "25-34"


class TestAgeGeneralizationDynamicStep:
    def test_age_dynamic_step_level_0_exact_value(self):
        assert generalize_age(27, 0, step_years=5) == "27"
        assert generalize_age(0, 0, step_years=5) == "0"
        assert generalize_age(99, 0, step_years=5) == "99"

    def test_age_dynamic_step_5_years_level_1(self):
        assert generalize_age(27, 1, step_years=5) == "25-30"
        assert generalize_age(25, 1, step_years=5) == "25-30"
        assert generalize_age(29, 1, step_years=5) == "25-30"
        assert generalize_age(30, 1, step_years=5) == "30-35"
        assert generalize_age(17, 1, step_years=5) == "15-20"
        assert generalize_age(0, 1, step_years=5) == "0-5"
        assert generalize_age(99, 1, step_years=5) == "95-100"

    def test_age_dynamic_step_5_years_level_2(self):
        assert generalize_age(27, 2, step_years=5) == "20-30"
        assert generalize_age(25, 2, step_years=5) == "20-30"
        assert generalize_age(34, 2, step_years=5) == "30-40"
        assert generalize_age(17, 2, step_years=5) == "10-20"
        assert generalize_age(0, 2, step_years=5) == "0-10"
        assert generalize_age(99, 2, step_years=5) == "90-100"

    def test_age_dynamic_step_5_years_level_3(self):
        assert generalize_age(17, 3, step_years=5) == "minor"
        assert generalize_age(18, 3, step_years=5) == "adult"
        assert generalize_age(27, 3, step_years=5) == "adult"
        assert generalize_age(99, 3, step_years=5) == "adult"

    def test_age_dynamic_step_5_years_level_4_full_suppression(self):
        assert generalize_age(27, 4, step_years=5) == "*"
        assert generalize_age(50, 4, step_years=5) == "*"
        assert generalize_age(99, 4, step_years=5) == "*"

    def test_age_dynamic_step_higher_levels_suppression(self):
        for level in range(4, 10):
            assert generalize_age(27, level, step_years=5) == "*"

    def test_age_dynamic_step_none_value(self):
        assert generalize_age(None, 1, step_years=5) == ""

    def test_age_dynamic_step_negative_value(self):
        assert generalize_age(-5, 1, step_years=5) == "invalid"

    def test_age_dynamic_step_non_numeric_value(self):
        assert generalize_age("not_a_number", 1, step_years=5) == "not_a_number"

    def test_age_dynamic_step_string_numeric_value(self):
        assert generalize_age("27", 1, step_years=5) == "25-30"

    def test_age_dynamic_step_1_year(self):
        assert generalize_age(27, 1, step_years=1) == "27-28"
        assert generalize_age(27, 2, step_years=1) == "26-28"

    def test_age_dynamic_step_10_years(self):
        assert generalize_age(27, 1, step_years=10) == "20-30"
        assert generalize_age(27, 2, step_years=10) == "20-40"

    def test_age_dynamic_step_zero_falls_back_to_default(self):
        assert generalize_age(27, 1, step_years=0) == "25-34"
        assert generalize_age(25, 1, step_years=0) == "25-34"

    def test_age_dynamic_step_none_falls_back_to_default(self):
        assert generalize_age(27, 1, step_years=None) == "25-34"
        assert generalize_age(25, 1, step_years=None) == "25-34"

    def test_age_dynamic_step_boundary_values(self):
        assert generalize_age(5, 1, step_years=5) == "5-10"
        assert generalize_age(4, 1, step_years=5) == "0-5"
        assert generalize_age(9, 1, step_years=5) == "5-10"
        assert generalize_age(10, 1, step_years=5) == "10-15"


class TestZipcodeGeneralization:
    def test_zipcode_level_0_exact(self):
        assert generalize_zipcode("100081", 0) == "100081"

    def test_zipcode_level_1_mask_one(self):
        assert generalize_zipcode("100081", 1) == "10008*"

    def test_zipcode_level_2_mask_two(self):
        assert generalize_zipcode("100081", 2) == "1000**"

    def test_zipcode_level_3_mask_three(self):
        assert generalize_zipcode("100081", 3) == "100***"

    def test_zipcode_level_4_mask_four(self):
        assert generalize_zipcode("100081", 4) == "10****"

    def test_zipcode_level_5_mask_five(self):
        assert generalize_zipcode("100081", 5) == "1*****"

    def test_zipcode_level_6_full_mask(self):
        assert generalize_zipcode("100081", 6) == "******"

    def test_zipcode_higher_levels_full_mask(self):
        for level in range(6, 10):
            assert generalize_zipcode("100081", level) == "******"

    def test_zipcode_different_lengths(self):
        assert generalize_zipcode("12345", 2) == "123**"
        assert generalize_zipcode("12345", 5) == "*****"

    def test_zipcode_none_value(self):
        assert generalize_zipcode(None, 1) == ""

    def test_zipcode_empty_string(self):
        assert generalize_zipcode("", 1) == ""

    def test_zipcode_non_string_value(self):
        assert generalize_zipcode(100081, 2) == "1000**"


class TestIPGeneralization:
    def test_ip_level_0_full_ip(self):
        assert generalize_ip("192.168.1.100", 0) == "192.168.1.100"

    def test_ip_level_1_mask_last_octet(self):
        assert generalize_ip("192.168.1.100", 1) == "192.168.1.*"

    def test_ip_level_2_mask_last_two_octets(self):
        assert generalize_ip("192.168.1.100", 2) == "192.168.*.*"

    def test_ip_level_3_mask_last_three_octets(self):
        assert generalize_ip("192.168.1.100", 3) == "192.*.*.*"

    def test_ip_level_4_full_mask(self):
        assert generalize_ip("192.168.1.100", 4) == "*.*.*.*"

    def test_ip_higher_levels_full_mask(self):
        for level in range(4, 10):
            assert generalize_ip("192.168.1.100", level) == "*.*.*.*"

    def test_ip_none_value(self):
        assert generalize_ip(None, 1) == ""

    def test_ip_empty_string(self):
        assert generalize_ip("", 1) == ""

    def test_ip_invalid_format(self):
        assert generalize_ip("not_an_ip", 1) == "not_an_ip"
        assert generalize_ip("192.168.1", 1) == "192.168.1"
        assert generalize_ip("192.168.1.256", 1) == "192.168.1.256"

    def test_ip_different_addresses(self):
        assert generalize_ip("10.0.0.1", 2) == "10.0.*.*"
        assert generalize_ip("172.16.0.1", 1) == "172.16.0.*"
        assert generalize_ip("255.255.255.255", 3) == "255.*.*.*"


class TestNumericRangeGeneralization:
    def test_numeric_level_0_exact(self):
        assert generalize_numeric_range(27, 0) == "27"
        assert generalize_numeric_range(27.5, 0) == "27.5"

    def test_numeric_level_1_ranges(self):
        assert generalize_numeric_range(5, 1) == "<10"
        assert generalize_numeric_range(15, 1) == "10-19"
        assert generalize_numeric_range(25, 1) == "20-29"
        assert generalize_numeric_range(35, 1) == "30-49"
        assert generalize_numeric_range(75, 1) == "50-99"
        assert generalize_numeric_range(150, 1) == "100+"

    def test_numeric_level_2_coarse_ranges(self):
        assert generalize_numeric_range(25, 2) == "<50"
        assert generalize_numeric_range(75, 2) == "50+"

    def test_numeric_level_3_suppression(self):
        assert generalize_numeric_range(50, 3) == "*"
        assert generalize_numeric_range(100, 3) == "*"

    def test_numeric_higher_levels_suppression(self):
        for level in range(3, 10):
            assert generalize_numeric_range(50, level) == "*"

    def test_numeric_none_value(self):
        assert generalize_numeric_range(None, 1) == ""

    def test_numeric_non_numeric_value(self):
        assert generalize_numeric_range("not_a_number", 1) == "not_a_number"

    def test_numeric_boundary_values(self):
        assert generalize_numeric_range(9.999, 1) == "<10"
        assert generalize_numeric_range(10, 1) == "10-19"
        assert generalize_numeric_range(19.999, 1) == "10-19"
        assert generalize_numeric_range(20, 1) == "20-29"


class TestCategoryGeneralization:
    def test_category_level_0_exact(self):
        assert generalize_category("male", 0) == "male"
        assert generalize_category("Female", 0) == "Female"
        assert generalize_category("Other", 0) == "Other"

    def test_category_level_1_normalized(self):
        assert generalize_category("Male", 1) == "male"
        assert generalize_category("FEMALE", 1) == "female"
        assert generalize_category("Unknown", 1) == "other"

    def test_category_level_2_person(self):
        assert generalize_category("male", 2) == "person"
        assert generalize_category("female", 2) == "person"
        assert generalize_category("other", 2) == "person"

    def test_category_level_3_suppression(self):
        assert generalize_category("male", 3) == "*"

    def test_category_higher_levels_suppression(self):
        for level in range(3, 10):
            assert generalize_category("male", level) == "*"

    def test_category_none_value(self):
        assert generalize_category(None, 1) == ""

    def test_category_empty_string(self):
        assert generalize_category("", 1) == ""


class TestGeneralizationStrategyClass:
    def test_create_age_generalizer(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)
        assert generalizer.current_level == 1
        assert generalizer.generalize(27) == "25-34"

    def test_create_zipcode_generalizer(self):
        generalizer = GeneralizationStrategy.create_zipcode_generalizer(
            default_level=2, zipcode_length=6
        )
        assert generalizer.current_level == 2
        assert generalizer.generalize("100081") == "1000**"
        assert generalizer.max_level == 6

    def test_create_ip_generalizer(self):
        generalizer = GeneralizationStrategy.create_ip_generalizer(default_level=1)
        assert generalizer.current_level == 1
        assert generalizer.generalize("192.168.1.100") == "192.168.1.*"

    def test_set_level(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=0)
        assert generalizer.current_level == 0

        generalizer.set_level(2)
        assert generalizer.current_level == 2
        assert generalizer.generalize(27) == "18-34"

    def test_set_level_out_of_range(self):
        from src.solocoder_py.masking import InvalidConfigurationError

        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=0)
        max_level = generalizer.max_level

        with pytest.raises(InvalidConfigurationError, match="exceeds max level"):
            generalizer.set_level(max_level + 1)

    def test_set_level_negative(self):
        from src.solocoder_py.masking import InvalidConfigurationError

        generalizer = GeneralizationStrategy.create_age_generalizer()
        with pytest.raises(InvalidConfigurationError, match="negative"):
            generalizer.set_level(-1)

    def test_callable_interface(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)
        result = generalizer(27)
        assert result == "25-34"

    def test_explicit_level_overrides_current(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)
        result = generalizer.generalize(27, level=3)
        assert result == "adult"
        assert generalizer.current_level == 1

    def test_max_level(self):
        age_generalizer = GeneralizationStrategy.create_age_generalizer()
        assert age_generalizer.max_level == 4

        ip_generalizer = GeneralizationStrategy.create_ip_generalizer()
        assert ip_generalizer.max_level == 4

        zip_generalizer = GeneralizationStrategy.create_zipcode_generalizer(
            zipcode_length=6
        )
        assert zip_generalizer.max_level == 6

    def test_generalize_to_highest_level(self):
        age_generalizer = GeneralizationStrategy.create_age_generalizer()
        age_generalizer.set_level(4)
        assert age_generalizer.generalize(27) == "*"

        zip_generalizer = GeneralizationStrategy.create_zipcode_generalizer(
            zipcode_length=6
        )
        zip_generalizer.set_level(6)
        assert zip_generalizer.generalize("100081") == "******"

    def test_numeric_field_type(self):
        generalizer = GeneralizationStrategy(field_type="numeric")
        assert generalizer.generalize(25, level=1) == "20-29"

    def test_category_field_type(self):
        generalizer = GeneralizationStrategy(field_type="category")
        assert generalizer.generalize("male", level=1) == "male"


class TestGeneralizationStrategyDynamicAgeStep:
    def test_create_age_generalizer_with_step_5(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(
            default_level=1, step_years=5
        )
        assert generalizer.current_level == 1
        assert generalizer.generalize(27) == "25-30"
        assert generalizer.generalize(25) == "25-30"
        assert generalizer.generalize(29) == "25-30"

    def test_create_age_generalizer_with_step_5_level_2(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(
            default_level=2, step_years=5
        )
        assert generalizer.current_level == 2
        assert generalizer.generalize(27) == "20-30"
        assert generalizer.generalize(25) == "20-30"

    def test_create_age_generalizer_with_step_5_set_level(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(
            default_level=0, step_years=5
        )
        generalizer.set_level(1)
        assert generalizer.generalize(27) == "25-30"
        generalizer.set_level(3)
        assert generalizer.generalize(27) == "adult"

    def test_create_age_generalizer_without_step_uses_default(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)
        assert generalizer.generalize(27) == "25-34"

    def test_create_age_generalizer_with_step_10(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(
            default_level=1, step_years=10
        )
        assert generalizer.generalize(27) == "20-30"

    def test_create_age_generalizer_step_5_description(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(
            default_level=1, step_years=5
        )
        levels = generalizer.config.levels
        assert levels[1].description == "5-year ranges"
        assert levels[2].description == "10-year ranges"

    def test_create_age_generalizer_no_step_description(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)
        levels = generalizer.config.levels
        assert levels[1].description == "10-year ranges"
        assert levels[2].description == "20-year ranges"
