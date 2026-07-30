from aws_cdk import (
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_glue as glue,
)
from constructs import Construct
from typing import Any


class MedallionWorkflowConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        sensor_silver_glue_job: glue.CfnJob,
        openmeteo_silver_glue_job: glue.CfnJob,
        gold_glue_job: glue.CfnJob,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # 1. Task Glue Job Sensor
        self.bronze_to_silver_sensor_task = tasks.GlueStartJobRun(
            self,
            "SubmitBronzeToSilverSensorJob",
            glue_job_name=sensor_silver_glue_job.name,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # wait for it to finish
        )

        # 1.1 Task Glue job OPEN-METEO
        self.open_meteo_task = tasks.GlueStartJobRun(
            self,
            "SubmitBronzeToSilverOpenMeteoJob",
            glue_job_name=openmeteo_silver_glue_job.name,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # wait for it to finish
        )

        # 2. Defining Gold Glue job Task
        self.gold_task = tasks.GlueStartJobRun(
            self,
            "SubmitGoldETLJobRun",
            glue_job_name=gold_glue_job.name,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
        )

        # 3. Parallel State for Bronze integration into Silver
        self.parallel_ingestion = sfn.Parallel(self, "ParallelBronzeToSilverIngestion")
        self.parallel_ingestion.branch(self.bronze_to_silver_sensor_task)
        self.parallel_ingestion.branch(self.open_meteo_task)

        # 4. Chain to Gold
        self.pipeline_definition = self.parallel_ingestion.next(self.gold_task)

        # 5. State Machine
        self.state_machine = sfn.StateMachine(
            self,
            "MedallionPipelineStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(self.pipeline_definition),
        )

        # Event Bridge run Step function
        # Triggers at 00:00, 08:00, and 16:00 UTC every day
        self.pipeline_schedule = events.Rule(
            self,
            "PipelineScheduleRule",
            schedule=events.Schedule.cron(minute="0", hour="0,8,16"),
        )
        self.pipeline_schedule.add_target(targets.SfnStateMachine(self.state_machine))
