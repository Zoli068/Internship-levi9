from aws_cdk import (
    aws_glue as glue,
    aws_iam as iam,
    aws_s3_assets as s3_assets,
)
import os
from constructs import Construct
from .storage import MedallionStorageConstruct
from typing import Any


class MedallionBronzeSensorETLConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storageConstruct: MedallionStorageConstruct,
        **kwargs: Any,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.script_path_bronze_sensor = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../services/medallion/glue_jobs/sensor_bronze.py",
            )
        )

        self.script_asset = s3_assets.Asset(
            self, "ETLAsset", path=self.script_path_bronze_sensor
        )

        self.glue_role_bronze_sensor = iam.Role(
            self,
            "Role",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )

        self.script_asset.grant_read(self.glue_role_bronze_sensor)

        #  Grant access to  data bucket layers so the script can read/write data
        self.glue_role_bronze_sensor.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:aws:s3:::{storageConstruct.medallion_bucket.bucket_name}",
                    f"arn:aws:s3:::{storageConstruct.medallion_bucket.bucket_name}/*",
                ],
            )
        )

        # Glue Job
        self.glue_job_bronze_to_silver_sensor = glue.CfnJob(
            self,
            "Job",
            name="bronze-to-silver-senzor-etl",
            role=self.glue_role_bronze_sensor.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",  # for apache spark job
                script_location=self.script_asset.s3_object_url,
                python_version="3",
            ),
            glue_version="5.0",
            number_of_workers=2,
            worker_type="G.1X",
            # Additonal lowcost stuff
            max_retries=0,  # prevents paying for second run if script crashes on a bug
            timeout=20,  # defense against runaway bills
            execution_class="FLEX",
            default_arguments={
                "--job-bookmark-option": "job-bookmark-enable",  # glue saves which s3 objects it has read during run so on next run it will procces only new files
                "--BRONZE_SRC": f"s3://{storageConstruct.medallion_bucket.bucket_name}/bronze/sensor",
                "--SILVER_DEST": f"s3://{storageConstruct.medallion_bucket.bucket_name}/silver/sensor",
            },
        )
