import json
from typing import Union, List
import zipfile
import io
from time import sleep

import boto3
from botocore.exceptions import ClientError
from resources.aws_policy_document import PolicyStatement, PolicyDocumentCustom


class SnsTopic:
    """
    Class represents SNS Topic resource.
    """
    def __init__(self, name: str):
        self.name = name
        self._sns_client = boto3.client('sns')
        self.arn = None
        # Create Topic if not already exist
        self.create_topic()

    @property
    def subscriptions(self) -> list:
        """
        Returns a list of subscriptions to a specific topic.
        """
        return self._sns_client.list_subscriptions_by_topic(TopicArn=self.arn)['Subscriptions']

    def create_topic(self) -> None:
        """
        Creates SNS Topic resource. Method is called whenever a new instance of SnsTopic is created.
        Method can also be used to recreate SNS Topic resource after deleting it with 'delete_topic' method.
        """
        if not self.check_topic_exist():
            topic = self._sns_client.create_topic(
                Name=self.name,
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    }
                ]
            )
            self.arn = topic['TopicArn']
            print(f'The topic {self.name} created')

    def check_topic_exist(self) -> bool:
        """
        Checks whether a topic with the given name already exists.
        If topic already exists - assign existed topic ARN to 'arn' attribute.
        """
        topics = self._sns_client.list_topics()['Topics']
        for topic in topics:
            topic_arn = topic.get('TopicArn')
            if topic_arn and topic_arn.split(':')[-1] == self.name:
                print(f'Topic {self.name} exist. Using it.')
                self.arn = topic_arn
                return True
        return False

    def subscribe_endpoint(self, endpoint: str, protocol: str = 'email') -> None:
        """
        Adds a subscription to topic.
        The endpoint must be confirmed before their subscriptions are active.
        When a subscription is not confirmed, its ARN is set to 'PendingConfirmation'.
        """
        sub_arn = self.check_subscription_exist(endpoint)
        if sub_arn:
            print(f'The subscription {endpoint} already exist')
        else:
            self._sns_client.subscribe(
                TopicArn=self.arn,
                Protocol=protocol,
                Endpoint=endpoint,
                ReturnSubscriptionArn=False
            )
            print(f'The subscription {endpoint} added to {self.name} topic')
            print('NOTE: Check your email. Please confirm email endpoint subscription before first usage!!!')

    def unsubscribe_endpoint(self, endpoint: str) -> None:
        """
        Deletes specific subscription.
        """
        sub_arn = self.check_subscription_exist(endpoint)
        if sub_arn:
            if sub_arn == 'PendingConfirmation':
                print(f'The subscription "{endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
                return
            else:
                self._sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'The subscription {endpoint} has been deleted')
                return
        print(f'The "{endpoint}" is not valid subscription to {self.name} topic')

    def unsubscribe_all_endpoints(self) -> None:
        """
        Deletes all subscriptions.
        """
        for sub in self.subscriptions:
            sub_arn = sub['SubscriptionArn']
            sub_endpoint = sub['Endpoint']
            if sub_arn == 'PendingConfirmation':
                print(f'The subscription "{sub_endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
            else:
                self._sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'The subscription "{sub_endpoint}" has been deleted')

    def check_subscription_exist(self, endpoint: str) -> Union[None, str]:
        """
        Returns subscription ARN if subscription already exist.
        """
        for sub in self.subscriptions:
            sub_endpoint = sub['Endpoint']
            if sub_endpoint == endpoint:
                return sub['SubscriptionArn']

    def delete_topic(self) -> None:
        """
        Deletes topic.
        """
        self.unsubscribe_all_endpoints()
        self._sns_client.delete_topic(TopicArn=self.arn)
        self.arn = None
        print(f'The topic {self.name} has been deleted')


