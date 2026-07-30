from constructs import Construct
from aws_cdk import (
    aws_s3 as s3,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from ..medallion.storage import MedallionStorageConstruct
from prompts_queries.avg_aqi.avg_aqi_athena_querry import AVG_AQI_QUERRY


class AQIAthenaConstruct(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storage_Construct: MedallionStorageConstruct,
    ) -> None:
        super().__init__(scope, construct_id)

        self.athena_query_task = tasks.AthenaStartQueryExecution(
            self,
            "CalculateAVG",
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            query_string=AVG_AQI_QUERRY.format(
                table_name=storage_Construct.gold_table_name
            ),
            query_execution_context=tasks.QueryExecutionContext(
                database_name=storage_Construct.glue_database_name
            ),
            work_group=storage_Construct.aqi_workgroup,
            result_configuration=tasks.ResultConfiguration(
                output_location=s3.Location(
                    bucket_name=storage_Construct.medallion_bucket.bucket_name,
                    object_key=storage_Construct.avg_calculation_folder,
                )
            ),
        )
