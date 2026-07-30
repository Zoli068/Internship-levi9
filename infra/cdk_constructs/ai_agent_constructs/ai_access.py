from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigatewayv2 as apigwv2,
)
from constructs import Construct
from .ai_agent import BedrockAgentConstruct

class AiAgentAccessConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        ai_agent: BedrockAgentConstruct,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ai_access_lambda = _lambda.Function(
            self,
            "AiAccessLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ai_access_lambda.handler",
            code=_lambda.Code.from_asset("./services/ai_lambdas"),
            timeout=Duration.seconds(300),
            environment={
                "BEDROCK_AGENT_ID": ai_agent.agent_id,
                "BEDROCK_AGENT_ALIAS_ID": "TSTALIASID", 
            },
        )

        self.ai_access_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeAgent"], resources=["*"])
        )

        self.websocket_api = apigwv2.WebSocketApi(
            self, "AiWSApi", api_name="AiWSGateway"
        )

        # Gateway connect to our async lambda
        self.cfn_integration = apigwv2.CfnIntegration(
            self,
            "AiLambdaAsynIntegration",
            api_id=self.websocket_api.api_id,
            integration_type="AWS_PROXY",
            integration_uri=f"arn:aws:apigateway:{Stack.of(self).region}:lambda:path/2015-03-31/functions/{self.ai_access_lambda.function_arn}/invocations",
            integration_method="POST",
            request_parameters={
                "integration.request.header.X-Amz-Invocation-Type": "'Event'"
            },
        )

        apigwv2.CfnRoute(
            self,
            "DefaultRoute",
            api_id=self.websocket_api.api_id,
            route_key="$default",
            target=f"integrations/{self.cfn_integration.ref}",
        )

        stage = apigwv2.WebSocketStage(
            self,
            "APIstage",
            web_socket_api=self.websocket_api,
            stage_name="api",
            auto_deploy=True,
        )

        # Our lambda is async so he will send back manually the response based on the url + connectioID
        self.ai_access_lambda.add_environment(
            "CALLBACK_URL",
            f"https://{self.websocket_api.api_id}.execute-api.{Stack.of(self).region}.amazonaws.com/{stage.stage_name}",
        )

        self.ai_access_lambda.add_permission(
            "AllowApiGatewayInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=f"arn:aws:execute-api:{Stack.of(self).region}:{Stack.of(self).account}:{self.websocket_api.api_id}/*",
        )

        self.ai_access_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[
                    f"arn:aws:execute-api:{Stack.of(self).region}:{Stack.of(self).account}:{self.websocket_api.api_id}/{stage.stage_name}/*"
                ],
            )
        )
