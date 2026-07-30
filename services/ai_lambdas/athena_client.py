import time
import boto3
import os
import logging

logger = logging.getLogger(__name__)

ATHENA_OUTPUT_BUCKET = os.environ.get(
    "ATHENA_OUTPUT_BUCKET",
    "s3://aws-internship-pollution-387075079166-eu-central-1-an/athena-ai-results/",
)
MAX_WAIT_SECONDS = int(os.environ.get("MAX_WAIT_SECONDS", 60))
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", 2))


class AthenaClient:
    def __init__(self):
        self.client = boto3.client("athena")

    def run_query(
        self, database: str, table: str, query: str
    ) -> tuple[list[str], list[dict]]:

        execution_id = self._start_query(database, table, query)
        logger.info(f"Athena QueryExecutionId: {execution_id}")

        self._wait_for_query(execution_id)
        columns, rows = self._fetch_results(execution_id)

        logger.info(f"Query zavrseno. Broj redova: {len(rows)}")
        return execution_id, columns, rows

    def _start_query(self, database: str, table: str, query: str) -> str:
        """Pokrece Athena query i vraca QueryExecutionId."""
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": database},
            ResultConfiguration={"OutputLocation": ATHENA_OUTPUT_BUCKET},
        )
        return response["QueryExecutionId"]

    def _wait_for_query(self, execution_id: str) -> None:
        """
        Pollingom ceka dok Athena ne zavrsi query.
        Baca TimeoutError ili RuntimeError u slucaju problema.
        """
        elapsed = 0

        while elapsed < MAX_WAIT_SECONDS:
            response = self.client.get_query_execution(QueryExecutionId=execution_id)
            state = response["QueryExecution"]["Status"]["State"]

            if state == "SUCCEEDED":
                return
            elif state in ("FAILED", "CANCELLED"):
                reason = response["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Nepoznat razlog"
                )
                raise RuntimeError(f"Athena query {state}: {reason}")

            # RUNNING ili QUEUED — cekamo
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

        raise TimeoutError(
            f"Athena query nije zavrsio u roku od {MAX_WAIT_SECONDS} sekundi."
        )

    def _fetch_results(self, execution_id: str) -> tuple[list[str], list[dict]]:
        """
        Dohvata sve stranice rezultata iz Athene.

        Returns:
            (columns, rows)
        """
        columns: list[str] = []
        rows: list[dict] = []
        next_token = None
        first_page = True

        while True:
            kwargs = {"QueryExecutionId": execution_id, "MaxResults": 1000}
            if next_token:
                kwargs["NextToken"] = next_token

            response = self.client.get_query_results(**kwargs)
            result_set = response["ResultSet"]

            if first_page:
                columns = [
                    col["Label"]
                    for col in result_set["ResultSetMetadata"]["ColumnInfo"]
                ]
                data_rows = result_set["Rows"][1:]  # preskacemo header red
                first_page = False
            else:
                data_rows = result_set["Rows"]

            for row in data_rows:
                values = [field.get("VarCharValue", None) for field in row["Data"]]
                rows.append(dict(zip(columns, values)))

            next_token = response.get("NextToken")
            if not next_token:
                break

        return columns, rows
