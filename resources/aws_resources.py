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
    def __init__(self, name: str, topic_arn: str):
        self.name = name
        self.topic_arn = topic_arn
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
                AssumeRolePolicyDocument=json.dumps(self.trust_relationship_policy),
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
            self._iam_client.put_role_policy(
                RoleName=self.name,
                PolicyName='verus-lambda-sns-publish-inline',
                PolicyDocument=f'{{"Version":"2012-10-17","Statement":'
                               f'{{"Effect":"Allow","Action":"sns:Publish","Resource":"{self.topic_arn}"}}}}'
            )
            # TODO: change to specific DynamDB table (ARN)
            # Attach inline policy - allow Lambda to put item into DynamoDB table
            self._iam_client.put_role_policy(
                RoleName=self.name,
                PolicyName='verus-lambda-dynamodb-put-item-inline',
                PolicyDocument=f'{{"Version":"2012-10-17","Statement":'
                               f'{{"Effect":"Allow","Action":"dynamodb:PutItem","Resource":"arn:aws:dynamodb:*"}}}}'
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
    def trust_relationship_policy(self) -> dict:
        """
        The trust relationship policy document that grants an entity permission to assume the IAM Role.
        Only Lambda resource can assume this IAM Role.
        """
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'lambda.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }
        return policy

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


class ApiGateway:
    """
    Class represents API Gateway resource. If a API Gateway with the specified name already exists, it is used.
    The API Gateway is publicly accessible and invokes Lambda function.
    """
    def __init__(self, name: str, lambda_arn: str):
        self.name = name
        self.lambda_arn = lambda_arn
        self.id = None
        self.source_arn = None
        self.url = None
        self.api_endpoint = 'stake'
        self._api_client = boto3.client('apigateway')
        self._account_id = boto3.client('sts').get_caller_identity()['Account']
        self.create_api()

    def create_api(self) -> None:
        """
        Creates API Gateway resource. Method is called whenever a new instance of ApiGateway is created.
        Method can also be used to recreate API Gateway resource after deleting it with 'delete_api' method.
        """
        if not self.check_api_exist():
            resource_policy = self.create_policy()

            api = self._api_client.create_rest_api(
                name=self.name,
                description='Invoke Lambda function to publish a msg to SNS topic when new stake appears in Verus wallet.',
                apiKeySource='HEADER',
                endpointConfiguration={
                    'types': ['REGIONAL'],
                },
                policy=resource_policy,
                tags={
                    'Project': 'verus-notification'
                },
            )
            self.id = api['id']
            # Create resource 'stake'
            # Get parent id - root resource (path '/')
            root_id = self.get_root_resource_id()
            resource = self._api_client.create_resource(
                restApiId=self.id,
                parentId=root_id,
                pathPart=self.api_endpoint
            )
            resource_id = resource['id']
            # Put method to resource
            self._api_client.put_method(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                authorizationType='NONE'
            )
            # Put method response
            self._api_client.put_method_response(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                statusCode='200',
            )
            # Put method integration
            lambda_uri = f'arn:aws:apigateway:{self._api_client.meta.region_name}:' \
                         f'lambda:path/2015-03-31/functions/{self.lambda_arn}/invocations'
            # NOTE: For Lambda integrations, you must use the HTTP method of POST for the integration request
            # (integrationHttpMethod) or this will not work
            self._api_client.put_integration(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                type='AWS',
                integrationHttpMethod='POST',
                uri=lambda_uri,
                connectionType='INTERNET',
            )
            # Put method integration response
            self._api_client.put_integration_response(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                statusCode='200',
                selectionPattern='',
                contentHandling='CONVERT_TO_TEXT'
            )
            self.source_arn = f'arn:aws:execute-api:{self._api_client.meta.region_name}:' \
                              f'{self._account_id}:{self.id}/*/GET/{self.api_endpoint}'
            # Create deployment
            self._api_client.create_deployment(
                restApiId=self.id,
                stageName='vrsc'
            )
            # Create API URL
            self.url = f'https://{self.id}.execute-api.{self._api_client.meta.region_name}.amazonaws.com' \
                       f'/vrsc/{self.api_endpoint}'
            print(f'API Gateway {self.name} created')

    def check_api_exist(self) -> bool:
        """
        Checks whether a API with the given name already exists.
        If API already exists - assign existed API id to 'id' attribute.
        """
        apis_list = self._api_client.get_rest_apis()['items']
        for api in apis_list:
            if api['name'] == self.name:
                print(f'API Gateway {self.name} exist. Using it.')
                self.id = api['id']
                self.url = f'https://{self.id}.execute-api.{self._api_client.meta.region_name}.' \
                           f'amazonaws.com/vrsc/{self.api_endpoint}'
                self.source_arn = f'arn:aws:execute-api:{self._api_client.meta.region_name}:' \
                                  f'{self._account_id}:{self.id}/*/GET/{self.api_endpoint}'
                return True
        return False

    def get_root_resource_id(self) -> str:
        """
        Returns parent id (root resource - path '/').
        """
        resources = self._api_client.get_resources(restApiId=self.id)
        resource_items = resources['items']
        for item in resource_items:
            if item['path'] == '/':
                # return root resource id
                return item['id']

    def create_policy(self):
        """
        Creates resource-based policy for API Gateway endpoint
        """
        policy = PolicyDocumentCustom()
        policy_statement = PolicyStatement(effect='Allow',
                                           actions='execute-api:Invoke',
                                           resources='execute-api:/*',
                                           principals='*')
        policy_statement.add_condition(condition_operator='IpAddress',
                                       condition_key='aws:SourceIp',
                                       condition_value=['0.0.0.0/0'])
        policy.add_statement(policy_statement)
        return policy.get_json()


    def delete_api(self):
        """
        Deletes API Gateway.
        """
        self._api_client.delete_rest_api(restApiId=self.id)
        print(f'The API Gateway {self.name} has been deleted')
