from aws_cdk import (
    Duration,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
)
from typing import Any
from constructs import Construct


class StepFunctionLambdaConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_openmeteo: _lambda.IFunction,
        lambda_sensor: _lambda.IFunction,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        task_1 = tasks.LambdaInvoke(
            self,
            "Invoke Open Meteo Lambda",
            lambda_function=lambda_openmeteo,
        )

        task_2 = tasks.LambdaInvoke(
            self,
            "Invoke Remote Bucket Lambda",
            lambda_function=lambda_sensor,
        )

        parallel_execution = sfn.Parallel(self, "Parallel Fetching")
        parallel_execution.branch(task_1)
        parallel_execution.branch(task_2)

        state_machine = sfn.StateMachine(
            self,
            "ParallelLambdaStateMachine",
            state_machine_name="Data-Fetch-Workflow",
            definition_body=sfn.DefinitionBody.from_chainable(parallel_execution),
            timeout=Duration.minutes(10),
        )

        scheduler_rule = events.Rule(
            self,
            "StepFunction15MinRule",
            schedule=events.Schedule.rate(Duration.minutes(60)),
            rule_name="Trigger-Workflow-Every-60-Min",
        )

        scheduler_rule.add_target(targets.SfnStateMachine(state_machine))
