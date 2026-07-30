from typing import Any
from aws_cdk import Stack
from constructs import Construct
from cdk_constructs.medallion.orchestrator import MedallionOrchestratorConstruct
from cdk_constructs.ai_agent_constructs.ai_orchestrator import AiOrchestrator
from cdk_constructs.aqi_average.orchestrator import AQIOrchestratorConstruct
from cdk_constructs.visual_interface.visual_interface import VisualInterfaceConstruct


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.medallion = MedallionOrchestratorConstruct(
            self,
            "Medallion",
        )

        self.aqi_reporter = AQIOrchestratorConstruct(
            self, "AQI", self.medallion.storage
        )

        self.ai_orchestrator = AiOrchestrator(self, "AiAgentTest")

        self.visual_interface = VisualInterfaceConstruct(
            self, "VisualInterface", self.medallion.storage
        )
