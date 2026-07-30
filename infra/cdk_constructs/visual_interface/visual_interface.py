from aws_cdk import aws_s3_deployment as s3_deploy
from constructs import Construct
from ..medallion.storage import MedallionStorageConstruct
from typing import Any


class VisualInterfaceConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storageConstruct: MedallionStorageConstruct,
        **kwargs: Any,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Deploying our "front-end" code to s3 bucket
        s3_deploy.BucketDeployment(
            self,
            "HTMLPages",
            sources=[s3_deploy.Source.asset("./frontend/")],
            destination_bucket=storageConstruct.static_webhost_bucket,
            prune=False,
        )
