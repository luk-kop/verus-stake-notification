import boto3
from typing import List, Union
from dataclasses import dataclass

from resources.aws_policy_document import PolicyStatement, PolicyDocumentCustom
from resources.aws_cognito import CognitoUserPool, CognitoResources


class ApiGateway:
    """
    Class represents API Gateway resource. If a API Gateway with the specified name already exists, it is used.
    The API Gateway is publicly accessible and invokes Lambda function.
    """
    def __init__(self, name: str, lambda_arn: str):
        self.name = name
        self.lambda_arn = lambda_arn
        self.api_endpoint = 'stake'
        self._api_client = boto3.client('apigateway')
        self._account_id = boto3.client('sts').get_caller_identity()['Account']

    def create_resource(self) -> None:
        """
        Creates Cognito user pool resource in AWS cloud.
        """
        if not self._check_exist():
            resource_policy = self.create_policy()

            self._api_client.create_rest_api(
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
            print(f'The API Gateway "{self.name}" created.')
            return
        print(f'The API Gateway "{self.name}" exists. Using it.')

    @property
    def id(self):
        """
        Returns API Gateway id.
        """
        for api in self._api_gateways:
            if api['name'] == self.name:
                return api['id']
        return ''

    def get_url(self, stage_name: str):
        """
        Returns API Gateway URL.
        """
        if self._check_stage_exist(name=stage_name):
            for api in self._api_gateways:
                if api['name'] == self.name:
                    return f'https://{self.id}.execute-api.{self._api_client.meta.region_name}.' \
                           f'amazonaws.com/{stage_name}/{self.api_endpoint}'
        print(f'Stage name {stage_name} does not exist')
        return ''

    def _check_stage_exist(self, name):
        """
        Checks if stage with specified name already exist.
        """
        try:
            self._api_client.get_stage(restApiId=self.id,
                                       stageName=name)
            return True
        except self._api_client.exceptions.NotFoundException:
            return False

    @property
    def arn(self):
        """
        Returns API Gateway ARN.
        """
        for api in self._api_gateways:
            if api['name'] == self.name:
                return f'arn:aws:execute-api:{self._api_client.meta.region_name}:' \
                       f'{self._account_id}:{self.id}/*/GET/{self.api_endpoint}'
        return ''

    def _check_exist(self):
        """
        Checks if API Gateway resource with specified name already exist.
        """
        return True if self.id else False

    @property
    def _api_gateways(self):
        """
        Returns list of already created API Gateways.
        """
        return self._api_client.get_rest_apis()['items']

    @property
    def authorizers(self) -> list:
        """
        Returns list of already created API Gateway Authorizers.
        """
        try:
            return self._api_client.get_authorizers(limit=50,
                                                    restApiId=self.id)['items']
        except self._api_client.exceptions.NotFoundException:
            return []

    @property
    def root_resource_id(self) -> str:
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

    def delete_resource(self):
        """
        Deletes API Gateway with all associated API Gateway resources.
        """
        if self._check_exist():
            self._api_client.delete_rest_api(restApiId=self.id)
            print(f'The API Gateway {self.name} has been deleted')
            return
        print(f'The API Gateway "{self.name}" does not exist')

    def deploy(self, stage_name: str) -> None:
        """
        Creates API Gateway deployment.
        """
        if not self._check_stage_exist(name=stage_name):
            self._api_client.create_deployment(restApiId=self.id,
                                               stageName=stage_name)
            return
        print(f'Stage name "{stage_name}" already exists')


class ApiGatewayAuthorizer:
    """
    Class represents API Gateway Authorizer resource.
    """
    def __init__(self, name: str, api_id: str, providers: List[CognitoUserPool], auth_type: str) -> None:
        self.api_id = api_id
        self.name = name
        self.providers = providers
        self.auth_type = auth_type
        self._auth_client = boto3.client('apigateway')

    def create_resource(self) -> None:
        """
        Creates API Gateway Authorizer resource in AWS cloud.
        """
        if not self._check_exist():
            self._auth_client.create_authorizer(
                restApiId=self.api_id,
                name=self.name,
                type=self.auth_type,
                providerARNs=[provider.arn for provider in self.providers],
                identitySource='method.request.header.Authorization',
            )
            print(f'The API Gateway Authorizer "{self.name}" created')
            return
        print(f'The API Gateway Authorizer "{self.name}" exists. Using it.')

    @property
    def auth_type(self) -> str:
        """
        Returns auth_type attribute
        """
        return self._auth_type

    @auth_type.setter
    def auth_type(self, new_type) -> str:
        """
        Sets auth_type attribute and makes simple input validation.
        """
        allowed_types = ['TOKEN', 'REQUEST', 'COGNITO_USER_POOLS']
        if new_type not in allowed_types:
            raise AttributeError(f'Wrong auth_type value. The allowed auth_type values: {", ".join(allowed_types)}')
        self._auth_type = new_type

    @property
    def id(self) -> str:
        """
        Returns API Gateway Authorizer id.
        """
        for auth in self._authorizers:
            if auth['name'] == self.name:
                return auth['id']
        return ''

    @property
    def _authorizers(self) -> list:
        """
        Returns list of already created API Gateway Authorizers.
        """
        try:
            return self._auth_client.get_authorizers(limit=50,
                                                     restApiId=self.api_id)['items']
        except self._auth_client.exceptions.NotFoundException:
            return []

    def _check_exist(self) -> bool:
        """
        Checks if API Gateway Authorizer resource with specified name already exist.
        Assign 'id' attribute if user pool client exist.
        """
        result = True if self.id else False
        return result

    def delete_resource(self) -> None:
        """
        Deletes API Gateway Authorizer in AWS cloud.
        """
        if self._check_exist():
            try:
                self._auth_client.delete_authorizer(restApiId=self.api_id,
                                                    authorizerId=self.id)
                print(f'The API Gateway Authorizer "{self.name}" has been deleted')
            except self._auth_client.exceptions.ConflictException as err:
                print(err.response['Error']['Message'])
            return
        print(f'The API Gateway Authorizer "{self.name}" does not exist')


@dataclass
class ApiMethod:
    """
    Class represents API Gateway HTTP method.
    """
    http_method: str
    api_id: str
    resource_id: str
    authorizer: Union[None, ApiGatewayAuthorizer] = None

    @property
    def data(self) -> dict:
        """
        Returns properly prepared HTTP method statement for boto3 usage.
        """
        method_data = {
            'restApiId': self.api_id,
            'resourceId': self.resource_id,
            'httpMethod': self.http_method
        }
        if self.authorizer:
            method_data['authorizationType'] = self.authorizer.auth_type
            method_data['authorizerId'] = self.authorizer.id
            # TODO: change below!!!
            resource_srv = self.authorizer.providers[0].resource_servers[0]
            resource_srv_scopes = resource_srv['Scopes']
            resource_srv_identifier = resource_srv['Identifier']
            method_data['authorizationScopes'] = [f'{resource_srv_identifier}/{scope["ScopeName"]}'for scope in resource_srv_scopes]
        else:
            method_data['authorizationType'] = 'NONE'
        return method_data


class ApiGatewayResource:
    """
    Class represents API Gateway Resource resource.
    """
    def __init__(self, api_id: str, parent_id: str, path_part: str) -> None:
        self.api_id = api_id
        self.parent_id = parent_id
        self.path_part = path_part
        self._api_resource_client = boto3.client('apigateway')

    def create_resource(self) -> None:
        """
        Creates API Gateway Resource resource in AWS cloud.
        """
        if not self._check_exist():
            self._api_resource_client.create_resource(
                restApiId=self.api_id,
                parentId=self.parent_id,
                pathPart=self.path_part
            )
            print(f'The API Gateway resource "{self.path_part}" created')
            return
        print(f'The API Gateway resource "{self.path_part}" exists. Using it.')

    def _check_exist(self) -> bool:
        """
        Checks if API Gateway resource with specified path already exist.
        """
        return True if self.id else False

    @property
    def _api_resources(self) -> list:
        """
        Returns list of already created API Gateway resources.
        """
        return self._api_resource_client.get_resources(restApiId=self.api_id,
                                                       limit=60)['items']

    @property
    def id(self) -> str:
        """
        Returns user pool id.
        """
        for resource in self._api_resources:
            path_part = resource.get('pathPart')
            if path_part == self.path_part:
                return resource['id']
        return ''

    @property
    def full_path(self) -> str:
        """
        Returns full path for API Gateway resource.
        """
        if self._check_exist():
            resource = self._api_resource_client.client.get_resource(
                restApiId=self.api_id,
                resourceId=self.id,
            )
            return resource['path']
        return ''

    def put_method(self, api_method: ApiMethod) -> None:
        """
        Adds a method to existing resource.
        """
        try:
            self._api_resource_client.put_method(**api_method.data)
        except self._api_resource_client.exceptions.ConflictException:
            print('Method already exists for this resource')

    def put_integration(self, api_method, lambda_arn, integration_type: str = 'AWS') -> None:
        """
        Sets up a method' integration.
        """
        # NOTE: For Lambda integrations, you must use the HTTP method of POST for the integration request
        # (integrationHttpMethod) or this will not work
        lambda_uri = f'arn:aws:apigateway:{self._api_resource_client.meta.region_name}:' \
                     f'lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        self._api_resource_client.put_integration(restApiId=self.api_id,
                                                  resourceId=self.id,
                                                  httpMethod=api_method.http_method,
                                                  type=integration_type,
                                                  integrationHttpMethod='POST',
                                                  uri=lambda_uri,
                                                  connectionType='INTERNET'
                                                  )

    def put_method_response(self, api_method: ApiMethod) -> None:
        """
        Adds a method response to an existing existing method resource.
        """
        api_method = api_method.data
        # Remove unnecessary keys
        allowed_keys = ['restApiId', 'resourceId', 'httpMethod']
        method_response = {key: value for (key, value) in api_method.items() if key in allowed_keys}
        method_response['statusCode'] = '200'
        # Put method response
        try:
            self._api_resource_client.put_method_response(**method_response)
        except self._api_resource_client.exceptions.ConflictException:
            print('Response already exists for this resource')

    def put_integration_response(self, api_method: ApiMethod) -> None:
        """
        Sets up a method' integration response.
        """
        self._api_resource_client.put_integration_response(restApiId=self.api_id,
                                                           resourceId=self.id,
                                                           httpMethod=api_method.data['httpMethod'],
                                                           statusCode='200',
                                                           selectionPattern='',
                                                           contentHandling='CONVERT_TO_TEXT')

    def delete_resource(self) -> None:
        """
        Deletes API Gateway resource in AWS cloud.
        """
        if self._check_exist():
            try:
                self._api_resource_client.delete_resource(restApiId=self.api_id,
                                                          resourceId=self.id)
                print(f'The API Gateway resource "{self.path_part}" has been deleted')
            except self._api_resource_client.exceptions.InvalidParameterException as err:
                print(err.response['Error']['Message'])
            return
        print(f'The API Gateway resource "{self.path_part}" does not exist')


