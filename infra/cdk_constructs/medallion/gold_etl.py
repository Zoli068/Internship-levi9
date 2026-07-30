from aws_cdk import (
    aws_glue as glue,
    aws_s3_assets as s3_assets,
    aws_iam as iam,
    Stack,
)

import os
from constructs import Construct
from .storage import MedallionStorageConstruct


class MedallionGoldETLConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storageConstruct: MedallionStorageConstruct,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Grabing  stack context to get region and account for IAM policy to acess Glue Catalog DB and tables inside of it
        _stack = Stack.of(self)

        # Local script location
        self.script_path_gold_etl = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../services/medallion/glue_jobs/gold.py",
            )
        )

        # Uploading script to S3
        self.script_asset = s3_assets.Asset(
            self, "ETLGoldAsset", path=self.script_path_gold_etl
        )

        # Execution Role with Standard Glue Permissions
        self.glue_role_gold = iam.Role(
            self,
            "RoleGold",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )

        # Granting Glue permission to read uploaded execution script on S3, CDK auto makes IAM statement
        self.script_asset.grant_read(self.glue_role_gold)

        # Grant Glue full read/write access to Bucket
        storageConstruct.medallion_bucket.grant_read_write(self.glue_role_gold)

        # Glue job config

        self.glue_job_gold = glue.CfnJob(
            self,
            "JobGold",
            name="gold-etl-pollution",
            role=self.glue_role_gold.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",  # for apache spark job
                script_location=self.script_asset.s3_object_url,  # script location in s3
            ),
            glue_version="5.0",
            number_of_workers=2,
            worker_type="G.1X",
            max_retries=0,
            timeout=20,  # mins
            execution_class="FLEX",
            default_arguments={
                "--job-bookmark-option": "job-bookmark-enable",  # glue only takes new data by checking with bookmark
                "--SILVER_SRC_SENSOR": f"s3://{storageConstruct.medallion_bucket.bucket_name}/silver/sensor",
                "--SILVER_SRC_OPEN": f"s3://{storageConstruct.medallion_bucket.bucket_name}/silver/open_meteo",
                "--GOLD_DEST": f"s3://{storageConstruct.medallion_bucket.bucket_name}/gold/aqi",
            },
        )
