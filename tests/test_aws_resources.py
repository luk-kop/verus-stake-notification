import json

from resources.aws_policy_document import PolicyDocumentCustom, PolicyStatementCondition


def test_condition_one_condition_pair():
    """
    GIVEN PolicyStatementCondition object.
    WHEN Created PolicyStatementCondition object with 'condition_operator','condition_statements attributes.
    THEN Object created with desired attributes.
    """
    cond_statement = PolicyStatementCondition(
        condition_operator='StringEquals',
        condition_statements={'ec2:Vpc': 'arn:aws:ec2:region:account:vpc/vpc-11223344556677889'}
    )
    desired_result = {
        'StringEquals': {
            'ec2:Vpc': 'arn:aws:ec2:region:account:vpc/vpc-11223344556677889'
        }
    }
    assert cond_statement.get_condition() == desired_result


def test_statement_mandatory_attrs(dummy_policy_statement):
    """
    GIVEN PolicyStatement object.
    WHEN Created PolicyStatement object with mandatory attributes.
    THEN Object created with desired attributes.
    """
    desired_result = {
        'Effect': 'Allow',
        'Action': 'execute-api:Invoke',
        'Resource': ['execute-api:/*']
    }
    assert dummy_policy_statement.data == desired_result


def test_statement_add_condition(dummy_policy_statement):
    """
    GIVEN PolicyStatement object.
    WHEN Add condition to PolicyStatement object.
    THEN Condition attached.
    """
    dummy_policy_statement.add_condition(
        condition_operator='StringEquals',
        condition_key='ec2:Vpc',
        condition_value=['arn:aws:ec2:region:account:vpc/vpc-11223344556677889']
    )
    desired_result = {
        'Effect': 'Allow',
        'Action': 'execute-api:Invoke',
        'Resource': ['execute-api:/*'],
        'Condition': {
            'StringEquals': {
                'ec2:Vpc': 'arn:aws:ec2:region:account:vpc/vpc-11223344556677889'
            }
        }
    }
    assert dummy_policy_statement.data == desired_result


def test_policy_schema_no_statement():
    """
    GIVEN PolicyCustom object.
    WHEN PolicyCustom object has been created without statement.
    THEN Object created without statement part.
    """
    policy = PolicyDocumentCustom()
    desired_policy = {
        'Version': '2012-10-17',
        'Statement': []
    }
    assert policy.schema == desired_policy


def test_policy_schema_one_statement_no_condition(dummy_policy_statement):
    """
    GIVEN PolicyCustom and PolicyStatement object.
    WHEN Created object with one statement.
    THEN Object created with statement part and no conditions.
    """
    test_policy = PolicyDocumentCustom()
    test_policy.add_statement(dummy_policy_statement)
    desired_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 'execute-api:Invoke',
                'Resource': ['execute-api:/*']
            }
        ]
    }
    assert test_policy.schema == desired_policy


def test_policy_json_one_statement_no_condition(dummy_policy_statement):
    """
    GIVEN PolicyCustom and PolicyStatement object.
    WHEN Created object with one statement.
    THEN Return policy data in JSON format.
    """
    test_policy = PolicyDocumentCustom()
    test_policy.add_statement( dummy_policy_statement)
    desired_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 'execute-api:Invoke',
                'Resource': ['execute-api:/*']
            }
        ]
    }
    assert test_policy.get_json() == json.dumps(desired_policy)
