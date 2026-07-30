from constructs import Construct

from .ai_agent import BedrockAgentConstruct
from .athena_cdk import AthenaQueryLambdaConstruct
from .ai_access import AiAgentAccessConstruct

class AiOrchestrator(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.athena_lambda = AthenaQueryLambdaConstruct(
            self,
            "AthenaQueryLambda",
        )

        self.agent = BedrockAgentConstruct(
            self,
            "BedrockAgent",
            athena_lambda=self.athena_lambda,
        )

        self.ai_access = AiAgentAccessConstruct(
            self,
            "Access",
            self.agent
        )
