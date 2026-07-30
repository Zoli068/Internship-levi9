from typing import Any
from aws_cdk import Duration, aws_lambda as _lambda
from constructs import Construct
from .storage import MedallionStorageConstruct


class MedallionImportS3Construct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storageConstruct: MedallionStorageConstruct,
        **kwargs: Any,
    ):
        super().__init__(scope, construct_id, **kwargs)

        timeout_period = 300
        destination_prefix = "bronze/sensor/"
        source_prefix = "sensor/Levi9 NineAir Novi Sad/"

        self.object_importer_lambda = _lambda.Function(
            self,
            "ObjectImport",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("./services/medallion/lambdas"),
            handler="object_import_lambda.lambda_handler",
            timeout=Duration.seconds(timeout_period),
            environment={
                "SOURCE_BUCKET_NAME": storageConstruct.external_bucket.bucket_name,
                "DESTINATION_BUCKET_NAME": storageConstruct.medallion_bucket.bucket_name,
                "DESTINATION_PREFIX": destination_prefix,
                "SOURCE_PREFIX": source_prefix,
            },
        )

        storageConstruct.external_bucket.grant_read(self.object_importer_lambda)
        storageConstruct.medallion_bucket.grant_read_write(self.object_importer_lambda)
