import io
import csv
import json
import boto3
from typing import Any
from urllib.parse import urlparse

s3 = boto3.client("s3")


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:

    s3_uri = event["athena_result_key"]

    parsed = urlparse(s3_uri)

    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    response = s3.get_object(Bucket=bucket, Key=key)

    csv_raw_data = response["Body"].read().decode("utf-8")

    csv_file = io.StringIO(csv_raw_data)
    reader = csv.DictReader(csv_file)
    json_data = [row for row in reader]

    return {"statusCode": 200, "data_for_llm": json.dumps(json_data)}
