from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_iam as iam,
)
from typing import Any
from constructs import Construct
from ..medallion.storage import MedallionStorageConstruct
from prompts_queries.avg_aqi.avg_aqi_llm_request import (
    LLM_STATE,
)

class AQIReportGeneratorConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        storageConstruct: MedallionStorageConstruct,
        **kwargs: Any,
    ):
        super().__init__(scope, id, **kwargs)

        self.static_webhost_prefix = "aqi_average/"

        # Lambda for accessing the Athena AQI Average result
        self.prepare_data_lambda = _lambda.Function(
            self,
            "PrepareLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="prompt_prepare_lambda.lambda_handler",
            code=_lambda.Code.from_asset("./services/aqi_average/lambdas"),
            timeout=Duration.seconds(150),
        )

        storageConstruct.medallion_bucket.grant_read(
            self.prepare_data_lambda, storageConstruct.avg_calculation_folder + "/*"
        )

        # Generating report, the LLM response to be saved as index.html
        self.save_report_lambda = _lambda.Function(
            self,
            "GenerateIndexLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="generate_report_lambda.lambda_handler",
            code=_lambda.Code.from_asset("./services/aqi_average/lambdas"),
            timeout=Duration.seconds(30),
            environment={
                "STATIC_WEBSITE_BUCKET_NAME": storageConstruct.static_webhost_bucket.bucket_name,
                "STATIC_WEBSITE_PREFIX": self.static_webhost_prefix,
            },
        )

        storageConstruct.static_webhost_bucket.grant_write(
            self.save_report_lambda, self.static_webhost_prefix + "*"
        )

        # The task for generating report with LLM
        self.llm_generate_report_task = sfn.CustomState(
            self,
            "InvokeLLM",
            state_json=LLM_STATE,
        )

        # Policy for invoking the model
        self.invoke_llm_role = iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                "arn:aws:bedrock:eu-central-1:*:inference-profile/eu.amazon.nova-lite-v1:0",
                "arn:aws:bedrock:*::foundation-model/amazon.nova-lite-v1:0",
            ],
        )
