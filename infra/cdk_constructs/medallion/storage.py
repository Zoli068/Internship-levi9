from constructs import Construct
from aws_cdk import (
    aws_s3 as s3,
    custom_resources as cr,
    aws_iam as iam,
    RemovalPolicy,
    Aws,
    aws_athena as athena,
    aws_glue as glue,
)
from typing import Any


class MedallionStorageConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any):
        super().__init__(scope, construct_id, **kwargs)

        self.gold_table_name = "gold_aqi"
        self.aqi_workgroup = "aqi-workgroup"
        self.avg_calculation_folder = "gold/aqi_average"
        self.database_name = "medallion_pollution_lake_av"
        self.glue_database_name = "medallion_pollution_lake"
        self.source_bucket_name = "levi9-hack9-nineair-sensor-data"

        # Levi9 NineAir sensor bucket
        self.external_bucket = s3.Bucket.from_bucket_name(
            self,
            "ExternalBucket",
            self.source_bucket_name,
        )

        self.medallion_bucket = s3.Bucket.from_bucket_name(
            self,
            "MedallionBucket",
            "aws-internship-pollution-387075079166-eu-central-1-an",
        )

        # If we are creating this one, need to config static hosting
        self.static_webhost_bucket = s3.Bucket.from_bucket_name(
            self,
            "WebsiteBucket",
            "pollution-website",
        )

        # Mandatory Glue Database container where tables for gold schema will go
        self.glue_database = glue.CfnDatabase(
            self,
            "MedallionGluePollutionDatabase",
            catalog_id=Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=self.glue_database_name,
                description="Logical database for gold layer metrics",
            ),
        )

        # Schema of Gold folder for grafana
        self.gold_table = glue.CfnTable(
            self,
            "GoldAqiTable",
            database_name=self.glue_database.ref,
            catalog_id=Aws.ACCOUNT_ID,
            table_input=glue.CfnTable.TableInputProperty(
                name=self.gold_table_name,
                table_type="EXTERNAL_TABLE",
                parameters={"classification": "parquet"},
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        {"name": "location_name", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "hour_timestamp", "type": "timestamp"},
                        {"name": "avg_pm1_0", "type": "double"},
                        {"name": "avg_pm2_5", "type": "double"},
                        {"name": "avg_pm10_0", "type": "double"},
                        {"name": "carbon_monoxide", "type": "double"},
                        {"name": "nitrogen_dioxide", "type": "double"},
                        {"name": "ozone", "type": "double"},
                        {"name": "sulphur_dioxide", "type": "double"},
                        {"name": "pm25_index", "type": "double"},
                        {"name": "pm10_index", "type": "double"},
                        {"name": "no2_index", "type": "double"},
                        {"name": "so2_index", "type": "double"},
                        {"name": "ozone_index", "type": "double"},
                        {"name": "co_index", "type": "double"},
                        {"name": "final_aqi", "type": "double"},
                        {"name": "aqi_health_category", "type": "string"},
                        {"name": "dominant_pollutant", "type": "string"},
                    ],
                    location=f"s3://{self.medallion_bucket.bucket_name}/gold/aqi/",
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                    ),
                ),
                partition_keys=[{"name": "date", "type": "date"}],
            ),
        )

        crawler_role = iam.Role(
            self,
            "GlueCrawlerRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonS3ReadOnlyAccess"
                ),
            ],
        )

        crawler_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                resources=[
                    f"arn:aws:s3:::{self.medallion_bucket.bucket_name}",
                    f"arn:aws:s3:::{self.medallion_bucket.bucket_name}/*",
                ],
            )
        )

        self.glue_crawler = glue.CfnCrawler(
            self,
            "MedallionCrawlerCleanAV",
            role=crawler_role.role_arn,
            database_name=self.database_name,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    {
                        "path": f"s3://{self.medallion_bucket.bucket_name}/bronze/sensor/"
                    },
                    {
                        "path": f"s3://{self.medallion_bucket.bucket_name}/silver/open_meteo/"
                    },
                    {
                        "path": f"s3://{self.medallion_bucket.bucket_name}/silver/sensor/"
                    },
                    {"path": f"s3://{self.medallion_bucket.bucket_name}/gold/aqi/"},
                ]
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression="cron(30 1 * * ? *)"
            ),
        )

        cr.AwsCustomResource(
            self,
            "TriggerCrawlerOnDeploy",
            on_create=cr.AwsSdkCall(
                service="Glue",
                action="startCrawler",
                parameters={"Name": self.glue_crawler.ref},
                physical_resource_id=cr.PhysicalResourceId.of("TriggerCrawlerOnDeploy"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["glue:StartCrawler"],
                        resources=["*"],
                    )
                ]
            ),
        )

        # ATHENA Querry Bucket result
        self.athena_results_gold_bucket = s3.Bucket(
            self,
            "AthenaPollutionGoldQuerryResults",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.athena_gold_workgroup = athena.CfnWorkGroup(
            self,
            "AthenaPollutionWorkgroup",
            name=self.aqi_workgroup,
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{self.athena_results_gold_bucket.bucket_name}/results/",
                ),
                enforce_work_group_configuration=False,
                publish_cloud_watch_metrics_enabled=False,
                bytes_scanned_cutoff_per_query=10_000_000_000,  # 10 GB safety limit
            ),
        )
