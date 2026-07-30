import os
import json
import urllib.request
import boto3
from typing import Any
from datetime import datetime, timezone

s3_client = boto3.client("s3")


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:

    bucket_name = os.environ.get("BUCKET_NAME")
    prefix = os.environ.get("BRONZE_PREFIX")
    now = datetime.now(timezone.utc)
    date_folder = now.strftime("%d-%m-%Y")  # izmenjen format

    current_time_str = now.strftime("%H-%M")

    file_name = f"weather_{current_time_str}.json"

    s3_key = f"{prefix}{date_folder}/{file_name}"

    lat = os.environ.get("LATITUDE", "45.2517")
    lon = os.environ.get("LONGITUDE", "19.8369")

    url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={lat}&longitude={lon}&"
        f"current=carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
    )

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        current_data = data.get("current", {})

        data_to_save = {
            "ingested_at": now.isoformat(), 
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "time": current_data.get("time"),  
            "carbon_monoxide": current_data.get("carbon_monoxide"),
            "nitrogen_dioxide": current_data.get("nitrogen_dioxide"),
            "sulphur_dioxide": current_data.get("sulphur_dioxide"),
            "ozone": current_data.get("ozone"),
        }

        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data_to_save, indent=4),
            ContentType="application/json",
        )

        print(
            f"Uspešno sačuvani podaci na S3: {s3_key} za lokaciju lat: {lat}, lon: {lon}"
        )
        return {
            "statusCode": 200,
            "body": json.dumps("Podaci uspešno povučeni i sačuvani!"),
        }

    except Exception as e:
        print(
            f"Greška pri preuzimanju/upisu podataka u vreme {current_time_str}. Poruka: {str(e)}"
        )
        return {"statusCode": 500, "body": json.dumps(f"Greška: {str(e)}")}
