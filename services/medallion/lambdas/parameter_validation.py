import re
from datetime import datetime

SQS_NAME_REGEX = r"^[a-zA-Z0-9_-]{1,80}$"
BUCKET_NAME_REGEX = r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"
ILLEGAL_CHARACTER_COMBINATIONS_IN_NAME = ["..", ".-", "-."]


def validate_s3_name(name: str) -> str:

    if not isinstance(name, str) or not name.strip():
        raise ValueError("CRITICAL: Bucket name must be a non-empty string!")

    name = name.strip()

    if not re.match(BUCKET_NAME_REGEX, name):
        raise ValueError(f"CRITICAL: Bucket name '{name} is invalid")

    if any(
        combinations in name for combinations in ILLEGAL_CHARACTER_COMBINATIONS_IN_NAME
    ):
        raise ValueError(f"CRITICAL: Bucket name '{name} is invalid")

    return name


def validate_s3_prefix(prefix: str) -> str:

    if not isinstance(prefix, str):
        raise ValueError("CRITICAL: S3 Prefix must be a string!")

    prefix = prefix.strip()

    if prefix == "":
        return prefix

    if prefix.startswith("/"):
        prefix = prefix.lstrip("/")

    if not prefix.endswith("/"):
        prefix = prefix + "/"

    if len(prefix) > 900:
        raise ValueError("CRITICAL: S3 Prefix is too long!")

    return prefix


def validate_parse_datetime(datetime_str: str) -> datetime:

    if not isinstance(datetime_str, str):
        raise TypeError("CRITICAL: Datetime parameter must be a string!")

    datetime_str = datetime_str.strip()

    if datetime_str == "":
        return datetime.min

    try:
        return datetime.fromisoformat(datetime_str)
    except ValueError:
        raise ValueError(
            f"CRITICAL: Datetime string '{datetime_str}' is not in valid ISO format!"
        )
