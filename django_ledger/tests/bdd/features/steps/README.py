from behave import *


def parse_float(value):
    return float(value)


register_type(FloatNumber=parse_float)


@given("that we know what the two numbers are {n1:FloatNumber} and {n2:FloatNumber}")
def step_impl(context, n1: float, n2: float):
    context.n1 = n1
    context.n2 = n2


@when("we add both numbers")
def step_impl(context):
    assert isinstance(context.n1, float)
    assert isinstance(context.n2, float)
    context.result = context.n1 + context.n2


@then("we get back the correct result {result:FloatNumber}")
def step_impl(context, result):
    assert context.result == result
