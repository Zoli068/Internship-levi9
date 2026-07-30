from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3_assets as s3_assets,
)
from pathlib import Path
from constructs import Construct
from .storage import MedallionStorageConstruct


class OpenMeteoPipelineConstruct(Construct):

    def __init__(
        self,
        scope: Construct,
        id: str,
        storageConstruct: MedallionStorageConstruct,
    ) -> None:
        super().__init__(scope, id)

        root_path = Path(__file__).resolve().parents[2]
        # Pomera se jedan nivo iznad infra foldera, pa ulazi u services
        lambda_code_path = str(root_path.parent / "services" / "medallion" / "lambdas")
        etl_code_path = str(
            root_path.parent
            / "services"
            / "medallion"
            / "glue_jobs"
            / "etl_openmeteo_av.py"
        )
        latitude = "44.8125"
        longitude = "20.4612"
        bronze_prefix = "bronze/open_meteo/"
        silver_prefix = "silver/open_meteo/"

        # LAMBDA FUNKCIJA (Ingestion)
        self.access_openmeteo_lambda = _lambda.Function(
            self,
            "Lambda",
            function_name="open_meteo_lambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(lambda_code_path),
            handler="lambda_function_open_meteo.lambda_handler",
            timeout=Duration.seconds(30),
            environment={
                "BUCKET_NAME": storageConstruct.medallion_bucket.bucket_name,
                "BRONZE_PREFIX": bronze_prefix,
                "LATITUDE": latitude,
                "LONGITUDE": longitude,
            },
        )

        storageConstruct.medallion_bucket.grant_write(
            self.access_openmeteo_lambda, bronze_prefix + "*"
        )

        self.access_openmeteo_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        glue_job_role = iam.Role(
            self,
            "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )

        storageConstruct.medallion_bucket.grant_read(glue_job_role, bronze_prefix + "*")
        storageConstruct.medallion_bucket.grant_read_write(
            glue_job_role, silver_prefix + "*"
        )

        glue_script_asset = s3_assets.Asset(self, "GlueScriptAsset", path=etl_code_path)
        glue_script_asset.grant_read(glue_job_role)

        self.air_quality_glue_job = glue.CfnJob(
            self,
            "AirQualityGlueJob",
            name="etl_job_to_silver_pollution2",
            role=glue_job_role.role_arn,
            glue_version="4.0",
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                script_location=f"s3://{glue_script_asset.s3_bucket_name}/{glue_script_asset.s3_object_key}",
                python_version="3",
            ),
            default_arguments={
                "--job-language": "python",
                "--job-bookmark-option": "job-bookmark-enable",  # Popravka da glue job ne citao vec procitana fail-ove iz prethodnog run-a, vec samo nove file-ove
                "--BRONZE_PATH": f"s3://{storageConstruct.medallion_bucket.bucket_name}/{bronze_prefix}",
                "--SILVER_PATH": f"s3://{storageConstruct.medallion_bucket.bucket_name}/{silver_prefix}",
            },
            number_of_workers=2,
            worker_type="G.1X",
        )
