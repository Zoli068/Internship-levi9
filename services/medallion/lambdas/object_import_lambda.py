import os
import boto3
from typing import Any
from datetime import datetime
from parameter_validation import validate_s3_name, validate_s3_prefix
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")

# --- Environment Variables Configuration ---
# DESTINATION_BUCKET_NAME - The target S3 bucket where we want to extract object.
# SOURCE_BUCKET_NAME - The source S3 bucket from which we want to extract object.
# DESTINATION_PREFIX - The folder (prefix) inside the target bucket where the object will be saved.
# SOURCE_PREFIX      - The folder (prefix) inside the source bucket from which object should be copied.

DEST_BUCKET_NAME = validate_s3_name(os.environ.get("DESTINATION_BUCKET_NAME", ""))
SOURCE_BUCKET_NAME = validate_s3_name(os.environ.get("SOURCE_BUCKET_NAME", ""))
dest_prefix = validate_s3_prefix(os.environ.get("DESTINATION_PREFIX", ""))
source_prefix = validate_s3_prefix(os.environ.get("SOURCE_PREFIX", ""))

formatted_date = datetime.now().strftime("%d-%m-%Y")
dest_prefix += formatted_date + "/"
source_prefix += formatted_date + "/"


def lambda_handler(event: dict[str, Any], _context: Any) -> None:

    copied_count = 0

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=SOURCE_BUCKET_NAME, Prefix=source_prefix)

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                obj_key = obj["Key"]

                if obj_key.endswith("/"):
                    continue

                if source_prefix and obj_key.startswith(source_prefix):
                    prefix_key = obj_key[len(source_prefix) :]
                else:
                    prefix_key = obj_key

                dest_key = f"{dest_prefix}{prefix_key}" if dest_prefix else prefix_key

                copy_source = {"Bucket": SOURCE_BUCKET_NAME, "Key": obj_key}

                try:
                    s3_client.head_object(Bucket=DEST_BUCKET_NAME, Key=dest_key)

                    continue
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        try:
                            s3_client.copy_object(
                                Bucket=DEST_BUCKET_NAME,
                                Key=dest_key,
                                CopySource=copy_source,
                            )
                            copied_count += 1
                        except ClientError as copy_err:
                            raise Exception(
                                f"Lambda failed to copy object {obj_key}: {str(copy_err)}"
                            )
                    else:
                        raise Exception(
                            f"Lambda failed during head_object check: {str(e)}"
                        )

            print(f"Export results: Number of objects copied: {copied_count}")

    except Exception as e:
        raise Exception(f"Lambda failed to process object: {str(e)}")