class IamRoleLambda:
    """
    Class represents IAM role resource. If a role with the specified name already exists, it is used.
    IAM role that allow Lambda function to publish messages to a SNS Topic.
    """
    def __init__(self, name: str, topic_arn: str, dynamodb_arn: str):
        self.name = name
        self.topic_arn = topic_arn
        self.dynamodb_arn = dynamodb_arn
        self._iam_client = boto3.client('iam')
        self.arn = None
        self.role_id = None
        self.create_role()

    def create_role(self) -> None:
        """
        Creates new IAM Role.
        If IAM Role already exists - assign existed IAM Role to 'arn' and 'role_id' attributes.
        """
        try:
            iam_role = self._iam_client.create_role(
                RoleName=self.name,
                AssumeRolePolicyDocument=self.trust_relationship_policy,
                Path='/service-role/',
                Description='IAM role for verus notification',
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    },
                ]
            )
            # Attach AWSLambdaBasicExecutionRole managed policy
            self._iam_client.attach_role_policy(
                RoleName=self.name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            # Attach inline policy - allow Lambda publish to specified SNS topic
            sns_policy_doc = self.create_policy_document(actions=['sns:Publish'],
                                                         resources=[self.topic_arn])
            self._iam_client.put_role_policy(
                RoleName=self.name,
                PolicyName='verus-lambda-sns-publish-inline',
                PolicyDocument=sns_policy_doc
            )
            # Attach inline policy - allow Lambda to put item into DynamoDB table
            dynamodb_policy_doc = self.create_policy_document(
                actions=['dynamodb:PutItem'],
                # resources=['arn:aws:dynamodb:*']
                resources=[self.dynamodb_arn]
            )
            self._iam_client.put_role_policy(
                RoleName=self.name,
                PolicyName='verus-lambda-dynamodb-put-item-inline',
                PolicyDocument=dynamodb_policy_doc
            )
            print(f'The IAM role {self.name} created')
        except ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f'The IMA role {self.name} already exists. Using it.')
                iam_role = self._iam_client.get_role(RoleName=self.name)
            else:
                print('Unexpected error occurred. Role could not be created', error)
                return
        self.arn = iam_role['Role']['Arn']
        self.role_id = iam_role['Role']['RoleId']

    @property
    def trust_relationship_policy(self) -> str:
        """
        The trust relationship policy document that grants an entity permission to assume the IAM Role.
        Only Lambda resource can assume this IAM Role.
        """
        policy = PolicyDocumentCustom()
        policy_statement = PolicyStatement(effect='Allow',
                                           principals={'Service': 'lambda.amazonaws.com'},
                                           actions=['sts:AssumeRole'])
        policy.add_statement(policy_statement)
        return policy.get_json()

    def create_policy_document(self, actions: list, resources: list, effect: str = 'Allow') -> str:
        """
        Returns policy document in JSON format.
        """
        policy = PolicyDocumentCustom()
        policy_statement = PolicyStatement(effect=effect,
                                           actions=actions,
                                           resources=resources)
        policy.add_statement(policy_statement)
        return policy.get_json()

    def list_attached_polices(self) -> List[dict]:
        """
        Lists all managed policies that are attached to the IAM role.
        """
        polices = self._iam_client.list_attached_role_policies(RoleName=self.name)
        return polices.get('AttachedPolicies')

    def attach_policy(self, policy_arn):
        """
        Add the specified managed policy to IAM role.
        """
        self._iam_client.attach_role_policy(
            RoleName=self.name,
            PolicyArn=policy_arn
        )

    def detach_policy(self, policy_arn: str) -> None:
        """
        Removes the specified managed policy from the IAM role.
        """
        self._iam_client.detach_role_policy(
            RoleName=self.name,
            PolicyArn=policy_arn
        )

    def delete_role(self) -> None:
        """
        Deletes the IAM role.
        """
        # Detach all managed policies
        for policy in self.list_attached_polices():
            self.detach_policy(policy['PolicyArn'])
        # Delete inline policies
        self._iam_client.delete_role_policy(
            RoleName=self.name,
            PolicyName='verus-lambda-sns-publish-inline'
        )
        self._iam_client.delete_role_policy(
            RoleName=self.name,
            PolicyName='verus-lambda-dynamodb-put-item-inline'
        )
        # Delete IAM Role
        self._iam_client.delete_role(RoleName=self.name)
        print(f'The IAM Role {self.name} has been deleted')


class CustomerIamPolicy:
    """
    Class represents customer managed IAM policy.
    Policy is NOT deployed when a new CustomerIamPolicy instance is created.
    To deploy policy to AWS use 'create_policy' method on CustomerIamPolicy object.
    """
    def __init__(self, name):
        self.name = name
        self.arn = None
        self._iam_client = boto3.client('iam')
        self.statement = []

    def add_policy_to_statement(self, effect: str, actions: list, resource: str) -> None:
        """
        Adds policies details to 'Statement' part.
        """
        policy = {
            'Effect': effect,
            'Action': actions[0] if len(actions) == 1 else actions,
            'Resource': resource
        }
        self.statement.append(policy)

    def check_policy_exist(self) -> bool:
        """
        Returns policy ARN if policy already exist in 'Local' scope.
        """
        local_policies = self._iam_client.list_policies(Scope='Local')['Policies']
        for policy in local_policies:
            if policy['PolicyName'] == self.name:
                print(f'The policy {self.name} already exists. Using it.')
                self.arn = policy['Arn']
                return True
        return False

    def create_policy(self) -> None:
        """
        Creates customer managed policy - if not exists.
        """
        policy_arn = self.check_policy_exist()
        if not policy_arn:
            policy = {
                'Version': '2012-10-17',
                'Statement': self.statement
            }
            iam_policy = self._iam_client.create_policy(
                PolicyName=self.name,
                PolicyDocument=json.dumps(policy),
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    },
                ]
            )
            self.arn = iam_policy['Policy']['Arn']
            print(f'Policy {self.name} created')

    def delete_policy(self) -> None:
        """
        Deletes customer managed policy.
        """
        if self.arn:
            self._iam_client.delete_policy(PolicyArn=self.arn)
            print(f'The policy {self.name} has been deleted')


