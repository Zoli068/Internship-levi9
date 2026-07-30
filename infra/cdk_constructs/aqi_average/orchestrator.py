from typing import Any
from constructs import Construct
from .aqi_athena import AQIAthenaConstruct
from .stepfunction import AQIStepFunctionConstruct
from .aqi_report_generator import AQIReportGeneratorConstruct
from ..medallion.storage import MedallionStorageConstruct

class AQIOrchestratorConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storage_construct: MedallionStorageConstruct,
        **kwargs: Any,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.aqi_athena = AQIAthenaConstruct(self, "Athena", storage_construct)

        self.aqi_report_generator = AQIReportGeneratorConstruct(
            self, "Report", storage_construct
        )

        self.step_functions = AQIStepFunctionConstruct(
            self, "StepFunction", self.aqi_report_generator, self.aqi_athena
        )
