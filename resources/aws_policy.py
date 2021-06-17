import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class PolicyStatementCondition:
    """
    Condition for AWS policy statement.
    """
    condition_operator: str
    condition_statements: dict = field(default_factory=dict)

    def add_condition_pair(self, key: str, value: list) -> None:
        """
        Add key-value pair to condition statement.
        """
        self.condition_statements[key] = value[0] if len(value) == 1 else value

    def get_condition(self) -> dict:
        statement = {self.condition_operator: self.condition_statements}
        return statement


@dataclass
class PolicyStatement:
    """
    AWS policy statement.
    """
    effect: str
    actions: list
    resources: list
    principals: dict = field(default_factory=dict)
    sid: str = None
    conditions: dict = field(default_factory=dict)

    @property
    def data(self) -> dict:
        """
        Returns prepared policy statement.
        """
        new_statement = {
            'Effect': self.effect,
            'Action': self.actions[0] if len(self.actions) == 1 else self.actions,
            'Resource': self.resources
        }
        if self.sid:
            new_statement['Sid'] = self.sid
        if self.conditions:
            new_statement['Condition'] = self.conditions
        if self.principals:
            new_statement['Principal'] = self.principals
        return new_statement

    def add_condition(self, condition_operator: str, condition_key: str, condition_value: List[str]) -> None:
        """
        Add condition to policy statement.
        """
        self.conditions[condition_operator] = {
            condition_key: condition_value[0] if len(condition_value) == 1 else condition_value
        }

    def add_principal(self, principal_operator: str, principal_key: str, principal_value: List[str]) -> None:
        """
        Add condition to policy statement.
        """
        self.principals[principal_operator] = {
            principal_key: principal_value[0] if len(principal_value) == 1 else principal_value
        }


class PolicyCustom:
    """
    AWS policy object. It represent identity-based or resource-based policy.
    """
    def __init__(self):
        self.statements = []

    def add_statement(self, statement: PolicyStatement) -> None:
        self.statements.append(statement.data)

    @property
    def schema(self) -> dict:
        policy = {
            'Version': '2012-10-17',
            'Statement': self.statements
        }
        return policy

    def get_json(self) -> str:
        return json.dumps(self.schema)