class LambdaFunction:
    """
    Class represents Lambda function resource. If a Lambda function with the specified name already exists, it is used.
    The Lambda function publish message to a specific SNS topic.
    """
    def __init__(self, name: str, role_arn: str, topic_arn: str, function_file_name: str = 'lambda_function.py'):
        self.name = name
        self.role_arn = role_arn
        self.topic_arn = topic_arn
        self._lambda_client = boto3.client('lambda')
        self.function_file_name = function_file_name
        self.arn = None
        self.create_function()

    def create_function(self) -> None:
        """
        Creates new Lambda function.
        If Lambda function already exists - assign existed Lambda ARN to 'arn' attribute.
        """
        try:
            lambda_func = self._lambda_client.get_function(
                FunctionName=self.name,
            )
            print(f'The Lambda function {self.name} already exists. Using it.')
            self.arn = lambda_func['Configuration']['FunctionArn']
        except self._lambda_client.exceptions.ResourceNotFoundException:
            # Lambda with specified name does not exist - create new one
            retry_attempt = 0
            sleepy_time = 2
            # Retrying to create Lambda function after sleepy time. This is necessary when AWS is not yet ready to
            # perform an action because IAM role resource has not been fully deployed.
            while True:
                retry_attempt += 1
                try:
                    lambda_func = self._lambda_client.create_function(
                        FunctionName=self.name,
                        Description='Publish a msg to SNS topic when new stake appears in Verus wallet.',
                        Runtime='python3.8',
                        Role=self.role_arn,
                        Handler='lambda_function.lambda_handler',
                        Code={'ZipFile': self._deployment_package},
                        Publish=True,
                        Tags={
                            'Project': 'verus-notification'
                        },
                        Environment={
                            'Variables': {
                                'TOPIC_ARN': self.topic_arn,
                                'DYNAMODB_NAME': 'VerusStakes'
                            }
                        }
                    )
                    break
                except self._lambda_client.exceptions.InvalidParameterValueException:
                    if retry_attempt == 1:
                        print('Creating Lambda function...')
                    sleep(sleepy_time)
            self.arn = lambda_func['FunctionArn']
            print(f'Lambda function {self.name} created')

    @property
    def _deployment_package(self):
        """
        Creates a Lambda deployment package in ZIP format in an in-memory buffer. This
        buffer can be passed directly to AWS Lambda when creating the function.
        """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipped:
            zipped.write(self.function_file_name)
        buffer.seek(0)
        return buffer.read()

    def delete_function(self):
        """
        Deletes Lambda function.
        """
        self._lambda_client.delete_function(FunctionName=self.name)
        print(f'The Lambda function {self.name} has been deleted')

    def add_permission(self, source_arn: str, statement_id: str = 'allow-execution-from-apigateway',
                       principal: str = 'apigateway'):
        """
        Grants AWS service or another account permission to use function.
        """
        try:
            self._lambda_client.add_permission(
                FunctionName=self.name,
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal=f'{principal}.amazonaws.com',
                SourceArn=source_arn,
            )
        except self._lambda_client.exceptions.ResourceConflictException:
            pass


class DynamoDb:
    """
    Class represents DynamoDB table resource. If a DynamoDB with the specified name already exists, it is used.
    """
    def __init__(self, name: str):
        self.name = name
        self.arn = None
        self._dynamodb_client = boto3.client('dynamodb')
        self.create_dynamodb()

    def create_dynamodb(self) -> None:
        """
        Creates DynamoDB table resource. Method is called whenever a new instance of DynamoDb is created.
        Method creates a new DynamoDB table or assigns an ARN value to 'arn' attribute if one already exists.
        """
        if not self.check_table_exist():
            dynamodb_table = self._dynamodb_client.create_table(
                TableName=self.name,
                AttributeDefinitions=[
                    {
                        'AttributeName': 'stake_id',
                        'AttributeType': 'S'
                    }],
                KeySchema=[
                    {
                        'AttributeName': 'stake_id',
                        'KeyType': 'HASH'
                    },
                ],
                BillingMode='PROVISIONED',
                ProvisionedThroughput={
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                },
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    },
                ]
            )
            self.arn = dynamodb_table['TableDescription']['TableArn']
            print(f'The DynamoDB {self.name} table created')
            return
        print(f'The DynamoDB {self.name} table already exists. Using it.')
        self.arn = self.get_table_arn()

    def check_table_exist(self) -> bool:
        """
        Checks whether a DynamoDB table with the given name already exists.
        """
        tables_names = self._dynamodb_client.list_tables()['TableNames']
        if self.name in tables_names:
            return True
        return False

    def get_table_arn(self) -> str:
        """
        Returns DynamoDB table ARN.
        """
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(self.name)
        return table.table_arn

    def delete_table(self):
        """
        Deletes DynamoDB table.
        """
        self._dynamodb_client.delete_table(TableName=self.name)
        print(f'The DynamoDB {self.name} table has been deleted')
