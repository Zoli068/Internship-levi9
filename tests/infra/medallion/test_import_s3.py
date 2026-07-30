import aws_cdk as core
import aws_cdk.assertions as assertions
from infra.cdk_constructs.medallion.storage import MedallionStorageConstruct
from infra.cdk_constructs.medallion.import_s3 import MedallionImportS3Construct


def test_medallion_import_s3_construct_creates_lambda_with_correct_props() -> None:
    app = core.App()
    stack = core.Stack(app, "TestStack")

    storage = MedallionStorageConstruct(stack, "TestStorage")

    MedallionImportS3Construct(stack, "TestImportS3", storageConstruct=storage)

    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Lambda::Function", 1)

    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        {
                            "Action": [
                                "s3:GetObject*",
                                "s3:GetBucket*",
                                "s3:List*",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::levi9-hack9-nineair-sensor-data",
                                "arn:aws:s3:::levi9-hack9-nineair-sensor-data/*",
                            ],
                        },
                        {
                            "Action": [
                                "s3:GetObject*",
                                "s3:GetBucket*",
                                "s3:List*",
                                "s3:DeleteObject*",
                                "s3:PutObject*",
                                "s3:Abort*",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::aws-internship-pollution-387075079166-eu-central-1-an",
                                "arn:aws:s3:::aws-internship-pollution-387075079166-eu-central-1-an/*",
                            ],
                        },
                    ]
                )
            }
        },
    )
