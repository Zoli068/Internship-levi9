import os
import json
import boto3
from typing import Any
from botocore.exceptions import ClientError
from parameter_validation import validate_s3_name, validate_s3_prefix

s3_client = boto3.client("s3")

BUCKET_NAME = validate_s3_name(os.environ.get("STATIC_WEBSITE_BUCKET_NAME", ""))
BUCKET_PREFIX = validate_s3_prefix(os.environ.get("STATIC_WEBSITE_PREFIX", ""))


def lambda_handler(event: dict[str, Any], _context: Any) -> None:

    summary_text = event.get("summary_text", {}).get("text", "")

    if not summary_text:
        raise ValueError("Model output ('content') is empty or missing from the event.")

    report_data = {"text": summary_text}

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=BUCKET_PREFIX + "report.json",
            Body=json.dumps(report_data, ensure_ascii=False),
            ContentType="application/json",
        )

        print("Report successfully generated!")

    except ClientError as e:
        raise RuntimeError(
            f"Generated report.json cannot be added to the bucket: {e}"
        ) from e
