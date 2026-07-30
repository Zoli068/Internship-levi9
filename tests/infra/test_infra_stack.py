import aws_cdk as core
import aws_cdk.assertions as assertions

from infra.stacks.infra_stack import InfraStack


def test_infra_stack_successfully_instantiates_medallion_orchestrator() -> None:
    app = core.App()

    stack = InfraStack(app, "TestInfraStack")

    assert hasattr(stack, "medallion")

    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Lambda::Function", 1)
