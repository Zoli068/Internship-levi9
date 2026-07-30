import json
import logging
from athena_client import AthenaClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

athena = AthenaClient()


def lambda_handler(event, context):
    """
    Univerzalna Lambda za izvrsavanje Athena upita.

    Ocekivani input (event):
    {
        "database": "silver",
        "table":    "air_quality",
        "query":    "SELECT * FROM {table} WHERE date = '{date}'"
    }

    Output (uspjesan):
    {
        "statusCode": 200,
        "body": {
            "columns":            ["col1", "col2", ...],
            "rows":               [{"col1": "val1", ...}, ...],
            "row_count":          42,
            "query_execution_id": "abc-123"
        }
    }
    """
    if "actionGroup" in event:
        return _handle_bedrock_event(event)
    try:
        database, table, query = _parse_and_validate(event)
    except ValueError as e:
        return _error_response(400, str(e))

    logger.info(f"Pokrecemo query na bazi '{database}': {query[:200]}...")

    try:
        execution_id, columns, rows = athena.run_query(database, table, query)
    except TimeoutError as e:
        return _error_response(504, str(e))
    except RuntimeError as e:
        return _error_response(500, str(e))
    except Exception as e:
        logger.error(f"Neocekivana greska: {e}")
        return _error_response(500, "Neocekivana greska.", str(e))

    return {
        "statusCode": 200,
        "body": {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "query_execution_id": execution_id,
        },
    }


def _handle_bedrock_event(event):
    """Adapter za Bedrock Agent event format."""
    action_group = event["actionGroup"]
    function_name = event["function"]
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    database = parameters.get("database", "")
    table = parameters.get("table", "")
    query = parameters.get("query", "")

    try:
        database, table, query = _parse_and_validate(
            {
                "database": database,
                "table": table,
                "query": query,
            }
        )
        execution_id, columns, rows = athena.run_query(database, table, query)
        result = json.dumps(
            {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "query_execution_id": execution_id,
            }
        )
    except ValueError as e:
        result = json.dumps({"error": str(e)})
    except Exception as e:
        result = json.dumps({"error": str(e)})

    # Obavezan Bedrock response format
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {"responseBody": {"TEXT": {"body": result}}},
        },
    }


def _parse_and_validate(event: dict) -> tuple[str, str, str]:
    """Validira event i vraca (database, query) sa ubacenim {table} placeholderom."""

    database = event.get("database", "").strip()
    table = event.get("table", "").strip()
    query = event.get("query", "").strip()

    if not database:
        raise ValueError("Parametar 'database' je obavezan.")
    if not table:
        raise ValueError("Parametar 'table' je obavezan.")
    if not query:
        raise ValueError("Parametar 'query' je obavezan.")

    # Zamjena {table} u query-ju
    query = query.replace("{table}", table)

    return database, table, query


def _error_response(status_code: int, error: str, details: str = None) -> dict:
    body = {"error": error}
    if details:
        body["details"] = details
    return {"statusCode": status_code, "body": body}
