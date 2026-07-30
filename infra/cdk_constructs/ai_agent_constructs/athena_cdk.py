from constructs import Construct
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    Duration,
    Aws,
)
from typing import Any


class AthenaQueryLambdaConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any):
        super().__init__(scope, construct_id, **kwargs)

        lambda_role = iam.Role(
            self,
            "AthenaQueryLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"  # CloudWatch Logs
                ),
            ],
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                    "athena:StopQueryExecution",
                ],
                resources=[
                    f"arn:aws:athena:{Aws.REGION}:{Aws.ACCOUNT_ID}:workgroup/primary"
                ],
            )
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:GetPartitions",
                ],
                resources=["*"],
            )
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetBucketLocation",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject",
                ],
                resources=[
                    f"arn:aws:s3:::aws-athena-query-results-{Aws.ACCOUNT_ID}-{Aws.REGION}",
                    f"arn:aws:s3:::aws-athena-query-results-{Aws.ACCOUNT_ID}-{Aws.REGION}/*",
                    "arn:aws:s3:::aws-internship-pollution-387075079166-eu-central-1-an",
                    "arn:aws:s3:::aws-internship-pollution-387075079166-eu-central-1-an/*",
                ],
            )
        )

        self.athena_lambda = lambda_.Function(
            self,
            "AthenaQueryLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function_athena.lambda_handler",
            code=lambda_.Code.from_asset("./services/ai_lambdas/"),
            role=lambda_role,
            timeout=Duration.seconds(60),  
            memory_size=256,
        )
        self.function = self.athena_lambda
