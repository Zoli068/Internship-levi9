from constructs import Construct
from .storage import MedallionStorageConstruct
from .import_s3 import MedallionImportS3Construct
from .gold_etl import MedallionGoldETLConstruct
from .open_meteo_pipeline import OpenMeteoPipelineConstruct
from .stepfunction_lambda import StepFunctionLambdaConstruct
from .bronze_sensor_etl import MedallionBronzeSensorETLConstruct
from .glue_jobs_workflow import MedallionWorkflowConstruct
from typing import Any


class MedallionOrchestratorConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs: Any,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.storage = MedallionStorageConstruct(self, "Storage")

        self.import_s3 = MedallionImportS3Construct(self, "ImportS3", self.storage)

        self.bronze_to_silver_sensor_etl_job = MedallionBronzeSensorETLConstruct(
            self, "BronzeToSilverSensorETL", self.storage
        )

        self.openmeteo_pipeline = OpenMeteoPipelineConstruct(
            self, "OpenMeteoPipeline", self.storage
        )

        self.stepfunction_lambda = StepFunctionLambdaConstruct(
            self,
            "StepFunctionLambda",
            self.openmeteo_pipeline.access_openmeteo_lambda,
            self.import_s3.object_importer_lambda,
        )

        self.gold_etl_job = MedallionGoldETLConstruct(self, "GoldETL", self.storage)

        self.pipeline_workflow = MedallionWorkflowConstruct(
            self,
            "PipelineWorkflow",
            sensor_silver_glue_job=self.bronze_to_silver_sensor_etl_job.glue_job_bronze_to_silver_sensor,
            openmeteo_silver_glue_job=self.openmeteo_pipeline.air_quality_glue_job,
            gold_glue_job=self.gold_etl_job.glue_job_gold,
        )
