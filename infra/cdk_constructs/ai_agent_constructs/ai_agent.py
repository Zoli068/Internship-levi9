from aws_cdk import Stack, aws_iam as iam, aws_bedrock as bedrock, aws_lambda as lambda_
from constructs import Construct
from .guardrails_agent import create_sql_guardrail

from prompts_queries.ai_agents.ai_agent_prompts import (
    SQL_QUERIES_DESCRIPTION,
    AGENT_DESCRIPTION,
    TABLE_DESCRIPTION,
    AGENT_INSTRUCTION,
    DATABASE_DESCRIPTION,
)

NOVA_LITE_MODEL_ID = "eu.amazon.nova-pro-v1:0"

class BedrockAgentConstruct(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        athena_lambda: lambda_.Function,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.athena_lambda = athena_lambda
        sql_guardrail, sql_version = create_sql_guardrail(self)

        agent_role = iam.Role(
            self,
            "PrazanAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0",
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:inference-profile/eu.amazon.nova-pro-v1:0",
                ],
            )
        )
        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{Stack.of(self).region}:{Stack.of(self).account}:function:athena-query-lambda2"
                ],
            )
        )
        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:guardrail/{sql_guardrail.attr_guardrail_id}"
                ],
            )
        )
        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0",
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:inference-profile/eu.amazon.nova-pro-v1:0",
                ],
            )
        )

        self.agent = bedrock.CfnAgent(
            self,
            "MyPollutionAgent",
            agent_name="PollutionAgent",
            foundation_model=NOVA_LITE_MODEL_ID,
            agent_resource_role_arn=agent_role.role_arn,
            instruction=AGENT_INSTRUCTION,
            description="Pollution Agent",
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="AthenaQueryActionGroup",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.athena_lambda.function.function_arn,
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="execute_athena_query",
                                description=(AGENT_DESCRIPTION),
                                parameters={
                                    "database": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description=(DATABASE_DESCRIPTION),
                                        required=True,
                                    ),
                                    "table": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description=(TABLE_DESCRIPTION),
                                        required=True,
                                    ),
                                    "query": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description=(SQL_QUERIES_DESCRIPTION),
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                )
            ],
            auto_prepare=True,
            guardrail_configuration=bedrock.CfnAgent.GuardrailConfigurationProperty(
                guardrail_identifier=sql_guardrail.attr_guardrail_id,
                guardrail_version=sql_version.attr_version,
            ),
        )

        self.athena_lambda.athena_lambda.add_permission(
            "AllowBedrockAgent",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.agent.attr_agent_arn,
        )

        self.agent_id = self.agent.attr_agent_id