class ApiResources:
    """
    Class represents all API Gateway related resources used in verus-notification project.
    """
    def __init__(self, api_name: str, lambda_arn: str, http_methods: list, stage_name: str,
                 user_pool: Union[CognitoUserPool, None] = None) -> None:
        self.api_name = api_name
        self.lambda_arn = lambda_arn
        self.user_pool = user_pool
        self.http_methods = http_methods
        self.stage_name = stage_name
        self.authorizer = None
        # API Gateway instantiation
        self.api = ApiGateway(name=api_name, lambda_arn=lambda_arn)
        self.api.create_resource()
        # API Gateway Resource instantiation
        self.api_resource = ApiGatewayResource(api_id=self.api.id,
                                               parent_id=self.api.root_resource_id,
                                               path_part='stake')
        self.api_resource.create_resource()
        if user_pool:
            # API Gateway Authorizer instantiation
            self.authorizer = ApiGatewayAuthorizer(name='VerusApiAuthBoto3',
                                                   api_id=self.api.id,
                                                   providers=[user_pool],
                                                   auth_type='COGNITO_USER_POOLS')
            self.authorizer.create_resource()
        self.add_http_methods()
        # Deploy API Gateway
        self.api.deploy(stage_name=stage_name)

    @property
    def invoke_url(self):
        """
        Returns API Gateway invoke URL.
        """
        return self.api.get_url(self.stage_name)

    @property
    def arn(self):
        """
        Returns API Gateway ARN.
        """
        return self.api.arn

    def add_http_methods(self):
        """
        Adds HTTP methods and integrations to API Gateway Resource.
        """
        for method in self.http_methods:
            method_get = ApiMethod(http_method=method,
                                   api_id=self.api.id,
                                   resource_id=self.api_resource.id,
                                   authorizer=self.authorizer)
            self.api_resource.put_method(api_method=method_get)
            self.api_resource.put_integration(api_method=method_get, lambda_arn=self.lambda_arn)
            self.api_resource.put_method_response(api_method=method_get)
            self.api_resource.put_integration_response(api_method=method_get)

    def create(self):
        """
        Creates all API Gateway related resources. Method can be used to recreate API Gateway resources after deletion.
        """
        self.api.create_resource()
        if self.user_pool:
            self.authorizer.create_resource()
        self.add_http_methods()
        # Deploy API Gateway
        self.api.deploy(stage_name=self.stage_name)

    def delete(self):
        """
        Deletes all API Gateway related resources.
        """
        self.api.delete_resource()


def main() -> None:
    """
    Main function - example of use
    """
    # Add existed Lambda ARN
    lambda_arn = ''

    scopes = [
        {
            'name': 'api-read',
            'description': 'Read access to the API'
        }
    ]
    cognito_resources = CognitoResources(user_pool_name='UserPool4Tests',
                                         resource_server_scopes=scopes,
                                         pool_domain='verus-test-12345',
                                         name_prefix='verus-api')

    resources = ApiResources(api_name='ApiGateway4Tests',
                             lambda_arn=lambda_arn,
                             http_methods=['GET'],
                             stage_name='vrsc',
                             user_pool=cognito_resources.user_pool)
    print(resources.invoke_url)
    # Delete all resources
    resources.delete()
    cognito_resources.delete()


if __name__ == '__main__':
    main()