import aws_cdk as core
import aws_cdk.assertions as assertions
from infra.cdk_constructs.medallion.storage import MedallionStorageConstruct


def test_medallion_storage_construct_creates_sqs_with_properties() -> None:

    app = core.App()
    stack = core.Stack(app, "TestStack")

    construct = MedallionStorageConstruct(stack, "TestMedallionStorage")

    template = assertions.Template.from_stack(stack)

    assert construct.external_bucket.bucket_name == "levi9-hack9-nineair-sensor-data"
    assert (
        construct.medallion_bucket.bucket_name
        == "aws-internship-pollution-387075079166-eu-central-1-an"
    )

    template.resource_count_is("AWS::S3::Bucket", 0)
