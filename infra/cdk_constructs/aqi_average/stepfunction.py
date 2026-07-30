from typing import Any
from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_scheduler as scheduler,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from .aqi_report_generator import AQIReportGeneratorConstruct
from .aqi_athena import AQIAthenaConstruct

class AQIStepFunctionConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        aqi_report_generator: AQIReportGeneratorConstruct,
        aqi_athena: AQIAthenaConstruct,
        **kwargs: Any,
    ):
        super().__init__(scope, id, **kwargs)

        # Creating tasks and handling the input/outpot logic of stepfunction
        self.prepare_data_lambda_task = tasks.LambdaInvoke(
            self,
            "ExecutePrepare",
            lambda_function=aqi_report_generator.prepare_data_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "athena_result_key": sfn.JsonPath.string_at(
                        "$.QueryExecution.ResultConfiguration.OutputLocation"
                    )
                }
            ),
            result_selector={
                "statusCode": sfn.JsonPath.number_at("$.Payload.statusCode"),
                "data_for_llm": sfn.JsonPath.string_at("$.Payload.data_for_llm"),
            },
            result_path="$.lambda_output",
        )

        self.save_report_lambda_task = tasks.LambdaInvoke(
            self,
            "SaveReport",
            lambda_function=aqi_report_generator.save_report_lambda,
            payload=sfn.TaskInput.from_object(
                {"summary_text": sfn.JsonPath.string_at("$.summary_text")}
            ),
        )

        # The flow of the stepfunction
        self.stepfunction_flow = (
            sfn.Chain.start(aqi_athena.athena_query_task)
            .next(self.prepare_data_lambda_task)
            .next(aqi_report_generator.llm_generate_report_task)
            .next(self.save_report_lambda_task)
        )

        # Creating stepmachine
        self.state_machine = sfn.StateMachine(
            self,
            "Machine",
            definition_body=sfn.DefinitionBody.from_chainable(self.stepfunction_flow),
            timeout=Duration.minutes(15),
        )

        # Event scheduler to invoke the state machine at midnight
        self.scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )

        self.state_machine.grant_start_execution(self.scheduler_role)

        self.daily_midnight_schedule = scheduler.CfnSchedule(
            self,
            "DailyMidnightSchedule",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="OFF"
            ),
            schedule_expression="cron(0 0 * * ? *)",
            target=scheduler.CfnSchedule.TargetProperty(
                arn=self.state_machine.state_machine_arn,
                role_arn=self.scheduler_role.role_arn,
            ),
        )

        # Giving state machine role for invoking LLM
        self.state_machine.add_to_role_policy(aqi_report_generator.invoke_llm_role)
