import pytest
from datetime import datetime
from services.medallion.lambdas.parameter_validation import (
    validate_s3_name,
    validate_s3_prefix,
    validate_parse_datetime,
)


@pytest.mark.parametrize(
    "valid_name",
    [
        "my-bucket-123",
        "valid.bucket.name",
        " test-with-whitespaces ",
    ],
)
def test_validate_s3_name_success(valid_name: str) -> None:
    assert validate_s3_name(valid_name) == valid_name.strip()


@pytest.mark.parametrize(
    "invalid_name, expected_error",
    [
        ("", "must be a non-empty string"),
        ("   ", "must be a non-empty string"),
        (12345, "must be a non-empty string"),
        ("Moj-Bucket-UpperCase-Letters", "is invalid"),
        ("a..b", "is invalid"),
        ("a.-b", "is invalid"),
        ("-bucket-starts-with-dash", "is invalid"),
    ],
)
def test_validate_s3_name_failures(invalid_name: str, expected_error: str) -> None:
    with pytest.raises(ValueError, match=expected_error):
        validate_s3_name(invalid_name)


@pytest.mark.parametrize(
    "input_prefix, expected_output",
    [
        ("", ""),
        ("   ", ""),
        ("folder/subfolder", "folder/subfolder/"),
        ("/remove-start/", "remove-start/"),
        ("correct/prefix/", "correct/prefix/"),
    ],
)
def test_validate_s3_prefix_success(input_prefix: str, expected_output: str) -> None:
    assert validate_s3_prefix(input_prefix) == expected_output


def test_validate_s3_prefix_too_long() -> None:
    long_prefix = "a" * 901
    with pytest.raises(ValueError, match="S3 Prefix is too long"):
        validate_s3_prefix(long_prefix)


def test_validate_parse_datetime_empty() -> None:
    assert validate_parse_datetime("") == datetime.min
    assert validate_parse_datetime("   ") == datetime.min


@pytest.mark.parametrize(
    "valid_iso, expected_dt",
    [
        ("2026-05-21T15:30:00", datetime(2026, 5, 21, 15, 30, 0)),
        ("2025-12-31", datetime(2025, 12, 31, 0, 0, 0)),
    ],
)
def test_validate_parse_datetime_success(valid_iso: str, expected_dt: datetime) -> None:
    assert validate_parse_datetime(valid_iso) == expected_dt


@pytest.mark.parametrize(
    "invalid_iso",
    [
        "21-05-2026",
        "2026/05/21 15:30:00",
        "not-a-date",
    ],
)
def test_validate_parse_datetime_failures(invalid_iso: str) -> None:
    with pytest.raises(ValueError, match="is not in valid ISO format"):
        validate_parse_datetime(invalid_iso)
